# Decisions

Locked build decisions for Compliance Drift Sentinel.

| # | Decision | Choice | Rationale |
|---|----------|--------|-----------|
| D1 | Demo scenario | Daily **margin report** (broker: ledger + positions + collateral → margin report) | Author's domain; "wrong margin = regulatory breach" is a compelling break story. |
| D2 | Agent LLM | **Google Gemini** (free tier, AI Studio key) | Free; author already uses it on other projects. |
| D3 | Scope | Slices 0–5 + package as a DataHub Skill (OSS bonus) | Matches ~10h/wk budget. |
| D4 | Work model | Focused build sessions + daily digest; light per-slice walkthrough | Author is interview-prepping — must be able to explain the code. |
| D5 | Live demo | Free-tier app (Render API + Vercel UI) reading a **baked lineage snapshot** + pre-computed drift | DataHub's 7-container ~8GB stack won't fit a free tier. Video shows the REAL local DataHub doing live write-back. Zero cost, robust. |

## Human gates (author reviews before I proceed)
- **Graph write-back** (Slice 3): review exactly what aspects we write before enabling mutations.
- **UI direction** (Slice 5): author picks from 2–3 proposed design directions (anti-slop).

## Inputs due from author
- Slice 4: free Gemini API key → `.env` as `GEMINI_API_KEY`.
- Week 3: connect Render/Vercel for deploy.
