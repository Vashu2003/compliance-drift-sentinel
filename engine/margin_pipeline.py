"""Single source of truth for the demo margin pipeline.

Both the DataHub seeder (`data/seed_margin_pipeline.py`) and the API build from this, so the
lineage the app shows always matches the lineage seeded into DataHub. Lets the API compute
impact + serve the graph WITHOUT a live DataHub (needed for the free-tier deployed demo);
only write-back needs the live instance.
"""
from __future__ import annotations

from engine.lineage_graph import ColumnLineageGraph, column_urn
from engine.models import ChangeType

PLATFORM = "snowflake"
ENV = "PROD"
REPORT = "broker.marts.margin_report"

_STR, _NUM, _DATE = "string", "number", "date"

# dataset -> [(field, type, native, description)]
DATASETS: dict[str, list[tuple[str, str, str, str]]] = {
    "broker.raw.ledger": [
        ("client_id", _STR, "VARCHAR", "Broker client code"),
        ("as_of_date", _DATE, "DATE", "Ledger snapshot date"),
        ("cash_balance", _NUM, "NUMBER(18,2)", "Free cash balance"),
        ("currency", _STR, "VARCHAR", "ISO currency"),
    ],
    "broker.raw.positions": [
        ("client_id", _STR, "VARCHAR", "Broker client code"),
        ("symbol", _STR, "VARCHAR", "Instrument symbol"),
        ("quantity", _NUM, "NUMBER(18,4)", "Open quantity"),
        ("avg_price", _NUM, "NUMBER(18,4)", "Average traded price"),
        ("mtm_price", _NUM, "NUMBER(18,4)", "Mark-to-market price"),
        ("span_margin", _NUM, "NUMBER(18,2)", "SPAN margin requirement"),
        ("exposure_margin", _NUM, "NUMBER(18,2)", "Exposure margin requirement"),
    ],
    "broker.raw.collateral": [
        ("client_id", _STR, "VARCHAR", "Broker client code"),
        ("security", _STR, "VARCHAR", "Pledged security"),
        ("market_value", _NUM, "NUMBER(18,2)", "Pledged market value"),
        ("haircut_pct", _NUM, "NUMBER(5,2)", "Haircut percentage (0-100)"),
    ],
    REPORT: [
        ("client_id", _STR, "VARCHAR", "Broker client code"),
        ("report_date", _DATE, "DATE", "Margin report date"),
        ("cash_margin", _NUM, "NUMBER(18,2)", "Cash available toward margin"),
        ("span_margin", _NUM, "NUMBER(18,2)", "SPAN margin requirement"),
        ("exposure_margin", _NUM, "NUMBER(18,2)", "Exposure margin requirement"),
        ("collateral_after_haircut", _NUM, "NUMBER(18,2)", "Collateral value net of haircut"),
        ("total_available_margin", _NUM, "NUMBER(18,2)", "Total margin available"),
        ("margin_shortfall", _NUM, "NUMBER(18,2)", "Shortfall vs requirement"),
    ],
}

# report column -> ([(source_dataset, source_column), ...], transform)
COLUMN_LINEAGE: dict[str, tuple[list[tuple[str, str]], str]] = {
    "client_id": ([("broker.raw.ledger", "client_id")], "passthrough"),
    "report_date": ([("broker.raw.ledger", "as_of_date")], "passthrough"),
    "cash_margin": ([("broker.raw.ledger", "cash_balance")], "cash available"),
    "span_margin": ([("broker.raw.positions", "span_margin")], "passthrough"),
    "exposure_margin": ([("broker.raw.positions", "exposure_margin")], "passthrough"),
    "collateral_after_haircut": (
        [("broker.raw.collateral", "market_value"), ("broker.raw.collateral", "haircut_pct")],
        "market_value * (1 - haircut_pct/100)",
    ),
    "total_available_margin": (
        [("broker.raw.ledger", "cash_balance"), ("broker.raw.collateral", "market_value"),
         ("broker.raw.collateral", "haircut_pct")],
        "cash_balance + market_value*(1 - haircut_pct/100)",
    ),
    "margin_shortfall": (
        [("broker.raw.positions", "span_margin"), ("broker.raw.positions", "exposure_margin"),
         ("broker.raw.ledger", "cash_balance"), ("broker.raw.collateral", "market_value"),
         ("broker.raw.collateral", "haircut_pct")],
        "(span+exposure) - total_available_margin",
    ),
}


def dataset_urn(name: str) -> str:
    return f"urn:li:dataset:(urn:li:dataPlatform:{PLATFORM},{name},{ENV})"


REPORT_URN = dataset_urn(REPORT)


def build_column_graph() -> ColumnLineageGraph:
    """The same column graph DataHub stores — built in-process (no live DataHub needed)."""
    g = ColumnLineageGraph()
    for down_col, (up_cols, transform) in COLUMN_LINEAGE.items():
        for ds, col in up_cols:
            g.add_edge(column_urn(dataset_urn(ds), col), column_urn(REPORT_URN, down_col), transform)
    return g


def lineage_view() -> dict:
    """Nodes + edges for the frontend lineage graph."""
    datasets = [
        {
            "name": name,
            "urn": dataset_urn(name),
            "role": "report" if name == REPORT else "source",
            "columns": [
                {"name": f, "type": t, "native": native, "description": desc}
                for (f, t, native, desc) in fields
            ],
        }
        for name, fields in DATASETS.items()
    ]
    edges, seen_ds = [], set()
    for down_col, (up_cols, transform) in COLUMN_LINEAGE.items():
        for ds, col in up_cols:
            edges.append({
                "source_dataset": ds, "source_column": col,
                "target_dataset": REPORT, "target_column": down_col, "transform": transform,
            })
            seen_ds.add(ds)
    dataset_edges = [{"source": ds, "target": REPORT} for ds in DATASETS if ds in seen_ds]
    return {"datasets": datasets, "column_edges": edges, "dataset_edges": dataset_edges,
            "report": REPORT}


# Predefined upstream-change scenarios the operator can trigger.
SCENARIOS = [
    {"id": "haircut_retype", "label": "Retype collateral.haircut_pct (pct → fraction)",
     "dataset": "broker.raw.collateral", "column": "haircut_pct",
     "change_type": ChangeType.RETYPED.value,
     "detail": "Upstream changed haircut_pct from percent (0-100) to fraction (0-1)."},
    {"id": "haircut_drop", "label": "Drop collateral.haircut_pct",
     "dataset": "broker.raw.collateral", "column": "haircut_pct",
     "change_type": ChangeType.DROPPED.value,
     "detail": "Upstream team removed collateral.haircut_pct."},
    {"id": "market_value_drop", "label": "Drop collateral.market_value",
     "dataset": "broker.raw.collateral", "column": "market_value",
     "change_type": ChangeType.DROPPED.value, "detail": "collateral.market_value removed."},
    {"id": "cash_rename", "label": "Rename ledger.cash_balance",
     "dataset": "broker.raw.ledger", "column": "cash_balance",
     "change_type": ChangeType.RENAMED.value, "detail": "ledger.cash_balance renamed to cash_bal."},
    {"id": "currency_drop", "label": "Drop ledger.currency (no downstream use)",
     "dataset": "broker.raw.ledger", "column": "currency",
     "change_type": ChangeType.DROPPED.value, "detail": "ledger.currency removed."},
]
