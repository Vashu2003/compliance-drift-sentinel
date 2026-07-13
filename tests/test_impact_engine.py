"""Unit tests for the deterministic impact engine (pure — no DataHub)."""
import pytest

from engine.impact import analyze
from engine.lineage_graph import ColumnLineageGraph, column_urn, parse_column_urn
from engine.models import ChangeType, ColumnRef, SchemaChange

COLL = "urn:li:dataset:(urn:li:dataPlatform:snowflake,broker.raw.collateral,PROD)"
LEDGER = "urn:li:dataset:(urn:li:dataPlatform:snowflake,broker.raw.ledger,PROD)"
REPORT = "urn:li:dataset:(urn:li:dataPlatform:snowflake,broker.marts.margin_report,PROD)"


@pytest.fixture
def margin_graph() -> ColumnLineageGraph:
    g = ColumnLineageGraph()
    for down, tf in [
        ("collateral_after_haircut", "market_value*(1-haircut_pct/100)"),
        ("total_available_margin", "cash + collateral_after_haircut"),
        ("margin_shortfall", "(span+exposure) - total_available_margin"),
    ]:
        g.add_edge(column_urn(COLL, "haircut_pct"), column_urn(REPORT, down), tf)
    g.add_edge(column_urn(LEDGER, "cash_balance"), column_urn(REPORT, "cash_margin"), "passthrough")
    return g


def test_parse_column_urn_roundtrip():
    ref = parse_column_urn(column_urn(COLL, "haircut_pct"))
    assert ref == ColumnRef(COLL, "haircut_pct")
    assert ref.dataset_name == "broker.raw.collateral"
    assert str(ref) == "broker.raw.collateral.haircut_pct"


def test_dropped_haircut_breaks_three_report_columns(margin_graph):
    change = SchemaChange(ColumnRef(COLL, "haircut_pct"), ChangeType.DROPPED)
    report = analyze(change, margin_graph)

    assert report.breaks
    assert report.severity == "hard_break"
    cols = {str(a.column) for a in report.affected}
    assert cols == {
        "broker.marts.margin_report.collateral_after_haircut",
        "broker.marts.margin_report.total_available_margin",
        "broker.marts.margin_report.margin_shortfall",
    }


def test_retype_is_silent_break(margin_graph):
    change = SchemaChange(ColumnRef(COLL, "haircut_pct"), ChangeType.RETYPED,
                          detail="pct 0-100 -> fraction 0-1")
    report = analyze(change, margin_graph)
    assert report.breaks
    assert report.severity == "silent_break"  # the dangerous one: miscomputes, no error


def test_unrelated_column_has_no_impact(margin_graph):
    change = SchemaChange(ColumnRef(LEDGER, "currency"), ChangeType.DROPPED)
    report = analyze(change, margin_graph)
    assert not report.breaks
    assert "No downstream impact" in report.summary()


def test_transitive_multi_hop():
    a = "urn:li:dataset:(urn:li:dataPlatform:snowflake,db.a,PROD)"
    b = "urn:li:dataset:(urn:li:dataPlatform:snowflake,db.b,PROD)"
    c = "urn:li:dataset:(urn:li:dataPlatform:snowflake,db.c,PROD)"
    g = ColumnLineageGraph()
    g.add_edge(column_urn(a, "x"), column_urn(b, "y"), "y=f(x)")
    g.add_edge(column_urn(b, "y"), column_urn(c, "z"), "z=g(y)")

    report = analyze(SchemaChange(ColumnRef(a, "x"), ChangeType.DROPPED), g)
    by_col = {str(x.column): x.hops for x in report.affected}
    assert by_col == {"db.b.y": 1, "db.c.z": 2}
