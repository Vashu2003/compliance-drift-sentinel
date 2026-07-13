"""Slice 3 — write drift findings back to the DataHub graph.

For each affected report column the Sentinel writes (all via the MCP mutation tools, so it
contributes back through the same interface it reads):
  1. a tag  (`drift-at-risk` + severity tag)
  2. a `drift_status` structured property (the offending upstream change)
  3. a replaced column description carrying the auto-proposed data contract

Run `data/seed_drift_vocab.py` once first to provision the tags + property.
"""
from __future__ import annotations

from dataclasses import dataclass

from engine.datahub_client import DataHubClient
from engine.models import AffectedColumn, ImpactReport

DRIFT_STATUS_PROPERTY = "urn:li:structuredProperty:drift_status"
TAG_AT_RISK = "urn:li:tag:drift-at-risk"
SEVERITY_TAG = {
    "hard_break": "urn:li:tag:drift-hard-break",
    "silent_break": "urn:li:tag:drift-silent-break",
}
CONTRACT_MARKER = "⚠️ DRIFT SENTINEL CONTRACT"


@dataclass
class WriteResult:
    columns_annotated: int
    tags_written: int
    details: list[str]


def _status_text(report: ImpactReport) -> str:
    c = report.change
    return f"AT_RISK [{report.severity}]: {c.column} {c.change_type.value}" + (
        f" — {c.detail}" if c.detail else ""
    )


def _contract_note(report: ImpactReport, affected: AffectedColumn) -> str:
    c = report.change
    return (
        f"{CONTRACT_MARKER}: `{affected.column}` is derived via `{affected.transform}` and "
        f"depends on `{c.column}`. Contract: `{c.column}` must exist and keep its type/semantics; "
        f"a {c.change_type.value} upstream would cause a {report.severity} here."
    )


class DriftWriter:
    """Persists an ImpactReport into DataHub as tags + property + contract description."""

    def __init__(self, client: DataHubClient) -> None:
        self.client = client

    async def write(self, report: ImpactReport) -> WriteResult:
        if not report.breaks:
            return WriteResult(0, 0, ["no impact — nothing written"])

        severity_tag = SEVERITY_TAG[report.severity]
        details: list[str] = []
        tags_written = 0

        for affected in report.affected:
            ds, col = affected.column.dataset_urn, affected.column.column

            await self.client.add_column_tags(ds, col, [TAG_AT_RISK, severity_tag])
            tags_written += 2

            await self.client.set_column_structured_property(
                ds, col, DRIFT_STATUS_PROPERTY, [_status_text(report)]
            )
            await self.client.set_column_description(
                ds, col, _contract_note(report, affected), operation="replace"
            )
            details.append(f"annotated {affected.column} ({report.severity})")

        return WriteResult(
            columns_annotated=len(report.affected),
            tags_written=tags_written,
            details=details,
        )
