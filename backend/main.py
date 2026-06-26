import warnings
warnings.filterwarnings("ignore", message=".*NotOpenSSLWarning.*")
warnings.filterwarnings("ignore", category=Warning, module="urllib3")

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
import time
import threading

load_dotenv()

from apscheduler.schedulers.background import BackgroundScheduler
from news_fetcher import fetch_all_news
from analyzer import analyze_new_articles, get_top_recommendations
from prices import get_egx_prices, enrich_with_prices
from history import add_signals, check_checkpoints, get_history, get_stats
from egx_stocks import EGX_STOCKS
from notifier import send_new_signals, send_test_message
import database
import learning
import backtest as bt_module

app = FastAPI(title="EGX Stock Intelligence Bot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── In-memory cache (served instantly to frontend) ───────────────────────────
_cache = {"analyzed": [], "recommendations": [], "prices": {}, "fetched_at": 0}
_refresh_lock = threading.Lock()
_refresh_in_progress = False


def _load_cache_from_db():
    """On startup, load recent 48h articles from MongoDB into memory."""
    try:
        cutoff = time.time() - 48 * 3600
        docs = list(database.articles().find(
            {"timestamp": {"$gte": cutoff}},
            {"_id": 0}
        ).sort("timestamp", -1))
        if docs:
            _cache["analyzed"] = docs
            _cache["recommendations"] = get_top_recommendations(docs)
            _cache["fetched_at"] = max(d.get("analyzed_at", 0) for d in docs)
            print(f"[startup] Loaded {len(docs)} articles from MongoDB")
        else:
            print("[startup] No recent articles in MongoDB — will fetch on first run")
    except Exception as e:
        print(f"[startup] MongoDB load failed: {e}")


def _run_check():
    """
    Core job: fetch RSS, find new articles, analyze only new ones,
    update cache, send Telegram if new actionable signals found.
    """
    global _refresh_in_progress

    if not _refresh_lock.acquire(blocking=False):
        return  # Already running

    try:
        _refresh_in_progress = True
        print("[scheduler] Checking for new news...")

        # 1. Fetch RSS
        news = fetch_all_news(max_per_feed=15)
        if not news:
            print("[scheduler] No news fetched")
            return

        # 2. Find which articles are genuinely new (not in MongoDB)
        col = database.articles()
        existing_ids = set(
            doc["_id"] for doc in col.find(
                {"_id": {"$in": [n["id"] for n in news]}}, {"_id": 1}
            )
        )
        new_count = sum(1 for n in news if n["id"] not in existing_ids)
        print(f"[scheduler] {len(news)} articles found — {new_count} new, {len(news)-new_count} already analyzed")

        if new_count == 0 and _cache["analyzed"]:
            # Nothing new — just update prices and check checkpoints
            _update_prices_only()
            return

        # 3. Analyze (only new ones hit OpenAI; cached ones load from MongoDB)
        existing_set = existing_ids  # already computed above
        analyzed = analyze_new_articles(news)

        # Identify which articles were genuinely new (for Telegram)
        new_articles = [a for a in analyzed if a.get("id") not in existing_set]

        # 4. Rebuild recommendations
        recommendations = get_top_recommendations(analyzed)
        tickers = list({r["ticker"] for r in recommendations})
        prices = get_egx_prices(tickers) if tickers else {}
        analyzed = enrich_with_prices(analyzed, prices)
        for rec in recommendations:
            rec["price_data"] = prices.get(rec["ticker"], {"available": False})

        # 5. Save signals & check 1h/6h/24h checkpoints (silent — no Telegram spam)
        add_signals(recommendations, prices)
        check_checkpoints(prices)

        # 6. Update in-memory cache
        _cache["analyzed"] = analyzed
        _cache["recommendations"] = recommendations
        _cache["prices"] = prices
        _cache["fetched_at"] = time.time()

        # 7. Telegram — only once per new article with actionable signals
        if new_articles:
            sent = send_new_signals(new_articles)
            if sent:
                print(f"[scheduler] Sent {sent} Telegram alert(s) for new articles")

        print(f"[scheduler] Done — {len(analyzed)} articles, {len(recommendations)} signals")

    except Exception as e:
        import traceback
        print(f"[scheduler] ERROR: {e}")
        traceback.print_exc()
    finally:
        _refresh_in_progress = False
        _refresh_lock.release()


def _update_prices_only():
    """Refresh prices and check signal checkpoints without re-fetching news."""
    # Get all tickers from pending signals too
    pending = list(database.signals().find({"outcome": "PENDING"}, {"ticker": 1}))
    tickers = list({r["ticker"] for r in _cache.get("recommendations", [])} |
                   {s["ticker"] for s in pending})
    if not tickers:
        return
    prices = get_egx_prices(tickers)
    for rec in _cache.get("recommendations", []):
        rec["price_data"] = prices.get(rec["ticker"], {"available": False})
    resolved = check_checkpoints(prices)
    if resolved:
        print(f"[scheduler] {len(resolved)} checkpoint(s) resolved")
    _cache["prices"] = prices


# ── Startup ───────────────────────────────────────────────────────────────────
@app.on_event("startup")
def startup():
    _load_cache_from_db()

    # Retroactively resolve old signals that are EVEN/PENDING due to market-closed prices
    threading.Thread(target=_retroactive_resolve, daemon=True).start()

    import datetime as _dt
    scheduler = BackgroundScheduler(timezone="Africa/Cairo")
    scheduler.add_job(_run_check, "interval", minutes=2, id="news_check",
                      next_run_time=_dt.datetime.now() + _dt.timedelta(seconds=30))
    scheduler.start()
    print("[startup] Scheduler started — checking news every 2 minutes")


def _retroactive_resolve():
    """
    On startup, re-evaluate any 24h signals that resolved as EVEN or are old PENDING
    using historical yfinance prices so the learning system has real data.
    """
    import contextlib, io
    try:
        import yfinance as yf
    except ImportError:
        return

    from history import _fetch_close_on_or_after, _outcome, _parse_expected_pct
    from datetime import datetime, timedelta, timezone

    CAIRO_TZ = timezone(timedelta(hours=2))
    col = database.signals()
    now = time.time()
    fixed = 0

    candidates = list(col.find({
        "$or": [
            {"outcome_24h": {"$in": ["EVEN", "PENDING", None]},
             "timestamp": {"$lt": now - 86400}},   # over 24h old
        ]
    }))

    for sig in candidates:
        ticker = sig.get("ticker", "")
        entry  = sig.get("price_at_signal")
        if not entry or not ticker:
            continue

        sig_date = datetime.fromtimestamp(sig.get("timestamp", now), tz=CAIRO_TZ).date()
        next_day = sig_date + timedelta(days=1)

        price = _fetch_close_on_or_after(ticker, next_day)
        if not price:
            continue

        pct     = (price - entry) / entry * 100
        outcome = _outcome(sig.get("action", ""), pct)

        col.update_one({"_id": sig["_id"]}, {"$set": {
            "price_24h":    price,
            "change_24h":   round(pct, 2),
            "outcome_24h":  outcome,
            "outcome":      outcome,
            "evaluated_24h": True,
        }})
        fixed += 1
        time.sleep(0.1)

    if fixed:
        print(f"[startup] Retroactively resolved {fixed} signals with historical prices")


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"status": "Stocksawy running", "version": "3.0"}


@app.get("/api/news")
def get_news():
    return {"news": _cache["analyzed"], "fetched_at": _cache["fetched_at"], "total": len(_cache["analyzed"])}


@app.get("/api/recommendations")
def get_recommendations():
    return {"recommendations": _cache["recommendations"], "fetched_at": _cache["fetched_at"]}


@app.post("/api/refresh")
def force_refresh():
    """Trigger an immediate check (runs in background, returns current cache)."""
    threading.Thread(target=_run_check, daemon=True).start()
    return {"status": "check triggered", "news_count": len(_cache["analyzed"]),
            "recommendations_count": len(_cache["recommendations"])}


@app.get("/api/history")
def get_signal_history():
    signals = get_history()
    stats = get_stats()
    return {"signals": signals, "stats": stats}


@app.get("/api/learning")
def get_learning_stats():
    """Return AI accuracy stats and calibration data."""
    import math

    def _clean(obj):
        if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
            return None
        if isinstance(obj, dict):
            return {k: _clean(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_clean(v) for v in obj]
        return obj

    return _clean(learning.get_full_stats())


@app.get("/api/heatmap")
def get_heatmap():
    sector_data = {s: {"bullish": 0, "bearish": 0, "neutral": 0, "stocks": set(), "urgency": 0}
                   for s in EGX_STOCKS}
    for item in _cache["analyzed"]:
        analysis = item.get("analysis", {})
        sentiment = analysis.get("sentiment", "NEUTRAL")
        urgency_val = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}.get(analysis.get("urgency", "LOW"), 1)
        for stock in analysis.get("affected_stocks", []):
            sector = stock.get("sector", "")
            if sector not in sector_data:
                continue
            sector_data[sector]["stocks"].add(stock["ticker"])
            sector_data[sector]["urgency"] = max(sector_data[sector]["urgency"], urgency_val)
            if sentiment == "BULLISH":
                sector_data[sector]["bullish"] += 1
            elif sentiment == "BEARISH":
                sector_data[sector]["bearish"] += 1
            else:
                sector_data[sector]["neutral"] += 1

    result = []
    for sector, d in sector_data.items():
        total = d["bullish"] + d["bearish"] + d["neutral"]
        score = (d["bullish"] - d["bearish"]) / total if total else 0
        sentiment = "BULLISH" if score > 0.2 else ("BEARISH" if score < -0.2 else "NEUTRAL")
        result.append({"sector": sector, "sentiment": sentiment, "score": round(score, 2),
                        "bullish": d["bullish"], "bearish": d["bearish"], "neutral": d["neutral"],
                        "stocks_affected": len(d["stocks"]), "urgency": d["urgency"], "total_signals": total})
    return {"heatmap": result}


@app.get("/api/status")
def status():
    age = int(time.time() - _cache["fetched_at"]) if _cache["fetched_at"] else None
    db_count = database.articles().count_documents({})
    return {
        "has_data": bool(_cache["analyzed"]),
        "news_count": len(_cache["analyzed"]),
        "recommendations_count": len(_cache["recommendations"]),
        "cache_age_seconds": age,
        "refresh_in_progress": _refresh_in_progress,
        "db_articles_total": db_count,
        "openai_key_set": bool(os.getenv("OPENAI_API_KEY")),
        "telegram_configured": bool(os.getenv("TELEGRAM_BOT_TOKEN") and os.getenv("TELEGRAM_CHAT_ID")),
    }


@app.get("/api/analytics/distribution")
def get_distribution():
    """Signal distribution stats straight from analyzed articles — no price data needed."""
    from collections import Counter, defaultdict

    col = database.articles()
    sig_col = database.signals()

    action_counts  = Counter()
    conf_counts    = Counter()
    sector_counts  = Counter()
    expected_vals  = []

    for art in col.find({}, {"analysis": 1}):
        for stock in art.get("analysis", {}).get("affected_stocks", []):
            action = stock.get("action", "")
            if action in ("BUY", "SELL", "WATCH"):
                action_counts[action] += 1
            conf = stock.get("confidence", "")
            if conf in ("HIGH", "MEDIUM", "LOW"):
                conf_counts[conf] += 1
            sec = stock.get("sector", "")
            if sec:
                sector_counts[sec] += 1
            try:
                pct = float(stock.get("expected_change", "").replace("%", "").replace("+", ""))
                expected_vals.append(pct)
            except Exception:
                pass

    # Sector chart sorted by count
    sector_chart = [{"sector": s, "count": c}
                    for s, c in sector_counts.most_common(12)]

    # Expected change histogram buckets
    buckets = {"< -5%": 0, "-5 to -2%": 0, "-2 to 0%": 0, "0 to 2%": 0, "2 to 5%": 0, "> 5%": 0}
    for v in expected_vals:
        if v < -5:   buckets["< -5%"] += 1
        elif v < -2: buckets["-5 to -2%"] += 1
        elif v < 0:  buckets["-2 to 0%"] += 1
        elif v < 2:  buckets["0 to 2%"] += 1
        elif v < 5:  buckets["2 to 5%"] += 1
        else:        buckets["> 5%"] += 1
    expected_hist = [{"bucket": k, "count": v} for k, v in buckets.items()]

    # Live signal checkpoint progress
    total_sigs  = sig_col.count_documents({})
    pending_1h  = sig_col.count_documents({"outcome_1h": "PENDING"})
    resolved_1h = sig_col.count_documents({"outcome_1h": {"$in": ["WIN", "LOSS", "EVEN"]}})
    resolved_24h = sig_col.count_documents({"outcome_24h": {"$in": ["WIN", "LOSS", "EVEN"]}})

    return {
        "total_articles": col.count_documents({}),
        "total_stock_signals": sum(action_counts.values()),
        "action_distribution": [{"action": k, "count": v} for k, v in action_counts.items()],
        "confidence_distribution": [{"confidence": k, "count": v} for k, v in conf_counts.items()],
        "sector_distribution": sector_chart,
        "expected_histogram": expected_hist,
        "live_tracking": {
            "total": total_sigs,
            "pending_1h": pending_1h,
            "resolved_1h": resolved_1h,
            "resolved_24h": resolved_24h,
        }
    }


@app.get("/api/backtest/stats")
def get_backtest_stats():
    """Return retroactive backtest accuracy stats for Analytics."""
    return bt_module.get_backtest_stats()


@app.post("/api/backtest/run")
def run_backtest(force: bool = False):
    """
    Retroactively test all AI signals in MongoDB against real historical prices.
    Safe to call multiple times — skips already-evaluated signals.
    Runs in background; returns immediately.
    """
    def _run():
        print("[backtest] Starting retroactive evaluation...")
        result = bt_module.run_backtest(force_refresh=force)
        print(f"[backtest] Done — {result}")
    threading.Thread(target=_run, daemon=True).start()
    return {"status": "running", "message": "Backtest started in background"}


@app.post("/api/notify/test")
def test_notification():
    if not (os.getenv("TELEGRAM_BOT_TOKEN") and os.getenv("TELEGRAM_CHAT_ID")):
        raise HTTPException(status_code=400, detail="Telegram not configured in .env")
    ok = send_test_message()
    if not ok:
        raise HTTPException(status_code=500, detail="Failed — check token and chat ID")
    return {"status": "sent"}


@app.post("/api/notify/now")
def notify_now():
    if not _cache["analyzed"]:
        raise HTTPException(status_code=400, detail="No articles in cache yet")
    sent = send_new_signals(_cache["analyzed"])
    return {"status": "sent", "messages_sent": sent}
