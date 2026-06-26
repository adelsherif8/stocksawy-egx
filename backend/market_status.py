from datetime import datetime, timezone, timedelta

# Egypt is UTC+2 year-round (no DST since 2011)
CAIRO_TZ = timezone(timedelta(hours=2))

# EGX trading: Sunday–Thursday, 10:00–14:30 Cairo time
# Python weekday(): Mon=0, Tue=1, Wed=2, Thu=3, Fri=4, Sat=5, Sun=6
TRADING_DAYS = {6, 0, 1, 2, 3}  # Sun, Mon, Tue, Wed, Thu
OPEN_HOUR, OPEN_MIN = 10, 0
CLOSE_HOUR, CLOSE_MIN = 14, 30


def get_market_status() -> dict:
    now = datetime.now(CAIRO_TZ)
    weekday = now.weekday()
    is_trading_day = weekday in TRADING_DAYS

    open_time = now.replace(hour=OPEN_HOUR, minute=OPEN_MIN, second=0, microsecond=0)
    close_time = now.replace(hour=CLOSE_HOUR, minute=CLOSE_MIN, second=0, microsecond=0)

    if not is_trading_day:
        day_name = now.strftime("%A")
        return {
            "open": False,
            "label": "Weekend",
            "detail": f"EGX closed ({day_name})",
            "next_open": _next_open_str(now),
            "cairo_time": now.strftime("%H:%M"),
        }

    if now < open_time:
        mins = int((open_time - now).total_seconds() / 60)
        h, m = divmod(mins, 60)
        eta = f"{h}h {m}m" if h else f"{m}m"
        return {
            "open": False,
            "label": "Pre-Market",
            "detail": f"Opens in {eta}",
            "next_open": open_time.strftime("%H:%M"),
            "cairo_time": now.strftime("%H:%M"),
        }

    if now > close_time:
        return {
            "open": False,
            "label": "Closed",
            "detail": "Closed for today",
            "next_open": _next_open_str(now),
            "cairo_time": now.strftime("%H:%M"),
        }

    mins_left = int((close_time - now).total_seconds() / 60)
    h, m = divmod(mins_left, 60)
    eta = f"{h}h {m}m" if h else f"{m}m"
    return {
        "open": True,
        "label": "Market Open",
        "detail": f"Closes in {eta}",
        "next_open": None,
        "cairo_time": now.strftime("%H:%M"),
    }


def should_auto_refresh() -> bool:
    """Return True only during EGX trading hours + 30 min buffer around open/close."""
    now = datetime.now(CAIRO_TZ)
    weekday = now.weekday()
    if weekday not in TRADING_DAYS:
        return False
    open_time = now.replace(hour=OPEN_HOUR - 1, minute=30, second=0, microsecond=0)  # 30min before open
    close_time = now.replace(hour=CLOSE_HOUR, minute=CLOSE_MIN + 30, second=0, microsecond=0)  # 30min after close
    return open_time <= now <= close_time


def _next_open_str(now: datetime) -> str:
    """Find next Sunday-Thursday after now."""
    candidate = now + timedelta(days=1)
    for _ in range(7):
        if candidate.weekday() in TRADING_DAYS:
            return candidate.replace(hour=OPEN_HOUR, minute=OPEN_MIN).strftime("%a %H:%M")
        candidate += timedelta(days=1)
    return "N/A"
