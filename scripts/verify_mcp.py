"""Slice 0 verification: prove the DataHub MCP server talks to our local OSS instance.

Runs `uvx mcp-server-datahub` over stdio with mutations ENABLED, lists the tools,
and calls `search` to confirm end-to-end connectivity to GMS at localhost:8080.
"""
import asyncio
import json
import os

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ENV = {
    **os.environ,
    "DATAHUB_GMS_URL": "http://localhost:8080",
    "DATAHUB_GMS_TOKEN": "",
    "TOOLS_IS_MUTATION_ENABLED": "true",  # we NEED write-back for the Sentinel
}

PARAMS = StdioServerParameters(
    command="uvx", args=["mcp-server-datahub"], env=ENV
)


async def main():
    async with stdio_client(PARAMS) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            names = sorted(t.name for t in tools.tools)
            print(f"TOOLS ({len(names)}):", ", ".join(names))

            has_lineage = "get_lineage" in names
            has_mutation = any(m in names for m in ("add_tags", "add_structured_properties", "update_description"))
            print("get_lineage present:", has_lineage)
            print("mutation tools present (write-back path):", has_mutation)

            # Real GMS round-trip: search the catalog.
            res = await session.call_tool("search", {"query": "*"})
            text = res.content[0].text if res.content else ""
            print("search round-trip OK, sample bytes:", len(text))
            print("SEARCH SNIPPET:", text[:300].replace("\n", " "))

            print("\nSLICE 0 RESULT:",
                  "PASS" if (has_lineage and has_mutation and text) else "PARTIAL")


if __name__ == "__main__":
    asyncio.run(main())
