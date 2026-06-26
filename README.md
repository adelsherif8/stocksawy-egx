# Stocksawy — EGX Market Intelligence

> **An AI analyst for the Egyptian Exchange (EGX).** Pulls live prices and news, uses an LLM to summarize sentiment and answer questions about tickers, and pushes Telegram alerts — all behind a React dashboard with interactive charts.

![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-LLM-412991?logo=openai&logoColor=white)
![React](https://img.shields.io/badge/React-dashboard-61DAFB?logo=react&logoColor=black)
![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)

**▶️ Live demo:** _deploying — see [Getting Started](#getting-started) for now_

---

## Features

- 📈 **Live market data** — EGX prices and history via `yfinance`
- 📰 **News ingestion** — pulls and parses market news per ticker
- 🧠 **LLM analysis** — summarizes sentiment and answers natural-language questions about tickers
- 🔔 **Telegram alerts** — optional push notifications on signals
- 🧪 **Backtesting** — strategy backtest module included
- 📊 **Interactive dashboard** — charts and chat UI (React + Recharts)

## Tech Stack

- **Backend:** Python, FastAPI, OpenAI, `yfinance` (market data), `feedparser` (news), MongoDB (`pymongo`), `httpx`
- **Frontend:** React, Recharts (charts), `lucide-react`

## Project Layout

```
backend/
  ├─ main.py          FastAPI app
  ├─ analyzer.py      LLM analysis
  ├─ news_fetcher.py  market news
  ├─ prices.py        live prices (yfinance)
  ├─ backtest.py      strategy backtesting
  └─ notifier.py      Telegram alerts
frontend/             React dashboard — charts & chat UI
```

## Getting Started

**Backend:**
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env       # add OPENAI_API_KEY (Telegram + MongoDB optional)
uvicorn main:app --reload  # http://localhost:8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

## Configuration

Secrets load from `backend/.env` (git-ignored). `OPENAI_API_KEY` is required; Telegram bot token/chat ID and a MongoDB connection string are optional (see `.env.example`).
