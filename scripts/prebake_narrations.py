"""Generate `data/narrations.json` — one real Gemini narration per built-in scenario.

Why this exists: the Gemini free tier allows only 20 generateContent calls per project per
DAY, shared by every visitor to the deployed demo. Render's free tier also spins the container
down after ~15 minutes idle, which empties the in-process cache, so a handful of cold starts
can burn the whole day's budget and leave judges looking at a rate-limit message instead of
the headline feature.

Pre-baking makes the deployed demo independent of daily quota. The text is still genuinely
Gemini's — it is just generated once, here, rather than per visitor.

Run when quota is available (resets daily):

    ./.venv/bin/python scripts/prebake_narrations.py

Then commit data/narrations.json and redeploy. Re-run only if the scenarios or the prompt change.
"""
from __future__ import annotations

import json
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from engine.agent import DriftNarrator, NarrationUnavailable  # noqa: E402
from engine.config import GeminiConfig  # noqa: E402
from engine.impact import analyze  # noqa: E402
from engine.margin_pipeline import SCENARIOS, build_column_graph, dataset_urn  # noqa: E402
from engine.models import ChangeType, ColumnRef, SchemaChange  # noqa: E402

OUT = pathlib.Path(__file__).resolve().parent.parent / "data" / "narrations.json"
GAP_SECONDS = 5.0   # be gentle with the per-minute burst limit


def main() -> int:
    if not GeminiConfig().configured:
        print("GEMINI_API_KEY not set — nothing to do.", file=sys.stderr)
        return 1

    graph = build_column_graph()
    narrator = DriftNarrator()
    baked: dict[str, dict] = {}
    if OUT.exists():
        baked = json.loads(OUT.read_text())
        print(f"existing file has {len(baked)} entries; missing ones will be filled")

    failures = 0
    for i, scn in enumerate(SCENARIOS):
        key = f"{scn['dataset']}|{scn['column']}|{scn['change_type']}"
        if key in baked:
            print(f"  skip  {scn['id']:18s} (already baked)")
            continue

        report = analyze(
            SchemaChange(
                column=ColumnRef(dataset_urn(scn["dataset"]), scn["column"]),
                change_type=ChangeType(scn["change_type"]),
                detail=scn["detail"],
            ),
            graph,
        )
        try:
            exp = narrator.narrate(report)
        except NarrationUnavailable as exc:
            print(f"  FAIL  {scn['id']:18s} {exc.reason}")
            failures += 1
            continue

        baked[key] = {
            "available": True,
            "narrative": exp.narrative,
            "business_impact": exp.business_impact,
            "contract": exp.contract,
            "remediation": exp.remediation,
        }
        print(f"  ok    {scn['id']:18s} {len(exp.narrative)} chars")
        if i < len(SCENARIOS) - 1:
            time.sleep(GAP_SECONDS)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(baked, indent=2) + "\n")
    print(f"\nwrote {OUT} with {len(baked)}/{len(SCENARIOS)} scenarios")
    if failures:
        print(f"{failures} scenario(s) still missing — re-run when quota allows.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
