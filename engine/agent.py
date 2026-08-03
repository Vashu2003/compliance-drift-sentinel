"""Slice 4 — the Gemini narrator.

The deterministic engine has already decided WHAT breaks. Gemini's only job is to explain the
risk in plain English and draft a concrete data contract — grounded strictly in the facts we
give it, never inventing impact. This keeps correctness in the engine and uses the LLM for
what it's good at: prose and phrasing.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

import httpx

from engine.config import GeminiConfig
from engine.models import ImpactReport

_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


class NarrationUnavailable(RuntimeError):
    """Gemini could not be reached or refused the request.

    Carries a human-readable reason and never the request URL — httpx puts the API key in the
    query string, so its stock error message would leak the key into logs and tracebacks.
    """

    def __init__(self, reason: str, *, status: int | None = None):
        super().__init__(reason)
        self.reason = reason
        self.status = status

_RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "narrative": {"type": "STRING"},
        "business_impact": {"type": "STRING"},
        "contract": {"type": "STRING"},
        "remediation": {"type": "STRING"},
    },
    "required": ["narrative", "business_impact", "contract", "remediation"],
}

_SYSTEM = (
    "You are a data-governance assistant for a stock broker's data platform. "
    "You are given a FACTUAL, already-computed impact analysis of an upstream schema change on a "
    "daily regulatory MARGIN report. Do not invent or infer additional impacted columns — use only "
    "the facts provided. Be precise and concise.\n"
    "- narrative: 2-3 sentences explaining what will happen, for a data engineer.\n"
    "- business_impact: 1-2 sentences on the regulatory/financial consequence (a margin report "
    "silently misreporting is a compliance breach).\n"
    "- contract: a concrete, enforceable data contract on the CHANGED upstream column that would "
    "catch this next time (name, type, constraints).\n"
    "- remediation: the single most important next step."
)


@dataclass
class DriftExplanation:
    narrative: str
    business_impact: str
    contract: str
    remediation: str


def _facts(report: ImpactReport) -> str:
    c = report.change
    lines = [
        f"Change: column `{c.column}` was {c.change_type.value.upper()}"
        + (f" ({c.detail})" if c.detail else ""),
        f"Severity (computed): {report.severity}",
        f"Impacted downstream report columns ({len(report.affected)}):",
    ]
    for a in report.affected:
        lines.append(f"  - {a.column}  (derived via: {a.transform}; {a.hops} hop(s))")
    return "\n".join(lines)


class DriftNarrator:
    def __init__(self, config: GeminiConfig | None = None) -> None:
        self.config = config or GeminiConfig()

    def narrate(self, report: ImpactReport, *, timeout: float = 60.0) -> DriftExplanation:
        if not self.config.configured:
            raise RuntimeError("GEMINI_API_KEY not set (add it to .env)")
        if not report.breaks:
            return DriftExplanation(
                narrative="No downstream impact detected.",
                business_impact="None.",
                contract="",
                remediation="No action needed.",
            )

        payload = {
            "systemInstruction": {"parts": [{"text": _SYSTEM}]},
            "contents": [{"parts": [{"text": _facts(report)}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseSchema": _RESPONSE_SCHEMA,
                "temperature": 0.2,
            },
        }
        try:
            resp = httpx.post(
                _URL.format(model=self.config.model),
                params={"key": self.config.api_key},
                json=payload,
                timeout=timeout,
            )
        except httpx.RequestError as exc:
            raise NarrationUnavailable(f"could not reach Gemini ({type(exc).__name__})") from None

        if resp.status_code == 429:
            # The free AI Studio tier rate-limits aggressively; this is the common failure.
            raise NarrationUnavailable(
                "Gemini rate limit reached (free tier). Try again in a moment.", status=429
            )
        if resp.status_code != 200:
            # Deliberately not httpx's message: it embeds the URL, which carries ?key=<secret>.
            raise NarrationUnavailable(
                f"Gemini returned HTTP {resp.status_code}", status=resp.status_code
            )

        try:
            text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
            return DriftExplanation(**json.loads(text))
        except (KeyError, IndexError, ValueError, TypeError) as exc:
            # e.g. a safety block or MAX_TOKENS finish returns 200 with no usable candidate.
            raise NarrationUnavailable(
                f"Gemini returned an unusable response ({type(exc).__name__})"
            ) from None
