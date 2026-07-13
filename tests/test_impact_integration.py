"""Slice 2 integration test — impact engine over the REAL seeded margin pipeline.

Requires: `make up` then `./.venv/bin/python data/seed_margin_pipeline.py`.
"""
import pytest

from datahub.ingestion.graph.client import DataHubGraph, DatahubClientConfig

from engine.config import DataHubConfig
from engine.impact import analyze
from engine.lineage_graph import ColumnLineageGraph
from engine.models import ChangeType, ColumnRef, SchemaChange

COLL = "urn:li:dataset:(urn:li:dataPlatform:snowflake,broker.raw.collateral,PROD)"
REPORT = "urn:li:dataset:(urn:li:dataPlatform:snowflake,broker.marts.margin_report,PROD)"

EXPECTED_HAIRCUT_IMPACT = {
    "broker.marts.margin_report.collateral_after_haircut",
    "broker.marts.margin_report.total_available_margin",
    "broker.marts.margin_report.margin_shortfall",
}


@pytest.fixture(scope="module")
def live_graph() -> ColumnLineageGraph:
    cfg = DataHubConfig()
    client = DataHubGraph(DatahubClientConfig(server=cfg.gms_url))
    return ColumnLineageGraph.from_datahub(client, REPORT)


@pytest.mark.integration
def test_real_lineage_loaded(live_graph):
    # 8 fine-grained edges were seeded; graph should be non-empty.
    change = SchemaChange(ColumnRef(COLL, "market_value"), ChangeType.DROPPED)
    assert analyze(change, live_graph).breaks


@pytest.mark.integration
def test_dropping_haircut_pct_breaks_expected_report_columns(live_graph):
    change = SchemaChange(ColumnRef(COLL, "haircut_pct"), ChangeType.DROPPED,
                          detail="collateral.haircut_pct removed by upstream team")
    report = analyze(change, live_graph)

    assert report.breaks
    assert {str(a.column) for a in report.affected} == EXPECTED_HAIRCUT_IMPACT
    assert report.severity == "hard_break"
