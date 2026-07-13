"""End-to-end demo: detect drift on the margin report and write findings back to DataHub.

    make up && make seed && make provision
    ./.venv/bin/python scripts/demo_writeback.py

Then open the margin_report dataset in DataHub (localhost:9002) to see the drift tags,
`drift_status` property, and auto-proposed contract on the affected columns.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datahub.ingestion.graph.client import DataHubGraph, DatahubClientConfig

from engine.config import DataHubConfig
from engine.datahub_client import DataHubClient
from engine.impact import analyze
from engine.lineage_graph import ColumnLineageGraph
from engine.models import ChangeType, ColumnRef, SchemaChange
from engine.writer import DriftWriter

COLL = "urn:li:dataset:(urn:li:dataPlatform:snowflake,broker.raw.collateral,PROD)"
REPORT = "urn:li:dataset:(urn:li:dataPlatform:snowflake,broker.marts.margin_report,PROD)"


async def main() -> None:
    cfg = DataHubConfig(mutation_enabled=True)
    graph = ColumnLineageGraph.from_datahub(
        DataHubGraph(DatahubClientConfig(server=cfg.gms_url)), REPORT
    )
    change = SchemaChange(
        ColumnRef(COLL, "haircut_pct"),
        ChangeType.RETYPED,
        detail="Upstream changed haircut_pct from percent (0-100) to fraction (0-1).",
    )
    report = analyze(change, graph)
    print("DETECTED:", report.summary())

    async with DataHubClient(cfg).connect() as dh:
        result = await DriftWriter(dh).write(report)

    print(f"WROTE BACK: {result.columns_annotated} columns, {result.tags_written} tags")
    for d in result.details:
        print("  -", d)
    print("\nView it: http://localhost:9002 → search 'margin_report' → Schema tab "
          "(affected columns now carry drift tags + a proposed contract).")


if __name__ == "__main__":
    asyncio.run(main())
