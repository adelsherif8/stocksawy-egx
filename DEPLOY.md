# Deploying Stocksawy (free tier)

**Backend → Render**, **frontend (Vite/React) → Vercel.**

> ⚠️ This app has **no mock mode** — it needs a funded `OPENAI_API_KEY` to return
> analysis. Set one before relying on the demo.

## Backend → Render
1. <https://dashboard.render.com> → **New + → Blueprint** → select this repo → **Apply** (reads [`render.yaml`](./render.yaml), root dir `backend`).
2. Set env vars when prompted: `OPENAI_API_KEY` (required); Telegram/MongoDB optional.
3. Note the URL, e.g. `https://stocksawy-api.onrender.com`.

> Free tier sleeps after ~15 min idle (≈50s cold start).

## Frontend → Vercel
1. <https://vercel.com/new> → import this repo → **Root Directory** = `frontend`.
2. Framework preset: **Vite**. Build: `npm run build`, output dir: `dist`.
3. Add env var pointing the UI at your Render API (check `frontend/src` for the exact var name, typically `VITE_API_URL`).
4. Deploy → note the URL.

## Connect
- In Render, set `ALLOWED_ORIGINS` to your Vercel URL so the API accepts browser requests, then update the live-demo link in [`README.md`](./README.md).

### Note on CORS
If browser calls are blocked, confirm the backend reads `ALLOWED_ORIGINS` and adds a `CORSMiddleware` allowing your frontend origin.
