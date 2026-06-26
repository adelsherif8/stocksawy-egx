import time
import logging
import warnings
import contextlib
import io
from typing import Dict, List

# Silence SSL/urllib3 warning about LibreSSL
warnings.filterwarnings("ignore", message=".*NotOpenSSLWarning.*")
warnings.filterwarnings("ignore", category=Warning, module="urllib3")

# Silence yfinance's own logger (it prints "possibly delisted" etc.)
logging.getLogger("yfinance").setLevel(logging.CRITICAL)
logging.getLogger("peewee").setLevel(logging.CRITICAL)

_cache: Dict[str, dict] = {}
TTL = 300  # 5 minutes

# Known EGX tickers that don't exist on Yahoo Finance — skip them immediately
_UNAVAILABLE = set()

# Overrides for tickers with non-standard Yahoo Finance symbols
YF_OVERRIDES = {
    "CENT": "CEY.L",  # Centamin is on London Stock Exchange
}


def get_egx_prices(tickers: List[str]) -> Dict[str, dict]:
    """Fetch live prices for EGX tickers via yfinance. Cached 5 min, silent on failure."""
    try:
        import yfinance as yf
    except ImportError:
        return {t: {"available": False} for t in tickers}

    now = time.time()
    result = {}
    to_fetch = []

    for t in tickers:
        # Skip tickers we already know don't exist on Yahoo
        if t in _UNAVAILABLE:
            result[t] = {"available": False, "fetched_at": now}
            continue
        c = _cache.get(t)
        if c and (now - c.get("fetched_at", 0)) < TTL:
            result[t] = c
        else:
            to_fetch.append(t)

    for ticker in to_fetch:
        yf_sym = YF_OVERRIDES.get(ticker, f"{ticker}.CA")
        price_data = _fetch_one(yf, yf_sym, now)

        if not price_data["available"]:
            _UNAVAILABLE.add(ticker)  # Don't retry this ticker until restart

        _cache[ticker] = price_data
        result[ticker] = price_data

    return result


def _fetch_one(yf, symbol: str, now: float) -> dict:
    """Fetch a single ticker silently. Returns available=False on any failure."""
    try:
        # Suppress all stdout/stderr from yfinance
        with contextlib.redirect_stderr(io.StringIO()):
            stock = yf.Ticker(symbol)
            hist = stock.history(period="5d", raise_errors=False)

        if hist is None or hist.empty or len(hist) < 2:
            return {"available": False, "fetched_at": now}

        today = float(hist["Close"].iloc[-1])
        prev  = float(hist["Close"].iloc[-2])

        if today == 0 or prev == 0:
            return {"available": False, "fetched_at": now}

        return {
            "price":      round(today, 2),
            "change_pct": round((today - prev) / prev * 100, 2),
            "prev_close": round(prev, 2),
            "day_high":   round(float(hist["High"].iloc[-1]), 2),
            "day_low":    round(float(hist["Low"].iloc[-1]), 2),
            "volume":     int(hist["Volume"].iloc[-1]) if hist["Volume"].iloc[-1] else 0,
            "available":  True,
            "fetched_at": now,
        }
    except Exception:
        return {"available": False, "fetched_at": now}


def enrich_with_prices(items: List[dict], price_map: Dict[str, dict]) -> List[dict]:
    """Attach price_data and already_moved flag to affected stocks in news items."""
    now = time.time()

    for item in items:
        analysis = item.get("analysis", {})
        news_age_hours = (now - item.get("timestamp", now)) / 3600

        for stock in analysis.get("affected_stocks", []):
            ticker = stock.get("ticker", "")
            pd = price_map.get(ticker, {})
            stock["price_data"] = pd

            if pd.get("available") and news_age_hours > 4:
                if abs(pd.get("change_pct", 0)) >= 3:
                    stock["already_moved"] = True
                    stock["moved_pct"] = pd["change_pct"]

    return items
