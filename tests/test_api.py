"""Slice 5 backend tests — FastAPI endpoints (no live DataHub needed)."""
import pytest
from fastapi.testclient import TestClient

import app.main as api
from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200 and r.json()["ok"] is True


def test_lineage_shape():
    data = client.get("/api/lineage").json()
    names = {d["name"] for d in data["datasets"]}
    assert "broker.marts.margin_report" in names
    assert len(data["datasets"]) == 4
    # column edge from the star column exists
    assert any(e["source_column"] == "haircut_pct" for e in data["column_edges"])


def test_scenarios_include_headline():
    ids = {s["id"] for s in client.get("/api/scenarios").json()}
    assert {"haircut_retype", "haircut_drop", "currency_drop"} <= ids


def test_analyze_retype_is_silent_break_on_three_columns():
    r = client.post("/api/analyze", json={
        "dataset": "broker.raw.collateral", "column": "haircut_pct",
        "change_type": "retyped", "detail": "pct->fraction"})
    body = r.json()
    assert body["severity"] == "silent_break"
    assert {a["column"] for a in body["affected"]} == {
        "collateral_after_haircut", "total_available_margin", "margin_shortfall"}


def test_analyze_no_impact_column():
    r = client.post("/api/analyze", json={
        "dataset": "broker.raw.ledger", "column": "currency", "change_type": "dropped"})
    assert r.json()["breaks"] is False


def test_writeback_demo_mode(monkeypatch):
    monkeypatch.setattr(api, "LIVE_WRITEBACK", False)
    r = client.post("/api/writeback", json={
        "dataset": "broker.raw.collateral", "column": "haircut_pct", "change_type": "dropped"})
    body = r.json()
    assert body["ok"] is True and body["live"] is False
    assert body["columns_annotated"] == 3
