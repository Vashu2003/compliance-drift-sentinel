"""Probe: inspect the real input/output shapes of the MCP lineage tools.

Run before writing the client so the wrapper is built against verified shapes.
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
    "TOOLS_IS_MUTATION_ENABLED": "true",
}
PARAMS = StdioServerParameters(command="uvx", args=["mcp-server-datahub"], env=ENV)


def _text(res):
    return res.content[0].text if res.content else ""


async def main():
    async with stdio_client(PARAMS) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = {t.name: t for t in (await session.list_tools()).tools}

            for name in ("get_lineage", "get_lineage_paths_between", "list_schema_fields"):
                t = tools[name]
                print(f"\n===== {name} =====")
                print("description:", (t.description or "")[:300])
                print("inputSchema:", json.dumps(t.inputSchema, indent=2)[:900])

            # Find a dataset that actually has lineage.
            search = json.loads(_text(await session.call_tool("search", {"query": "*"})))
            urns = [r["entity"]["urn"] for r in search.get("searchResults", [])
                    if r["entity"]["urn"].startswith("urn:li:dataset")]
            print("\nCandidate dataset urns:", urns[:8])

            for urn in urns[:8]:
                try:
                    res = _text(await session.call_tool("get_lineage", {"urn": urn}))
                except Exception as e:
                    print(f"get_lineage FAILED for {urn}: {e}")
                    continue
                if res and res.strip() not in ("{}", "[]"):
                    print(f"\n----- get_lineage({urn}) -----")
                    print(res[:1200])
                    break


if __name__ == "__main__":
    asyncio.run(main())
