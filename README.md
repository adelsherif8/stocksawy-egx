# Stocksawy — EGX Intelligence

An AI stock-market assistant focused on the **Egyptian Exchange (EGX)**. It pulls
live market data and news, then uses an LLM to summarise and answer questions
about tickers, with interactive charts in the UI.

## Tech Stack

- **Backend:** Python, FastAPI, OpenAI, `yfinance` (market data), `feedparser`
  (news), MongoDB (`pymongo`), `httpx`
- **Frontend:** React, Recharts (charts), `lucide-react`

## Project Layout

```
backend/    FastAPI service — data ingestion, LLM analysis, API
frontend/   React dashboard — charts & chat UI
```

## Getting Started

**Backend:**
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # add OPENAI_API_KEY, MongoDB URI, etc.
uvicorn main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

## Configuration

Secrets load from `backend/.env` (git-ignored). Required keys typically include
`OPENAI_API_KEY` and a MongoDB connection string.
