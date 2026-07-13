"""Runtime config for talking to DataHub via the MCP server."""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class DataHubConfig:
    gms_url: str = os.getenv("DATAHUB_GMS_URL", "http://localhost:8080")
    gms_token: str = os.getenv("DATAHUB_GMS_TOKEN", "")
    # Write-back tools are OFF by default in the MCP server; enable explicitly for Slice 3.
    mutation_enabled: bool = os.getenv("TOOLS_IS_MUTATION_ENABLED", "false").lower() == "true"

    def mcp_env(self) -> dict[str, str]:
        """Environment passed to the `uvx mcp-server-datahub` subprocess."""
        return {
            **os.environ,
            "DATAHUB_GMS_URL": self.gms_url,
            "DATAHUB_GMS_TOKEN": self.gms_token,
            "TOOLS_IS_MUTATION_ENABLED": "true" if self.mutation_enabled else "false",
        }
