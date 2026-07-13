"""Async client over the DataHub MCP server.

Only wraps calls verified end-to-end against a live DataHub v1.5 / mcp-server-datahub v0.6.0:
`search` and `get_lineage` (table- and column-level). Shapes confirmed via scripts/probe_lineage.py.
"""
from __future__ import annotations

import json
from contextlib import asynccontextmanager
from dataclasses import dataclass

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from engine.config import DataHubConfig


@dataclass(frozen=True)
class LineageNode:
    """One node in a lineage result (an upstream or downstream entity)."""

    urn: str
    entity_type: str  # e.g. DATASET, DATA_JOB
    degree: int       # hops from the queried entity

    @property
    def is_dataset(self) -> bool:
        return self.entity_type == "DATASET"


def _text(result) -> str:
    return result.content[0].text if result.content else ""


class DataHubClient:
    """Spawns `uvx mcp-server-datahub` over stdio and exposes typed lineage reads.

    Usage:
        async with DataHubClient().connect() as dh:
            ups = await dh.upstreams(urn)
    """

    def __init__(self, config: DataHubConfig | None = None) -> None:
        self.config = config or DataHubConfig()
        self._session: ClientSession | None = None

    @asynccontextmanager
    async def connect(self):
        params = StdioServerParameters(
            command="uvx", args=["mcp-server-datahub"], env=self.config.mcp_env()
        )
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                self._session = session
                try:
                    yield self
                finally:
                    self._session = None

    async def _call(self, tool: str, args: dict) -> dict:
        if self._session is None:
            raise RuntimeError("DataHubClient must be used inside `async with client.connect()`")
        raw = _text(await self._session.call_tool(tool, args))
        return json.loads(raw) if raw else {}

    async def search_datasets(self, query: str = "*", limit: int = 20) -> list[str]:
        data = await self._call("search", {"query": query})
        return [
            r["entity"]["urn"]
            for r in data.get("searchResults", [])
            if r["entity"]["urn"].startswith("urn:li:dataset")
        ][:limit]

    async def get_lineage(
        self,
        urn: str,
        *,
        upstream: bool = True,
        column: str | None = None,
        max_hops: int = 1,
    ) -> list[LineageNode]:
        """Return upstream (default) or downstream lineage nodes.

        Pass `column` for column-level lineage; leave None for dataset-level.
        """
        data = await self._call(
            "get_lineage",
            {"urn": urn, "upstream": upstream, "column": column, "max_hops": max_hops},
        )
        key = "upstreams" if upstream else "downstreams"
        results = data.get(key, {}).get("searchResults", [])
        return [
            LineageNode(
                urn=r["entity"]["urn"],
                entity_type=r["entity"].get("type", "UNKNOWN"),
                degree=int(r.get("degree", 1)),
            )
            for r in results
        ]

    async def upstreams(self, urn: str, **kw) -> list[LineageNode]:
        return await self.get_lineage(urn, upstream=True, **kw)

    async def downstreams(self, urn: str, **kw) -> list[LineageNode]:
        return await self.get_lineage(urn, upstream=False, **kw)
