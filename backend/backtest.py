"""
Retroactive backtester.

For every BUY/SELL signal in the articles collection:
  - entry_price  = closing price on the article's trading date (yfinance history)
  - price_now    = most recent available close (yfinance history)
  - price_1d     = close 1 trading day after article date
  - price_5d     = close 5 trading days after article date

All prices come from yfinance history so they're real, not the stale
"live" price which is always the same close when the market is shut.
"""
import contextlib
import io
import logging
import time
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Optional

import database

logging.getLogger("yfinance").setLevel(logging.CRITICAL)
logging.getLogger("peewee").setLevel(logging.CRITICAL)

YF_OVERRIDES = {"CENT": "CEY.L"}
CAIRO_TZ = timezone(timedelta(hours=2))


def _yf_sym(ticker: str) -> str:
    return YF_OVERRIDES.get(ticker, f"{ticker}.CA")


def _parse_pct(s: str) -> Optional[float]:
    try:
        return float(s.replace("%", "").replace(" ", "").replace("+", ""))
    except Exception:
        return None


def _outcome(action: str, pct: float) -> str:
    if abs(pct) < 0.5:
        return "EVEN"
    if action == "BUY":
        return "WIN" if pct > 0 else "LOSS"
    return "WIN" if pct < 0 else "LOSS"


def _fetch_history(ticker: str, article_ts: float) -> Optional[dict]:
    """
    Fetch a window of closing prices around the article date.
    Returns a dict with entry, +1d, +5d, and latest close — or None.
    """
    try:
        import yfinance as yf
    except ImportError:
        return None

    sym = _yf_sym(ticker)
    art_date = datetime.fromtimestamp(article_ts, tz=CAIRO_TZ).date()
    start = art_date - timedelta(days=5)
    end   = art_date + timedelta(days=20)

    try:
        with contextlib.redirect_stderr(io.StringIO()):
            hist = yf.Ticker(sym).history(
                start=start.isoformat(),
                end=end.isoformat(),
                raise_errors=False,
            )
    except Exception:
        return None

    if hist is None or hist.empty:
        return None

    dates  = [d.date() for d in hist.index]
    closes = [round(float(c), 2) for c in hist["Close"]]

    # Entry: last trading day on or before article date
    entry_idx = None
    for i, d in enumerate(dates):
        if d <= art_date:
            entry_idx = i

    if entry_idx is None or not closes[entry_idx]:
        return None

    def _at(offset) -> Optional[float]:
        idx = entry_idx + offset
        if 0 <= idx < len(closes):
            return closes[idx] or None
        return None

    return {
        "entry_price":  closes[entry_idx],
        "trading_date": dates[entry_idx].isoformat(),
        "price_1d":     _at(1),
        "price_5d":     _at(5),
        "price_latest": closes[-1],   # most recent close in the window
        "latest_date":  dates[-1].isoformat(),
    }


def run_backtest(force_refresh: bool = False) -> dict:
    art_col = database.articles()
    bt_col  = database.db()["backtest_signals"]
    bt_col.create_index("signal_key", unique=True, background=True)

    articles = list(art_col.find({}, {
        "_id": 0, "id": 1, "timestamp": 1, "date": 1, "analysis": 1
    }))

    processed = new_added = skipped = 0

    for art in articles:
        analysis = art.get("analysis", {})
        stocks = [s for s in analysis.get("affected_stocks", [])
                  if s.get("action") in ("BUY", "SELL")]
        if not stocks:
            continue

        art_ts = art.get("timestamp") or 0

        for stock in stocks:
            ticker = stock.get("ticker", "")
            action = stock.get("action", "")
            key    = f"bt_{art.get('id', '')}_{ticker}_{action}"

            if not force_refresh and bt_col.find_one({"signal_key": key}):
                skipped += 1
                continue

            processed += 1
            hist = _fetch_history(ticker, art_ts) if art_ts else None

            article_date = ""
            if art_ts:
                try:
                    article_date = datetime.fromtimestamp(art_ts, tz=CAIRO_TZ).strftime("%Y-%m-%d")
                except Exception:
                    pass

            predicted_pct = _parse_pct(stock.get("expected_change", ""))

            def _chg(ep, p):
                if ep and p:
                    return round((p - ep) / ep * 100, 2)
                return None

            if hist:
                ep  = hist["entry_price"]
                c1d = _chg(ep, hist.get("price_1d"))
                c5d = _chg(ep, hist.get("price_5d"))
                c_now = _chg(ep, hist.get("price_latest"))

                doc = {
                    "_id":           str(uuid.uuid4()),
                    "signal_key":   key,
                    "ticker":       ticker,
                    "name":         stock.get("name", ""),
                    "sector":       stock.get("sector", ""),
                    "action":       action,
                    "confidence":   stock.get("confidence", "MEDIUM"),
                    "expected_change": stock.get("expected_change", ""),
                    "predicted_pct":   predicted_pct,
                    "reason":       stock.get("reason", ""),
                    "article_id":   art.get("id", ""),
                    "article_date": article_date,
                    "timestamp":    art_ts,
                    "available":    True,
                    "entry_price":  ep,
                    "trading_date": hist["trading_date"],
                    "price_1d":     hist.get("price_1d"),
                    "change_1d":    c1d,
                    "outcome_1d":   _outcome(action, c1d) if c1d is not None else "NO_DATA",
                    "price_5d":     hist.get("price_5d"),
                    "change_5d":    c5d,
                    "outcome_5d":   _outcome(action, c5d) if c5d is not None else "NO_DATA",
                    "price_now":    hist.get("price_latest"),
                    "change_now":   c_now,
                    "outcome_now":  _outcome(action, c_now) if c_now is not None else "NO_DATA",
                    "latest_date":  hist.get("latest_date", ""),
                }
            else:
                doc = {
                    "_id":          str(uuid.uuid4()),
                    "signal_key":  key,
                    "ticker":      ticker,
                    "name":        stock.get("name", ""),
                    "sector":      stock.get("sector", ""),
                    "action":      action,
                    "confidence":  stock.get("confidence", "MEDIUM"),
                    "expected_change": stock.get("expected_change", ""),
                    "predicted_pct":   predicted_pct,
                    "reason":      stock.get("reason", ""),
                    "article_id":  art.get("id", ""),
                    "article_date": article_date,
                    "timestamp":   art_ts,
                    "available":   False,
                    "entry_price": None,
                    "price_1d": None, "change_1d": None, "outcome_1d": "NO_DATA",
                    "price_5d": None, "change_5d": None, "outcome_5d": "NO_DATA",
                    "price_now": None, "change_now": None, "outcome_now": "NO_DATA",
                }

            try:
                bt_col.replace_one({"signal_key": key}, doc, upsert=True)
                new_added += 1
            except Exception:
                pass

            time.sleep(0.15)

    return {
        "processed":   processed,
        "skipped":     skipped,
        "new_added":   new_added,
        "total_in_db": bt_col.count_documents({}),
    }


def get_backtest_stats() -> dict:
    bt_col = database.db()["backtest_signals"]

    total     = bt_col.count_documents({})
    available = bt_col.count_documents({"available": True})

    if available == 0:
        return {"total": total, "available": 0, "ready": False}

    def _rate(w, t):
        return round(w / t * 100, 1) if t > 0 else None

    stats: dict = {"total": total, "available": available, "ready": True}

    # Use "now" as primary (entry date close → latest close)
    for h in ["now", "1d", "5d"]:
        w = bt_col.count_documents({f"outcome_{h}": "WIN"})
        l = bt_col.count_documents({f"outcome_{h}": "LOSS"})
        e = bt_col.count_documents({f"outcome_{h}": "EVEN"})
        stats[f"wins_{h}"]          = w
        stats[f"losses_{h}"]        = l
        stats[f"evens_{h}"]         = e
        stats[f"total_resolved_{h}"] = w + l + e
        stats[f"accuracy_{h}"]      = _rate(w, w + l)

    # Per action
    for action in ["BUY", "SELL"]:
        w = bt_col.count_documents({"action": action, "outcome_now": "WIN"})
        t = bt_col.count_documents({"action": action, "outcome_now": {"$in": ["WIN", "LOSS"]}})
        stats[f"accuracy_action_{action}"] = _rate(w, t)

    # Per confidence
    for conf in ["HIGH", "MEDIUM", "LOW"]:
        w = bt_col.count_documents({"confidence": conf, "outcome_now": "WIN"})
        t = bt_col.count_documents({"confidence": conf, "outcome_now": {"$in": ["WIN", "LOSS"]}})
        stats[f"accuracy_conf_{conf}"] = _rate(w, t)

    # Sector (min 2 with outcome)
    sector_stats = defaultdict(lambda: {"wins": 0, "total": 0})
    for sig in bt_col.find({"outcome_now": {"$in": ["WIN", "LOSS"]}}):
        s = sig.get("sector", "Unknown")
        sector_stats[s]["total"] += 1
        if sig["outcome_now"] == "WIN":
            sector_stats[s]["wins"] += 1

    sector_chart = sorted(
        [{"sector": s, "accuracy": _rate(d["wins"], d["total"]), "signals": d["total"]}
         for s, d in sector_stats.items() if d["total"] >= 2],
        key=lambda x: x["accuracy"] or 0, reverse=True
    )
    stats["sector_chart"] = sector_chart

    # Daily accuracy
    daily = defaultdict(lambda: {"wins": 0, "total": 0})
    for sig in bt_col.find({"outcome_now": {"$in": ["WIN", "LOSS"]}}):
        day = sig.get("article_date", "")
        if day:
            daily[day]["total"] += 1
            if sig["outcome_now"] == "WIN":
                daily[day]["wins"] += 1
    stats["accuracy_over_time"] = [
        {"date": day, "accuracy": _rate(d["wins"], d["total"]), "signals": d["total"]}
        for day, d in sorted(daily.items()) if d["total"] >= 1
    ]

    # Charts
    conf_chart = []
    for conf in ["HIGH", "MEDIUM", "LOW"]:
        w = bt_col.count_documents({"confidence": conf, "outcome_now": "WIN"})
        l = bt_col.count_documents({"confidence": conf, "outcome_now": "LOSS"})
        e = bt_col.count_documents({"confidence": conf, "outcome_now": "EVEN"})
        t = w + l + e
        if t > 0:
            conf_chart.append({"confidence": conf, "wins": w, "losses": l, "evens": e,
                                "total": t, "accuracy": _rate(w, w + l)})
    stats["confidence_chart"] = conf_chart

    action_chart = []
    for action in ["BUY", "SELL"]:
        w = bt_col.count_documents({"action": action, "outcome_now": "WIN"})
        l = bt_col.count_documents({"action": action, "outcome_now": "LOSS"})
        e = bt_col.count_documents({"action": action, "outcome_now": "EVEN"})
        t = w + l + e
        if t > 0:
            action_chart.append({"action": action, "wins": w, "losses": l, "evens": e,
                                  "total": t, "accuracy": _rate(w, w + l)})
    stats["action_chart"] = action_chart

    horizon_chart = [
        {"horizon": lbl, "wins": stats[f"wins_{h}"], "losses": stats[f"losses_{h}"],
         "evens": stats[f"evens_{h}"], "accuracy": stats[f"accuracy_{h}"]}
        for h, lbl in [("now", "Since signal"), ("1d", "Next day"), ("5d", "5 days")]
    ]
    stats["horizon_chart"] = horizon_chart

    scatter = []
    for sig in bt_col.find({"predicted_pct": {"$ne": None}, "change_now": {"$ne": None}}):
        if sig.get("outcome_now") in ("WIN", "LOSS", "EVEN"):
            scatter.append({
                "predicted": sig["predicted_pct"],
                "actual":    sig["change_now"],
                "ticker":    sig.get("ticker"),
                "action":    sig.get("action"),
                "outcome":   sig.get("outcome_now"),
            })
    stats["scatter"] = scatter

    if sector_chart:
        stats["best_sector"]  = {"name": sector_chart[0]["sector"],  "accuracy": sector_chart[0]["accuracy"]}
        stats["worst_sector"] = {"name": sector_chart[-1]["sector"], "accuracy": sector_chart[-1]["accuracy"]}
    else:
        stats["best_sector"] = stats["worst_sector"] = None

    return stats
