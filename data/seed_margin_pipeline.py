"""Seed a synthetic broker MARGIN-REPORT pipeline into DataHub, with column-level lineage.

This is the demo world for Compliance Drift Sentinel:

    raw.ledger ─┐
    raw.positions ─┼─▶ marts.margin_report   (column-level / fine-grained lineage)
    raw.collateral ─┘

The star of the break story is `raw.collateral.haircut_pct`: it feeds three report
columns (collateral_after_haircut, total_available_margin, margin_shortfall). If it is
dropped / renamed / re-typed upstream, the daily margin report silently misreports —
a regulatory breach. The impact engine (Slice 2) detects exactly that from the lineage.

Run: `./.venv/bin/python data/seed_margin_pipeline.py`  (needs local DataHub up).
"""
from __future__ import annotations

import os

from datahub.emitter.mce_builder import make_dataset_urn, make_schema_field_urn
from datahub.emitter.mcp import MetadataChangeProposalWrapper
from datahub.emitter.rest_emitter import DatahubRestEmitter
from datahub.metadata.schema_classes import (
    DatasetLineageTypeClass,
    DateTypeClass,
    FineGrainedLineageClass,
    FineGrainedLineageDownstreamTypeClass,
    FineGrainedLineageUpstreamTypeClass,
    NumberTypeClass,
    OtherSchemaClass,
    SchemaFieldClass,
    SchemaFieldDataTypeClass,
    SchemaMetadataClass,
    StringTypeClass,
    UpstreamClass,
    UpstreamLineageClass,
)

PLATFORM = "snowflake"
ENV = "PROD"
GMS = os.getenv("DATAHUB_GMS_URL", "http://localhost:8080")

# (name, [(field, type, native, description)])
_STR, _NUM, _DATE = "string", "number", "date"
TYPE_MAP = {_STR: StringTypeClass, _NUM: NumberTypeClass, _DATE: DateTypeClass}

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
    "broker.marts.margin_report": [
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

# downstream_col -> list of (upstream_dataset, upstream_col), plus a transform note.
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
        [
            ("broker.raw.ledger", "cash_balance"),
            ("broker.raw.collateral", "market_value"),
            ("broker.raw.collateral", "haircut_pct"),
        ],
        "cash_balance + market_value*(1 - haircut_pct/100)",
    ),
    "margin_shortfall": (
        [
            ("broker.raw.positions", "span_margin"),
            ("broker.raw.positions", "exposure_margin"),
            ("broker.raw.ledger", "cash_balance"),
            ("broker.raw.collateral", "market_value"),
            ("broker.raw.collateral", "haircut_pct"),
        ],
        "(span+exposure) - total_available_margin",
    ),
}

REPORT = "broker.marts.margin_report"


def urn(name: str) -> str:
    return make_dataset_urn(PLATFORM, name, ENV)


def schema_aspect(name: str, fields) -> SchemaMetadataClass:
    return SchemaMetadataClass(
        schemaName=name,
        platform=f"urn:li:dataPlatform:{PLATFORM}",
        version=0,
        hash="",
        platformSchema=OtherSchemaClass(rawSchema=""),
        fields=[
            SchemaFieldClass(
                fieldPath=fp,
                type=SchemaFieldDataTypeClass(type=TYPE_MAP[t]()),
                nativeDataType=native,
                description=desc,
                nullable=True,
            )
            for (fp, t, native, desc) in fields
        ],
    )


def lineage_aspect() -> UpstreamLineageClass:
    report_urn = urn(REPORT)
    upstream_tables = ["broker.raw.ledger", "broker.raw.positions", "broker.raw.collateral"]
    upstreams = [
        UpstreamClass(dataset=urn(t), type=DatasetLineageTypeClass.TRANSFORMED)
        for t in upstream_tables
    ]
    fine_grained = []
    for down_col, (up_cols, transform) in COLUMN_LINEAGE.items():
        fine_grained.append(
            FineGrainedLineageClass(
                upstreamType=FineGrainedLineageUpstreamTypeClass.FIELD_SET,
                downstreamType=FineGrainedLineageDownstreamTypeClass.FIELD,
                upstreams=[make_schema_field_urn(urn(ds), col) for (ds, col) in up_cols],
                downstreams=[make_schema_field_urn(report_urn, down_col)],
                transformOperation=transform,
                confidenceScore=1.0,
            )
        )
    return UpstreamLineageClass(upstreams=upstreams, fineGrainedLineages=fine_grained)


def main() -> None:
    emitter = DatahubRestEmitter(gms_server=GMS)
    for name, fields in DATASETS.items():
        emitter.emit_mcp(
            MetadataChangeProposalWrapper(entityUrn=urn(name), aspect=schema_aspect(name, fields))
        )
        print(f"emitted schema: {name} ({len(fields)} cols)")
    emitter.emit_mcp(
        MetadataChangeProposalWrapper(entityUrn=urn(REPORT), aspect=lineage_aspect())
    )
    print(f"emitted column-level lineage into {REPORT} "
          f"({len(COLUMN_LINEAGE)} report cols, {len(DATASETS) - 1} source tables)")


if __name__ == "__main__":
    main()
