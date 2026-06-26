import os
import time
import httpx
from typing import List, Dict

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"

ACTION_EMOJI     = {"BUY": "🟢", "SELL": "🔴", "WATCH": "🟡"}
SENTIMENT_EMOJI  = {"BULLISH": "📈", "BEARISH": "📉", "NEUTRAL": "➡️"}
URGENCY_EMOJI    = {"HIGH": "🚨", "MEDIUM": "⚠️", "LOW": "ℹ️"}
CONFIDENCE_LABEL = {"HIGH": "High", "MEDIUM": "Med", "LOW": "Low"}

# Rate-limit: never send more than one digest within this many seconds
_COOLDOWN_SECONDS = 10 * 60   # 10 minutes
_last_sent_at = 0.0


def _get_credentials():
    return os.getenv("TELEGRAM_BOT_TOKEN", ""), os.getenv("TELEGRAM_CHAT_ID", "")


def _send(text: str) -> bool:
    token, chat_id = _get_credentials()
    if not token or not chat_id:
        return False
    try:
        resp = httpx.post(
            TELEGRAM_API.format(token=token),
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=10,
        )
        if resp.status_code != 200:
            print(f"[Telegram] Error {resp.status_code}: {resp.text[:200]}")
            return False
        return True
    except Exception as e:
        print(f"[Telegram] Send failed: {e}")
        return False


def send_new_signals(new_articles: List[Dict]) -> int:
    """
    One clean digest per scheduler run — never per-article.

    Aggregates all BUY/SELL signals from all new articles, deduplicates
    by ticker (highest urgency wins), and sends a single message with the
    top signals. Skips the run if cooldown hasn't expired.
    """
    global _last_sent_at

    token, chat_id = _get_credentials()
    if not token or not chat_id:
        return 0

    now = time.time()
    if now - _last_sent_at < _COOLDOWN_SECONDS:
        return 0  # still cooling down — no spam

    # ── Aggregate signals from all new articles ──────────────────────────────
    URGENCY_RANK = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
    CONF_RANK    = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}

    best: Dict[str, dict] = {}   # ticker → best signal dict

    for article in new_articles:
        analysis  = article.get("analysis", {})
        urgency   = analysis.get("urgency", "LOW")
        sentiment = analysis.get("sentiment", "NEUTRAL")

        for stock in analysis.get("affected_stocks", []):
            if stock.get("action") not in ("BUY", "SELL"):
                continue

            ticker = stock["ticker"]
            score  = URGENCY_RANK.get(urgency, 1) * CONF_RANK.get(stock.get("confidence", "LOW"), 1)

            if ticker not in best or score > best[ticker]["_score"]:
                best[ticker] = {
                    **stock,
                    "_score":     score,
                    "_urgency":   urgency,
                    "_sentiment": sentiment,
                    "_title":     article.get("title", "")[:80],
                    "_link":      article.get("link", ""),
                }

    if not best:
        return 0  # nothing actionable

    # ── Filter: drop LOW urgency + LOW confidence combos ────────────────────
    signals = [
        s for s in best.values()
        if not (s["_urgency"] == "LOW" and s.get("confidence", "LOW") == "LOW")
    ]

    if not signals:
        return 0

    # ── Sort by score, take top 6 ────────────────────────────────────────────
    signals.sort(key=lambda s: s["_score"], reverse=True)
    top = signals[:6]

    # ── Pick header emoji from highest-urgency signal ────────────────────────
    top_urgency  = top[0]["_urgency"]
    top_sentiment = top[0]["_sentiment"]
    urg_emoji  = URGENCY_EMOJI.get(top_urgency, "ℹ️")
    sent_emoji = SENTIMENT_EMOJI.get(top_sentiment, "➡️")

    lines = [
        f"{urg_emoji}{sent_emoji} <b>EGX Signals — {len(signals)} stock{'s' if len(signals)>1 else ''} flagged</b>",
        f"<i>From {len(new_articles)} new article{'s' if len(new_articles)>1 else ''}</i>\n",
    ]

    for s in top:
        act_emoji = ACTION_EMOJI[s["action"]]
        conf      = CONFIDENCE_LABEL.get(s.get("confidence", "LOW"), "")
        exp       = s.get("expected_change", "")
        reason    = s.get("reason", "")[:110]
        lines.append(
            f"{act_emoji} <b>{s['ticker']}</b> · {s['action']}  <b>{exp}</b>\n"
            f"   {conf} confidence · {s.get('sector','')}\n"
            f"   <i>{reason}</i>"
        )

    if len(signals) > 6:
        lines.append(f"\n<i>+{len(signals)-6} more signals in the dashboard</i>")

    if _send("\n".join(lines)):
        _last_sent_at = now
        return 1

    return 0


def send_test_message() -> bool:
    return _send(
        "✅ <b>EGX Stock Bot connected!</b>\n\n"
        "You'll receive one clean digest when new actionable signals are detected.\n"
        "BUY/SELL signals only — no spam."
    )
