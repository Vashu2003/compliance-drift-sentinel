"""End-to-end: live lineage -> deterministic impact -> Gemini narration + drafted contract.

    make up && make seed
    ./.venv/bin/python scripts/demo_agent.py   # needs GEMINI_API_KEY in .env

Writes examples/margin_haircut_explanation.md.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datahub.ingestion.graph.client import DataHubGraph, DatahubClientConfig

from engine.agent import DriftNarrator
from engine.config import DataHubConfig
from engine.impact import analyze
from engine.lineage_graph import ColumnLineageGraph
from engine.models import ChangeType, ColumnRef, SchemaChange

COLL = "urn:li:dataset:(urn:li:dataPlatform:snowflake,broker.raw.collateral,PROD)"
REPORT = "urn:li:dataset:(urn:li:dataPlatform:snowflake,broker.marts.margin_report,PROD)"


def main() -> None:
    cfg = DataHubConfig()
    graph = ColumnLineageGraph.from_datahub(
        DataHubGraph(DatahubClientConfig(server=cfg.gms_url)), REPORT
    )
    report = analyze(
        SchemaChange(ColumnRef(COLL, "haircut_pct"), ChangeType.RETYPED,
                     detail="Upstream changed haircut_pct from percent (0-100) to fraction (0-1)."),
        graph,
    )
    print("ENGINE:", report.summary(), "\n")

    exp = DriftNarrator().narrate(report)
    print("NARRATIVE:", exp.narrative)
    print("IMPACT:   ", exp.business_impact)
    print("CONTRACT: ", exp.contract)
    print("FIX:      ", exp.remediation)

    md = "\n".join([
        "# Drift Sentinel — Agent Explanation (Gemini)\n",
        f"**Detected (deterministic engine):** {report.summary()}\n",
        f"## Narrative\n{exp.narrative}\n",
        f"## Business impact\n{exp.business_impact}\n",
        f"## Proposed data contract\n```\n{exp.contract}\n```\n",
        f"## Remediation\n{exp.remediation}\n",
    ])
    out = Path(__file__).resolve().parent.parent / "examples" / "margin_haircut_explanation.md"
    out.write_text(md)
    print(f"\nwrote {out.relative_to(out.parent.parent)}")


if __name__ == "__main__":
    main()
