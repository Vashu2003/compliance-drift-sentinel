"""FastAPI backend for the Drift Sentinel UI.

Impact analysis + lineage + narration run in-process (no live DataHub needed → deployable on a
free tier). Write-back hits the live DataHub via MCP; when it can't (deployed demo), it returns
a simulated result flagged `live: false`.
"""
from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from engine.agent import DriftNarrator
from engine.config import DataHubConfig, GeminiConfig
from engine.impact import analyze
from engine.margin_pipeline import (
    SCENARIOS,
    build_column_graph,
    dataset_urn,
    lineage_view,
)
from engine.models import ChangeType, ColumnRef, ImpactReport, SchemaChange

LIVE_WRITEBACK = os.getenv("SENTINEL_LIVE_WRITEBACK", "true").lower() == "true"

app = FastAPI(title="Compliance Drift Sentinel", version="0.5.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

_GRAPH = build_column_graph()


class ChangeRequest(BaseModel):
    dataset: str
    column: str
    change_type: str  # dropped | renamed | retyped
    detail: str = ""


def _report(req: ChangeRequest) -> ImpactReport:
    change = SchemaChange(
        column=ColumnRef(dataset_urn(req.dataset), req.column),
        change_type=ChangeType(req.change_type),
        detail=req.detail,
    )
    return analyze(change, _GRAPH)


def _serialize(report: ImpactReport) -> dict:
    return {
        "dataset": report.change.column.dataset_name,
        "column": report.change.column.column,
        "change_type": report.change.change_type.value,
        "detail": report.change.detail,
        "severity": report.severity,
        "breaks": report.breaks,
        "summary": report.summary(),
        "affected": [
            {"dataset": a.column.dataset_name, "column": a.column.column,
             "transform": a.transform, "hops": a.hops}
            for a in report.affected
        ],
    }


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "gemini": GeminiConfig().configured, "live_writeback": LIVE_WRITEBACK}


@app.get("/api/lineage")
def lineage() -> dict:
    return lineage_view()


@app.get("/api/scenarios")
def scenarios() -> list[dict]:
    return SCENARIOS


@app.post("/api/analyze")
def do_analyze(req: ChangeRequest) -> dict:
    return _serialize(_report(req))


@app.post("/api/narrate")
def do_narrate(req: ChangeRequest) -> dict:
    report = _report(req)
    if not GeminiConfig().configured:
        return {"available": False, "reason": "GEMINI_API_KEY not set"}
    exp = DriftNarrator().narrate(report)
    return {"available": True, "narrative": exp.narrative, "business_impact": exp.business_impact,
            "contract": exp.contract, "remediation": exp.remediation}


@app.post("/api/writeback")
async def do_writeback(req: ChangeRequest) -> dict:
    report = _report(req)
    if not report.breaks:
        return {"ok": True, "live": False, "columns_annotated": 0, "tags_written": 0,
                "details": ["no impact — nothing to write"]}
    if not LIVE_WRITEBACK:
        return {"ok": True, "live": False, "columns_annotated": len(report.affected),
                "tags_written": len(report.affected) * 2,
                "details": [f"(demo) would annotate {a.column}" for a in report.affected]}

    from engine.datahub_client import DataHubClient
    from engine.writer import DriftWriter

    client = DataHubClient(DataHubConfig(mutation_enabled=True))
    async with client.connect() as dh:
        result = await DriftWriter(dh).write(report)
    return {"ok": True, "live": True, "columns_annotated": result.columns_annotated,
            "tags_written": result.tags_written, "details": result.details}
