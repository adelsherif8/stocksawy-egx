import contextlib
import io
import logging
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

import database

logging.getLogger("yfinance").setLevel(logging.CRITICAL)
logging.getLogger("peewee").setLevel(logging.CRITICAL)

CHECKPOINTS = [
    ("1h",  3600),
    ("6h",  21600),
    ("24h", 86400),
]

CAIRO_TZ   = timezone(timedelta(hours=2))
YF_OVERRIDES = {"CENT": "CEY.L"}


def _yf_sym(ticker: str) -> str:
    return YF_OVERRIDES.get(ticker, f"{ticker}.CA")


def _parse_expected_pct(s: str) -> Optional[float]:
    try:
        return float(s.replace("%", "").replace(" ", "").replace("+", ""))
    except Exception:
        return None


def _outcome(action: str, actual_pct: float) -> str:
    if abs(actual_pct) < 0.5:
        return "EVEN"
    if action == "BUY":
        return "WIN" if actual_pct > 0 else "LOSS"
    if action == "SELL":
        return "WIN" if actual_pct < 0 else "LOSS"
    return "EVEN"


def _fetch_close_on_or_after(ticker: str, target_date) -> Optional[float]:
    """
    Return the closing price on `target_date` or the next available trading day.
    `target_date` is a datetime.date object.
    """
    try:
        import yfinance as yf
    except ImportError:
        return None

    sym   = _yf_sym(ticker)
    start = target_date
    end   = target_date + timedelta(days=10)

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

    return round(float(hist["Close"].iloc[0]), 2)


def add_signals(recommendations: List[dict], prices: Dict[str, dict]) -> int:
    col  = database.signals()
    now  = time.time()
    today = datetime.fromtimestamp(now, tz=CAIRO_TZ).date()
    added = 0

    for rec in recommendations:
        signal_key = f"{rec['ticker']}_{rec['action']}_{today.isoformat()}"
        if col.find_one({"signal_key": signal_key}):
            continue

        price_data  = prices.get(rec["ticker"], {})
        entry_price = price_data.get("price") if price_data.get("available") else None
        predicted_pct = _parse_expected_pct(rec.get("expected_change", ""))

        doc = {
            "_id":           str(uuid.uuid4()),
            "signal_key":   signal_key,
            "ticker":       rec["ticker"],
            "name":         rec.get("name", ""),
            "sector":       rec.get("sector", ""),
            "action":       rec["action"],
            "confidence":   rec.get("confidence", "MEDIUM"),
            "reason":       rec.get("reason", ""),
            "expected_change": rec.get("expected_change", ""),
            "predicted_pct":   predicted_pct,
            "news_titles":  rec.get("news_titles", [])[:2],
            "timestamp":    now,
            "date":         today.isoformat(),
            # Entry
            "price_at_signal": entry_price,
            # Checkpoints
            "price_1h": None, "price_6h": None, "price_24h": None,
            "change_1h": None, "change_6h": None, "change_24h": None,
            "outcome_1h": "PENDING", "outcome_6h": "PENDING", "outcome_24h": "PENDING",
            "outcome":    "PENDING",
            # Track which checkpoints have been evaluated (not just notified)
            "evaluated_1h": False, "evaluated_6h": False, "evaluated_24h": False,
        }
        col.insert_one(doc)
        added += 1

    return added


def check_checkpoints(prices: Dict[str, dict]) -> List[tuple]:
    """
    Evaluate each pending signal at its 1h/6h/24h checkpoint.

    - For 1h/6h: uses the live price from the `prices` dict (current session).
    - For 24h:   uses the historical close from yfinance for the NEXT trading day
                 after the signal date — so it always resolves to a real W/L/E.

    Returns list of (signal_dict, label) for newly evaluated checkpoints.
    """
    col = database.signals()
    now = time.time()
    resolved = []

    for sig in col.find({"outcome": {"$in": ["PENDING", "EVEN", None]}}):
        age    = now - sig.get("timestamp", now)
        ticker = sig["ticker"]
        entry  = sig.get("price_at_signal")
        updates = {}
        newly_resolved = []

        for label, seconds in CHECKPOINTS:
            if sig.get(f"evaluated_{label}"):
                continue
            if age < seconds:
                continue

            if label == "24h":
                # Use historical next-day close — works regardless of market status
                sig_date = datetime.fromtimestamp(
                    sig.get("timestamp", now), tz=CAIRO_TZ
                ).date()
                next_day = sig_date + timedelta(days=1)
                price = _fetch_close_on_or_after(ticker, next_day)
            else:
                # Use live price for intraday checkpoints
                price = prices.get(ticker, {}).get("price")

            if not price:
                continue

            updates[f"price_{label}"]    = price
            updates[f"evaluated_{label}"] = True

            if entry:
                pct = (price - entry) / entry * 100
                updates[f"change_{label}"]  = round(pct, 2)
                updates[f"outcome_{label}"] = _outcome(sig["action"], pct)
            else:
                updates[f"outcome_{label}"] = "NO_DATA"

            newly_resolved.append(label)

        # Final outcome = 24h result once resolved
        o24 = updates.get("outcome_24h") or sig.get("outcome_24h")
        if o24 and o24 not in ("PENDING", None):
            updates["outcome"] = o24

        if updates:
            col.update_one({"_id": sig["_id"]}, {"$set": updates})

        for label in newly_resolved:
            sig.update(updates)
            resolved.append((sig, label))

    return resolved


def get_history(limit: int = 200) -> List[dict]:
    col = database.signals()
    return list(col.find({}, {"_id": 0}).sort("timestamp", -1).limit(limit))


def get_stats() -> dict:
    col = database.signals()
    total   = col.count_documents({})
    pending = col.count_documents({"outcome": "PENDING"})

    wins   = col.count_documents({"outcome_24h": "WIN"})
    losses = col.count_documents({"outcome_24h": "LOSS"})
    evens  = col.count_documents({"outcome_24h": "EVEN"})

    wins_1h  = col.count_documents({"outcome_1h": "WIN"})
    wins_6h  = col.count_documents({"outcome_6h": "WIN"})
    total_1h = col.count_documents({"outcome_1h": {"$in": ["WIN", "LOSS"]}})
    total_6h = col.count_documents({"outcome_6h": {"$in": ["WIN", "LOSS"]}})

    return {
        "total":       total,
        "resolved":    wins + losses + evens,
        "pending":     pending,
        "wins":        wins,
        "losses":      losses,
        "evens":       evens,
        "accuracy_24h": round(wins / (wins + losses) * 100, 1) if (wins + losses) > 0 else None,
        "accuracy_1h":  round(wins_1h / total_1h * 100, 1) if total_1h > 0 else None,
        "accuracy_6h":  round(wins_6h / total_6h * 100, 1) if total_6h > 0 else None,
    }
