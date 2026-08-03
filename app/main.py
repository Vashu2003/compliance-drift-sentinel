"""FastAPI backend for the Drift Sentinel UI.

Impact analysis + lineage + narration run in-process (no live DataHub needed → deployable on a
free tier). Write-back hits the live DataHub via MCP; when it can't (deployed demo), it returns
a simulated result flagged `live: false`.
"""
from __future__ import annotations

import json
import os
import pathlib

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from engine.agent import DriftNarrator, NarrationUnavailable
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

# There are only a handful of scenarios, and narration for a given change is deterministic
# enough to reuse. Caching it keeps repeat visitors (judges clicking through the demo) from
# spending a Gemini call every time — the free tier rate-limits after a couple of requests.
_NARRATION_CACHE: dict[tuple[str, str, str], dict] = {}


def _load_prebaked() -> dict[tuple[str, str, str], dict]:
    """Narrations generated once by scripts/prebake_narrations.py.

    The Gemini free tier allows 20 calls per project per DAY across all visitors, and a Render
    free-tier cold start wipes the in-process cache — so a live-only demo can run out of
    narration mid-judging. Serving pre-baked (still genuinely Gemini-authored) text makes the
    deployed demo independent of that quota. Absent file → falls straight through to live.
    """
    path = pathlib.Path(__file__).resolve().parent.parent / "data" / "narrations.json"
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text())
    except (OSError, ValueError):
        return {}
    out = {}
    for k, v in raw.items():
        parts = k.split("|")
        if len(parts) == 3:
            out[(parts[0], parts[1], parts[2])] = v
    return out


_PREBAKED = _load_prebaked()


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

    key = (req.dataset, req.column, req.change_type)
    if key in _NARRATION_CACHE:
        return _NARRATION_CACHE[key]
    if key in _PREBAKED:
        return _PREBAKED[key]

    try:
        exp = DriftNarrator().narrate(report)
    except NarrationUnavailable as exc:
        # Degrade instead of raising: an unhandled exception returns a bare 500, which
        # Starlette's CORS middleware does not attach headers to — the browser then reports a
        # misleading CORS error and the UI panel silently blanks. A 200 with available=false
        # lets the client say what actually went wrong.
        return {"available": False, "reason": exc.reason}

    payload = {"available": True, "narrative": exp.narrative,
               "business_impact": exp.business_impact, "contract": exp.contract,
               "remediation": exp.remediation}
    _NARRATION_CACHE[key] = payload
    return payload


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
