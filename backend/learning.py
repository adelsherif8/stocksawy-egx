"""
Self-learning module: computes accuracy stats from resolved signals
and feeds them back into the analyzer prompt so the AI calibrates itself.
"""
from collections import defaultdict
from typing import Dict, Any
import database


def compute_learning_stats() -> Dict[str, Any]:
    """
    Pull all resolved signals from MongoDB and compute accuracy by:
    - Overall (1h / 6h / 24h)
    - Per action (BUY / SELL)
    - Per sector
    - Per confidence level
    """
    col = database.signals()

    def _rate(wins, total):
        return round(wins / total * 100, 1) if total > 0 else None

    stats = {}

    for horizon in ["1h", "6h", "24h"]:
        field = f"outcome_{horizon}"
        wins   = col.count_documents({field: "WIN"})
        losses = col.count_documents({field: "LOSS"})
        total  = wins + losses
        stats[f"accuracy_{horizon}"] = _rate(wins, total)
        stats[f"total_resolved_{horizon}"] = total

    # Per action
    for action in ["BUY", "SELL"]:
        w = col.count_documents({"action": action, "outcome_24h": "WIN"})
        t = col.count_documents({"action": action, "outcome_24h": {"$in": ["WIN", "LOSS"]}})
        stats[f"accuracy_action_{action}"] = _rate(w, t)

    # Per confidence
    for conf in ["HIGH", "MEDIUM", "LOW"]:
        w = col.count_documents({"confidence": conf, "outcome_24h": "WIN"})
        t = col.count_documents({"confidence": conf, "outcome_24h": {"$in": ["WIN", "LOSS"]}})
        stats[f"accuracy_confidence_{conf}"] = _rate(w, t)

    # Per sector (top sectors with at least 3 resolved)
    sector_stats = defaultdict(lambda: {"wins": 0, "total": 0})
    for sig in col.find({"outcome_24h": {"$in": ["WIN", "LOSS"]}}):
        sector = sig.get("sector", "Unknown")
        sector_stats[sector]["total"] += 1
        if sig["outcome_24h"] == "WIN":
            sector_stats[sector]["wins"] += 1

    stats["sector_accuracy"] = {
        sector: _rate(d["wins"], d["total"])
        for sector, d in sector_stats.items()
        if d["total"] >= 3
    }

    return stats


def build_learning_context() -> str:
    """
    Returns a text block to inject into the analyzer prompt,
    helping GPT calibrate confidence based on past performance.
    """
    stats = compute_learning_stats()

    total_1h  = stats.get("total_resolved_1h", 0)
    total_24h = stats.get("total_resolved_24h", 0)

    if total_24h < 5:
        return ""  # Not enough data yet to be useful

    lines = ["PERFORMANCE CALIBRATION (learn from past predictions):"]

    acc_1h  = stats.get("accuracy_1h")
    acc_6h  = stats.get("accuracy_6h")
    acc_24h = stats.get("accuracy_24h")

    if acc_1h  is not None: lines.append(f"- 1h accuracy:  {acc_1h}%  ({stats.get('total_resolved_1h',0)} signals)")
    if acc_6h  is not None: lines.append(f"- 6h accuracy:  {acc_6h}%  ({stats.get('total_resolved_6h',0)} signals)")
    if acc_24h is not None: lines.append(f"- 24h accuracy: {acc_24h}% ({total_24h} signals)")

    for action in ["BUY", "SELL"]:
        acc = stats.get(f"accuracy_action_{action}")
        if acc is not None:
            lines.append(f"- {action} signal accuracy: {acc}%")

    for conf in ["HIGH", "MEDIUM", "LOW"]:
        acc = stats.get(f"accuracy_confidence_{conf}")
        if acc is not None:
            lines.append(f"- {conf} confidence accuracy: {acc}%")

    sector_acc = stats.get("sector_accuracy", {})
    if sector_acc:
        lines.append("- Sector accuracy (24h):")
        for sector, acc in sorted(sector_acc.items(), key=lambda x: x[1] or 0, reverse=True):
            lines.append(f"    {sector}: {acc}%")

    lines.append(
        "\nUse this data to calibrate your confidence: if a sector historically "
        "underperforms, lower confidence. Raise confidence for reliably accurate sectors."
    )

    return "\n".join(lines)


def get_full_stats() -> Dict[str, Any]:
    """Returns all learning stats for the API/frontend."""
    stats = compute_learning_stats()
    col = database.signals()

    sector_acc = stats.get("sector_accuracy", {})
    best_sector  = max(sector_acc, key=lambda s: sector_acc[s] or 0) if sector_acc else None
    worst_sector = min(sector_acc, key=lambda s: sector_acc[s] or 0) if sector_acc else None

    # Sector bar chart data
    sector_chart = [
        {"sector": s.replace(" & ", " &\n"), "accuracy": v, "signals": col.count_documents({"sector": s, "outcome_24h": {"$in": ["WIN","LOSS","EVEN"]}})}
        for s, v in sorted(sector_acc.items(), key=lambda x: x[1] or 0, reverse=True)
        if v is not None
    ]

    # Accuracy by day (for line chart)
    from collections import defaultdict
    import time
    daily = defaultdict(lambda: {"wins": 0, "total": 0})
    for sig in col.find({"outcome_24h": {"$in": ["WIN", "LOSS"]}}):
        day = sig.get("date", "")
        daily[day]["total"] += 1
        if sig["outcome_24h"] == "WIN":
            daily[day]["wins"] += 1
    accuracy_over_time = [
        {"date": day, "accuracy": round(d["wins"] / d["total"] * 100, 1), "signals": d["total"]}
        for day, d in sorted(daily.items()) if d["total"] >= 2
    ]

    # Confidence breakdown
    conf_chart = []
    for conf in ["HIGH", "MEDIUM", "LOW"]:
        w = col.count_documents({"confidence": conf, "outcome_24h": "WIN"})
        l = col.count_documents({"confidence": conf, "outcome_24h": "LOSS"})
        e = col.count_documents({"confidence": conf, "outcome_24h": "EVEN"})
        t = w + l + e
        if t > 0:
            conf_chart.append({
                "confidence": conf,
                "wins": w, "losses": l, "evens": e, "total": t,
                "accuracy": round(w / (w + l) * 100, 1) if (w + l) > 0 else None
            })

    # Horizon comparison (1h vs 6h vs 24h)
    horizon_chart = []
    for label in ["1h", "6h", "24h"]:
        w = col.count_documents({f"outcome_{label}": "WIN"})
        l = col.count_documents({f"outcome_{label}": "LOSS"})
        e = col.count_documents({f"outcome_{label}": "EVEN"})
        t = w + l + e
        horizon_chart.append({
            "horizon": label, "wins": w, "losses": l, "evens": e, "total": t,
            "accuracy": round(w / (w + l) * 100, 1) if (w + l) > 0 else None
        })

    # Action breakdown
    action_chart = []
    for action in ["BUY", "SELL", "WATCH"]:
        w = col.count_documents({"action": action, "outcome_24h": "WIN"})
        l = col.count_documents({"action": action, "outcome_24h": "LOSS"})
        e = col.count_documents({"action": action, "outcome_24h": "EVEN"})
        t = w + l + e
        if t > 0:
            action_chart.append({
                "action": action, "wins": w, "losses": l, "evens": e, "total": t,
                "accuracy": round(w / (w + l) * 100, 1) if (w + l) > 0 else None
            })

    # Predicted vs actual scatter data
    scatter = []
    for sig in col.find({"predicted_pct": {"$ne": None}, "change_24h": {"$ne": None}}):
        scatter.append({
            "predicted": sig.get("predicted_pct"),
            "actual": sig.get("change_24h"),
            "ticker": sig.get("ticker"),
            "action": sig.get("action"),
            "outcome": sig.get("outcome_24h"),
        })

    return {
        **stats,
        "best_sector":  {"name": best_sector,  "accuracy": sector_acc.get(best_sector)}  if best_sector  else None,
        "worst_sector": {"name": worst_sector, "accuracy": sector_acc.get(worst_sector)} if worst_sector else None,
        "total_signals": col.count_documents({}),
        "pending": col.count_documents({"outcome": "PENDING"}),
        "sector_chart": sector_chart,
        "accuracy_over_time": accuracy_over_time,
        "confidence_chart": conf_chart,
        "horizon_chart": horizon_chart,
        "action_chart": action_chart,
        "scatter": scatter,
    }
