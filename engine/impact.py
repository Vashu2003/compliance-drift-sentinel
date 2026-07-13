"""The deterministic impact engine: given an upstream schema change, which report columns break?"""
from __future__ import annotations

from engine.lineage_graph import ColumnLineageGraph, column_urn
from engine.models import AffectedColumn, ImpactReport, SchemaChange


def analyze(change: SchemaChange, graph: ColumnLineageGraph) -> ImpactReport:
    """Trace the changed upstream column through column lineage to affected report columns."""
    changed_urn = column_urn(change.column.dataset_urn, change.column.column)
    affected = [
        AffectedColumn(column=col, transform=transform, hops=hops)
        for (col, transform, hops) in graph.downstream_of(changed_urn)
    ]
    return ImpactReport(change=change, affected=affected)
