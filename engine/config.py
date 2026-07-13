"""Runtime config for DataHub (MCP) and the Gemini narrator."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _load_dotenv(filename: str = ".env") -> None:
    """Minimal .env loader (no dependency); existing env vars win."""
    path = Path(__file__).resolve().parent.parent / filename
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


_load_dotenv()


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


@dataclass(frozen=True)
class GeminiConfig:
    api_key: str = os.getenv("GEMINI_API_KEY", "")
    # Alias model so a version deprecation (as happened to gemini-2.5-flash) won't break us.
    model: str = os.getenv("GEMINI_MODEL", "gemini-flash-latest")

    @property
    def configured(self) -> bool:
        return bool(self.api_key)
