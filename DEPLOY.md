# Deploy the live demo (free tier)

The judge-facing URL runs the UI + API on free tiers. Impact analysis + Gemini narration work
fully in the cloud (computed in-process); write-back runs in **demo mode** (returns "would write"
without a live DataHub). The `<3min` video shows the *real* local write-back.

## 1. API on Render (~10 min)

1. Push is already on `main` at `github.com/Vashu2003/compliance-drift-sentinel`.
2. Render dashboard → **New → Blueprint** → connect the repo → it reads `render.yaml`.
3. In the service **Environment** tab set `GEMINI_API_KEY` = your AI Studio key (marked `sync:false`,
   so it is never in the repo).
4. Deploy. Note the URL, e.g. `https://drift-sentinel-api.onrender.com`.
5. Check `https://drift-sentinel-api.onrender.com/api/health` → `{"ok":true,...}`.

## 2. UI on Vercel (~10 min)

1. Vercel → **Add New → Project** → import the same repo.
2. Set **Root Directory** = `frontend` (Vercel auto-detects Vite: build `npm run build`, output `dist`).
3. Add an **Environment Variable**: `VITE_API_BASE` = your Render API URL (from step 1.4, no trailing slash).
4. Deploy. Open the Vercel URL — pick a scenario, the graph lights, Gemini explains, and
   "Write findings back" shows the demo-mode result.

## 3. Wire it into Devpost

- **Try it out** → the Vercel URL.
- **Code repository** → `github.com/Vashu2003/compliance-drift-sentinel`.

## Notes

- Render free tier sleeps after inactivity; first hit after idle takes ~30s to wake. Fine for judging.
- CORS is open (`allow_origins=["*"]`) so the Vercel origin can call the Render API.
- To run write-back live in a demo, run locally with `make dev` + `make ui` against local DataHub.
