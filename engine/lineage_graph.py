"""Column-level lineage graph, built from DataHub's fine-grained lineage aspect.

Pure graph + a `from_datahub` loader. The graph maps upstream columns to the downstream
columns derived from them, so the impact engine can traverse "what breaks if X changes".
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

from engine.models import ColumnRef


def column_urn(dataset_urn: str, column: str) -> str:
    """schemaField urn, matching DataHub's `make_schema_field_urn`."""
    return f"urn:li:schemaField:({dataset_urn},{column})"


def parse_column_urn(sf_urn: str) -> ColumnRef:
    """Split `urn:li:schemaField:(<dataset_urn>,<column>)` on the top-level comma.

    The dataset urn itself contains parens and commas, so we scan at paren depth.
    """
    prefix = "urn:li:schemaField:("
    if not sf_urn.startswith(prefix) or not sf_urn.endswith(")"):
        raise ValueError(f"not a schemaField urn: {sf_urn}")
    inner = sf_urn[len(prefix):-1]
    depth = 0
    for i, ch in enumerate(inner):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif ch == "," and depth == 0:
            return ColumnRef(dataset_urn=inner[:i], column=inner[i + 1:])
    raise ValueError(f"no top-level column separator in: {sf_urn}")


@dataclass
class ColumnLineageGraph:
    # upstream schemaField urn -> list of (downstream schemaField urn, transform)
    _edges: dict[str, list[tuple[str, str]]] = field(default_factory=dict)

    def add_edge(self, upstream_urn: str, downstream_urn: str, transform: str = "") -> None:
        self._edges.setdefault(upstream_urn, []).append((downstream_urn, transform))

    def downstream_of(self, upstream_urn: str) -> list[tuple[ColumnRef, str, int]]:
        """BFS over transitive downstreams. Returns (column, transform, hops), nearest first."""
        seen: set[str] = set()
        out: list[tuple[ColumnRef, str, int]] = []
        queue: deque[tuple[str, str, int]] = deque(
            (down, tf, 1) for (down, tf) in self._edges.get(upstream_urn, [])
        )
        while queue:
            urn, transform, hops = queue.popleft()
            if urn in seen:
                continue
            seen.add(urn)
            out.append((parse_column_urn(urn), transform, hops))
            for (down, tf) in self._edges.get(urn, []):
                queue.append((down, tf, hops + 1))
        return out

    @classmethod
    def from_fine_grained(cls, fine_grained) -> "ColumnLineageGraph":
        """Build from a list of FineGrainedLineage aspects (or duck-typed equivalents)."""
        g = cls()
        for fg in fine_grained or []:
            transform = getattr(fg, "transformOperation", "") or ""
            for down in getattr(fg, "downstreams", None) or []:
                for up in getattr(fg, "upstreams", None) or []:
                    g.add_edge(up, down, transform)
        return g

    @classmethod
    def from_datahub(cls, graph, report_urn: str) -> "ColumnLineageGraph":
        """Read the report's UpstreamLineage aspect from a live DataHub graph client."""
        from datahub.metadata.schema_classes import UpstreamLineageClass

        aspect = graph.get_aspect(entity_urn=report_urn, aspect_type=UpstreamLineageClass)
        if aspect is None:
            return cls()
        return cls.from_fine_grained(aspect.fineGrainedLineages)
