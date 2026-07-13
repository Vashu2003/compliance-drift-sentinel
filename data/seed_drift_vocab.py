"""Provision the DataHub vocabulary the Sentinel writes back with (idempotent).

Creates:
- tag entities `drift-at-risk`, `drift-hard-break`, `drift-silent-break`
- a structured property `drift_status` applicable to schemaFields + datasets

Must run once before write-back (Slice 3). Safe to re-run.
"""
from __future__ import annotations

import os

from datahub.emitter.mcp import MetadataChangeProposalWrapper
from datahub.emitter.rest_emitter import DatahubRestEmitter
from datahub.metadata.schema_classes import (
    StructuredPropertyDefinitionClass,
    TagPropertiesClass,
)

GMS = os.getenv("DATAHUB_GMS_URL", "http://localhost:8080")

TAGS = {
    "drift-at-risk": "Column depends on an upstream that is changing; verify before it breaks.",
    "drift-hard-break": "Upstream change (drop/rename) will break this column outright.",
    "drift-silent-break": "Upstream retype will silently miscompute this column (no error).",
}

DRIFT_STATUS_URN = "urn:li:structuredProperty:drift_status"


def main() -> None:
    emitter = DatahubRestEmitter(gms_server=GMS)

    for name, desc in TAGS.items():
        emitter.emit_mcp(
            MetadataChangeProposalWrapper(
                entityUrn=f"urn:li:tag:{name}",
                aspect=TagPropertiesClass(name=name, description=desc),
            )
        )
        print(f"tag ready: urn:li:tag:{name}")

    emitter.emit_mcp(
        MetadataChangeProposalWrapper(
            entityUrn=DRIFT_STATUS_URN,
            aspect=StructuredPropertyDefinitionClass(
                qualifiedName="drift_status",
                displayName="Drift Status",
                valueType="urn:li:dataType:datahub.string",
                cardinality="SINGLE",
                entityTypes=[
                    "urn:li:entityType:datahub.schemaField",
                    "urn:li:entityType:datahub.dataset",
                ],
                description="Set by Compliance Drift Sentinel when an upstream change threatens this field.",
            ),
        )
    )
    print(f"structured property ready: {DRIFT_STATUS_URN}")


if __name__ == "__main__":
    main()
