"""Core domain types for the impact engine (pure — no I/O)."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ChangeType(str, Enum):
    DROPPED = "dropped"      # column removed upstream
    RENAMED = "renamed"      # column renamed upstream
    RETYPED = "retyped"      # column's type/semantics changed (e.g. pct 0-100 -> 0-1)

    @property
    def severity(self) -> str:
        # Dropped/renamed break the transform outright; retyped miscomputes silently.
        return "silent_break" if self is ChangeType.RETYPED else "hard_break"


@dataclass(frozen=True)
class ColumnRef:
    dataset_urn: str
    column: str

    @property
    def dataset_name(self) -> str:
        # urn:li:dataset:(urn:li:dataPlatform:snowflake,broker.raw.collateral,PROD) -> broker.raw.collateral
        inner = self.dataset_urn.split(",")
        return inner[1] if len(inner) >= 2 else self.dataset_urn

    def __str__(self) -> str:
        return f"{self.dataset_name}.{self.column}"


@dataclass(frozen=True)
class SchemaChange:
    """A proposed/observed change to an upstream column."""

    column: ColumnRef
    change_type: ChangeType
    detail: str = ""

    @property
    def severity(self) -> str:
        return self.change_type.severity


@dataclass(frozen=True)
class AffectedColumn:
    column: ColumnRef            # the downstream (report) column that breaks
    transform: str               # how it was derived from the changed upstream
    hops: int                    # lineage distance from the change


@dataclass
class ImpactReport:
    change: SchemaChange
    affected: list[AffectedColumn] = field(default_factory=list)

    @property
    def breaks(self) -> bool:
        return bool(self.affected)

    @property
    def severity(self) -> str:
        return self.change.severity

    def summary(self) -> str:
        if not self.breaks:
            return f"No downstream impact from {self.change.change_type.value} of {self.change.column}."
        cols = ", ".join(sorted(str(a.column) for a in self.affected))
        return (
            f"{self.change.change_type.value.upper()} of {self.change.column} "
            f"[{self.severity}] breaks {len(self.affected)} report column(s): {cols}"
        )
