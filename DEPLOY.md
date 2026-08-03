# Deploy the live demo (free tier)

The judge-facing URL runs the UI + API on free tiers. Impact analysis + Gemini narration work
fully in the cloud (computed in-process); write-back runs in **demo mode** (returns "would write"
without a live DataHub). The `<3min` video shows the *real* local write-back.

**Currently deployed:**

| | |
|---|---|
| UI | https://compliance-drift-sentinel.vercel.app |
| API | https://compliance-drift-sentinel.onrender.com |

## 1. API on Render (~10 min)

Either path works. The live deployment above was created with the **manual Web Service** path.

1. Push is already on `main` at `github.com/Vashu2003/compliance-drift-sentinel`.
2. Render dashboard → **New → Blueprint** → connect the repo → it reads `render.yaml`.
   *Or* **New → Web Service** and enter the settings by hand:

   | Field | Value |
   | ----- | ----- |
   | Branch | `main` |
   | Root Directory | *(blank)* |
   | Language | Python 3 |
   | Build Command | `pip install -r deploy/requirements.txt` |
   | Start Command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
   | Health Check Path | `/api/health` |

3. Set the environment variables. On the Blueprint path Render takes the first two from
   `render.yaml`; **on the manual path you must add them yourself.**

   | Key | Value |
   | --- | ----- |
   | `SENTINEL_LIVE_WRITEBACK` | `false` |
   | `PYTHON_VERSION` | `3.12.7` |
   | `GEMINI_API_KEY` | your AI Studio key |

   Without `SENTINEL_LIVE_WRITEBACK=false` the app defaults to **live** write-back and tries to
   reach a DataHub at `localhost:8080` that does not exist in the cloud.

4. Deploy. Note the URL.
5. Check `<url>/api/health` → `{"ok":true,"gemini":true,"live_writeback":false}`. All three
   fields matter: `gemini:false` means the key did not take, `live_writeback:true` means step 3
   was missed.

## 2. UI on Vercel (~10 min)

1. Vercel → **Add New → Project** → import the same repo.
2. Set **Root Directory** = `frontend` (Vercel auto-detects Vite: build `npm run build`, output `dist`).
3. Add an **Environment Variable**: `VITE_API_BASE` = your Render API URL (from step 1.4, no trailing slash).
4. Deploy. Open the Vercel URL — pick a scenario, the graph lights, Gemini explains, and
   "Write findings back" shows the demo-mode result.

## 3. Wire it into Devpost

- **Try it out** → the Vercel URL.
- **Code repository** → `github.com/Vashu2003/compliance-drift-sentinel`.

## 3. Pre-bake the narrations (do this before judging)

The Gemini **free tier allows only 20 `generateContent` calls per project per day**, shared by
every visitor to the deployed demo — not per user. Render's free tier also spins the container
down after ~15 minutes idle, which empties the in-process narration cache, so a few cold starts
can exhaust the day's budget and leave visitors seeing "Gemini rate limit reached" where the
AI panel should be.

Generate the narrations once and commit them, so the demo stops depending on daily quota:

```bash
./.venv/bin/python scripts/prebake_narrations.py   # ~4 Gemini calls
git add data/narrations.json && git commit -m "chore: pre-bake narrations" && git push
```

The script is resumable — it skips scenarios already present. `do_narrate` resolves in this
order: in-process cache → `data/narrations.json` → live Gemini → a graceful
`{"available": false, "reason": ...}`.

## Notes

- Render free tier spins down after **~15 minutes** idle; the first hit then takes **30–60s** to
  wake. Warm the URL shortly before judging, and say so on the submission page.
- CORS is open (`allow_origins=["*"]`) so the Vercel origin can call the Render API.
- To run write-back live in a demo, run locally with `make dev` + `make ui` against local DataHub.
- `VITE_API_BASE` is baked in at **build** time, not read at runtime — set it before deploying;
  changing it later requires a redeploy.
