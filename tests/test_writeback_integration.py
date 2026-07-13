"""Slice 3 integration test — write drift findings back to DataHub, then read them back.

Requires: `make up && make seed && make provision` (vocab), live DataHub.
"""
import pytest

from datahub.ingestion.graph.client import DataHubGraph, DatahubClientConfig
from datahub.metadata.schema_classes import EditableSchemaMetadataClass

from engine.config import DataHubConfig
from engine.datahub_client import DataHubClient
from engine.impact import analyze
from engine.lineage_graph import ColumnLineageGraph
from engine.models import ChangeType, ColumnRef, SchemaChange
from engine.writer import CONTRACT_MARKER, DriftWriter

COLL = "urn:li:dataset:(urn:li:dataPlatform:snowflake,broker.raw.collateral,PROD)"
REPORT = "urn:li:dataset:(urn:li:dataPlatform:snowflake,broker.marts.margin_report,PROD)"
AFFECTED = {"collateral_after_haircut", "total_available_margin", "margin_shortfall"}


def _read_fields(gms: str):
    g = DataHubGraph(DatahubClientConfig(server=gms))
    esm = g.get_aspect(entity_urn=REPORT, aspect_type=EditableSchemaMetadataClass)
    return {f.fieldPath: f for f in (esm.editableSchemaFieldInfo if esm else [])}


@pytest.mark.integration
async def test_write_back_annotates_all_affected_columns():
    cfg = DataHubConfig(mutation_enabled=True)
    graph = ColumnLineageGraph.from_datahub(
        DataHubGraph(DatahubClientConfig(server=cfg.gms_url)), REPORT
    )
    report = analyze(
        SchemaChange(ColumnRef(COLL, "haircut_pct"), ChangeType.RETYPED,
                     detail="haircut_pct pct(0-100) -> fraction(0-1)"),
        graph,
    )

    async with DataHubClient(cfg).connect() as dh:
        result = await DriftWriter(dh).write(report)

    assert result.columns_annotated == 3

    fields = _read_fields(cfg.gms_url)
    for col in AFFECTED:
        f = fields[col]
        tags = {t.tag.split(":")[-1] for t in (f.globalTags.tags if f.globalTags else [])}
        assert "drift-silent-break" in tags, (col, tags)
        assert "drift-at-risk" in tags, (col, tags)
        assert CONTRACT_MARKER in (f.description or ""), col
