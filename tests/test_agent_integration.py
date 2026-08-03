"""Slice 4 test — the Gemini narrator, grounded in engine facts.

Pure (in-memory lineage) + one live Gemini call. Skipped if GEMINI_API_KEY is absent.
"""
import pytest

from engine.agent import DriftExplanation, DriftNarrator, NarrationUnavailable
from engine.config import GeminiConfig
from engine.impact import analyze
from engine.lineage_graph import ColumnLineageGraph, column_urn
from engine.models import ChangeType, ColumnRef, SchemaChange

COLL = "urn:li:dataset:(urn:li:dataPlatform:snowflake,broker.raw.collateral,PROD)"
REPORT = "urn:li:dataset:(urn:li:dataPlatform:snowflake,broker.marts.margin_report,PROD)"

pytestmark = pytest.mark.skipif(
    not GeminiConfig().configured, reason="GEMINI_API_KEY not set"
)


@pytest.fixture
def haircut_report():
    g = ColumnLineageGraph()
    for down, tf in [
        ("collateral_after_haircut", "market_value*(1-haircut_pct/100)"),
        ("total_available_margin", "cash + collateral_after_haircut"),
        ("margin_shortfall", "(span+exposure) - total_available_margin"),
    ]:
        g.add_edge(column_urn(COLL, "haircut_pct"), column_urn(REPORT, down), tf)
    return analyze(
        SchemaChange(ColumnRef(COLL, "haircut_pct"), ChangeType.RETYPED,
                     detail="haircut_pct pct(0-100) -> fraction(0-1)"),
        g,
    )


@pytest.mark.integration
def test_narrator_returns_grounded_explanation(haircut_report):
    try:
        exp = DriftNarrator().narrate(haircut_report)
    except NarrationUnavailable as exc:
        if exc.status == 429:
            # The free tier allows only 20 generateContent calls per project per DAY, so this
            # live test is expected to be unrunnable once the day's budget is spent. Quota
            # exhaustion is an environment condition, not a regression — skip, don't fail.
            pytest.skip(f"Gemini quota exhausted: {exc.reason}")
        raise

    assert isinstance(exp, DriftExplanation)
    assert exp.narrative and exp.contract and exp.remediation
    # Grounded in the fact we supplied (the changed column), not hallucinated.
    blob = f"{exp.narrative} {exp.contract}".lower()
    assert "haircut_pct" in blob


@pytest.mark.integration
def test_narrator_no_impact_short_circuits(haircut_report):
    # An empty report must not spend a Gemini call.
    from engine.models import ImpactReport

    empty = ImpactReport(change=haircut_report.change, affected=[])
    exp = DriftNarrator().narrate(empty)
    assert exp.contract == ""
