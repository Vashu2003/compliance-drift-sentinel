"""Seed the synthetic broker MARGIN-REPORT pipeline into DataHub, with column-level lineage.

Pipeline definition lives in engine/margin_pipeline.py (shared with the API). This script only
emits it to DataHub. Star of the break story: raw.collateral.haircut_pct feeds three report
columns (collateral_after_haircut, total_available_margin, margin_shortfall).

Run: `./.venv/bin/python data/seed_margin_pipeline.py`  (needs local DataHub up).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datahub.emitter.mce_builder import make_schema_field_urn
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

from engine.margin_pipeline import (
    COLUMN_LINEAGE,
    DATASETS,
    PLATFORM,
    REPORT,
    REPORT_URN,
    dataset_urn,
)

GMS = os.getenv("DATAHUB_GMS_URL", "http://localhost:8080")
TYPE_MAP = {"string": StringTypeClass, "number": NumberTypeClass, "date": DateTypeClass}


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
    upstream_tables = {ds for (up, _t) in COLUMN_LINEAGE.values() for (ds, _c) in up}
    upstreams = [
        UpstreamClass(dataset=dataset_urn(t), type=DatasetLineageTypeClass.TRANSFORMED)
        for t in sorted(upstream_tables)
    ]
    fine_grained = [
        FineGrainedLineageClass(
            upstreamType=FineGrainedLineageUpstreamTypeClass.FIELD_SET,
            downstreamType=FineGrainedLineageDownstreamTypeClass.FIELD,
            upstreams=[make_schema_field_urn(dataset_urn(ds), col) for (ds, col) in up_cols],
            downstreams=[make_schema_field_urn(REPORT_URN, down_col)],
            transformOperation=transform,
            confidenceScore=1.0,
        )
        for down_col, (up_cols, transform) in COLUMN_LINEAGE.items()
    ]
    return UpstreamLineageClass(upstreams=upstreams, fineGrainedLineages=fine_grained)


def main() -> None:
    emitter = DatahubRestEmitter(gms_server=GMS)
    for name, fields in DATASETS.items():
        emitter.emit_mcp(
            MetadataChangeProposalWrapper(entityUrn=dataset_urn(name), aspect=schema_aspect(name, fields))
        )
        print(f"emitted schema: {name} ({len(fields)} cols)")
    emitter.emit_mcp(MetadataChangeProposalWrapper(entityUrn=REPORT_URN, aspect=lineage_aspect()))
    print(f"emitted column-level lineage into {REPORT} "
          f"({len(COLUMN_LINEAGE)} report cols, {len(DATASETS) - 1} source tables)")


if __name__ == "__main__":
    main()
