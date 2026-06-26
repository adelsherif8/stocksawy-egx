import json
import os
import time
import threading
import httpx
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict
from openai import OpenAI
from egx_stocks import get_stocks_summary
import database
import learning

_thread_local = threading.local()


def _get_client():
    if not hasattr(_thread_local, "client"):
        key = os.getenv("OPENAI_API_KEY", "")
        if key:
            _thread_local.client = OpenAI(
                api_key=key,
                http_client=httpx.Client(timeout=httpx.Timeout(25.0)),
            )
        else:
            _thread_local.client = None
    return _thread_local.client


def analyze_new_articles(news_items: List[Dict]) -> List[Dict]:
    """
    Check MongoDB for already-analyzed articles, only send new ones to OpenAI.
    Returns list of (article + analysis) dicts for ALL items passed in.
    """
    col = database.articles()

    # Split into cached vs new
    existing_ids = set(
        doc["_id"] for doc in col.find({"_id": {"$in": [n["id"] for n in news_items]}}, {"_id": 1})
    )

    cached_items = []
    new_items = []
    for item in news_items:
        if item["id"] in existing_ids:
            doc = col.find_one({"_id": item["id"]})
            if doc:
                cached_items.append({**item, "analysis": doc["analysis"]})
        else:
            new_items.append(item)

    if not new_items:
        print(f"[analyzer] All {len(news_items)} articles from MongoDB — 0 OpenAI calls")
        return cached_items

    print(f"[analyzer] {len(new_items)} new articles → OpenAI | {len(cached_items)} from MongoDB")

    # Analyze new items in parallel (10 threads)
    analyzed_new: Dict[str, Dict] = {}
    with ThreadPoolExecutor(max_workers=10) as pool:
        future_to_item = {pool.submit(_analyze_single, item): item for item in new_items}
        completed = 0
        for future in as_completed(future_to_item, timeout=300):
            item = future_to_item[future]
            completed += 1
            try:
                result = future.result(timeout=30)
            except Exception as e:
                print(f"[analyzer] Failed: {item['title'][:50]} — {e}")
                result = {**item, "analysis": _empty_analysis()}

            analyzed_new[item["id"]] = result
            print(f"[analyzer] {completed}/{len(new_items)}: {item['title'][:55]}")

            # Save to MongoDB immediately
            col.update_one(
                {"_id": item["id"]},
                {"$set": {
                    "_id": item["id"],
                    **result,
                    "analyzed_at": time.time(),
                }},
                upsert=True,
            )

    print(f"[analyzer] Done — {len(new_items)} analyzed, {len(cached_items)} from cache")

    # Return in original order
    id_to_result = {
        **{item["id"]: {**item, "analysis": col.find_one({"_id": item["id"]})["analysis"]} for item in cached_items},
        **analyzed_new,
    }
    return [id_to_result[item["id"]] for item in news_items if item["id"] in id_to_result]


def _analyze_single(item: Dict) -> Dict:
    stocks_summary = get_stocks_summary()
    learning_context = learning.build_learning_context()

    prompt = f"""You are an expert financial analyst specializing in the Egyptian Stock Exchange (EGX) and how global/regional events affect Egyptian stocks.

NEWS ITEM:
Title: {item['title']}
Summary: {item['summary']}
Category: {item['source_label']}

EGX STOCKS BY SECTOR:
{stocks_summary}

{learning_context}

Analyze this news and its potential impact on EGX-listed stocks. Consider:
- Direct sector effects (e.g. oil news → oil stocks)
- Indirect effects (e.g. oil price rise → higher costs for manufacturing, transport)
- Currency effects (dollar/pound changes affect importers vs exporters differently)
- Geopolitical effects on Egyptian tourism, Suez Canal revenue, FDI
- Commodity prices and their effect on Egyptian producers/consumers

Respond ONLY with a valid JSON object (no markdown, no extra text):
{{
  "relevance": "HIGH" | "MEDIUM" | "LOW",
  "sentiment": "BULLISH" | "BEARISH" | "NEUTRAL",
  "urgency": "HIGH" | "MEDIUM" | "LOW",
  "impact_summary": "2-3 sentence analysis of how this affects Egyptian markets",
  "affected_stocks": [
    {{
      "ticker": "TICKER",
      "name": "Company Name",
      "sector": "Sector",
      "action": "BUY" | "SELL" | "WATCH",
      "confidence": "HIGH" | "MEDIUM" | "LOW",
      "expected_change": "+5%" or "-3%",
      "reason": "One sentence explaining why"
    }}
  ]
}}

Only include stocks genuinely affected. Return empty array if no clear impact. Max 6 stocks."""

    c = _get_client()
    if not c:
        return {**item, "analysis": _empty_analysis()}

    try:
        response = c.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=800,
        )
        raw = response.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()
        analysis = json.loads(raw)
        return {**item, "analysis": analysis}
    except json.JSONDecodeError as e:
        print(f"[analyzer] JSON error: {e}")
        return {**item, "analysis": _empty_analysis()}
    except Exception as e:
        print(f"[analyzer] Error: {type(e).__name__}: {e}")
        return {**item, "analysis": _empty_analysis()}


def _empty_analysis():
    return {
        "relevance": "LOW", "sentiment": "NEUTRAL", "urgency": "LOW",
        "impact_summary": "Could not analyze.", "affected_stocks": []
    }


def get_top_recommendations(analyzed_news: List[Dict]) -> List[Dict]:
    stock_scores = {}
    urgency_weight    = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
    confidence_weight = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}

    def _parse_pct(s: str):
        try:
            return float(s.replace("%", "").replace(" ", ""))
        except Exception:
            return None

    for item in analyzed_news:
        analysis = item.get("analysis", {})
        urgency  = analysis.get("urgency", "LOW")
        for stock in analysis.get("affected_stocks", []):
            ticker = stock["ticker"]
            w = urgency_weight[urgency] * confidence_weight.get(stock.get("confidence", "LOW"), 1)
            if ticker not in stock_scores:
                stock_scores[ticker] = {
                    **stock,
                    "score": 0, "news_count": 0, "news_titles": [],
                    "actions": [], "confidences": [],
                    "_pct_sum": 0.0, "_pct_count": 0,
                }
            d = stock_scores[ticker]
            d["score"]       += w
            d["news_count"]  += 1
            d["news_titles"].append(item["title"])
            d["actions"].append(stock["action"])
            d["confidences"].append(stock.get("confidence", "LOW"))
            pct = _parse_pct(stock.get("expected_change", ""))
            if pct is not None and pct != 0:
                d["_pct_sum"]   += pct * w   # weight by urgency×confidence
                d["_pct_count"] += w

            # Keep the reason from the highest-weighted article
            if w >= d["score"] - w:   # this article contributed the most so far
                d["reason"] = stock.get("reason", d.get("reason", ""))

    recommendations = []
    for ticker, data in stock_scores.items():
        # Consensus action
        actions = data["actions"]
        data["action"] = max(set(actions), key=actions.count)

        # Weighted average expected change (skip zeros — they mean "no prediction")
        if data["_pct_count"] > 0:
            avg = data["_pct_sum"] / data["_pct_count"]
            sign = "+" if avg >= 0 else ""
            data["expected_change"] = f"{sign}{avg:.1f}%"
        else:
            data["expected_change"] = ""

        # Consensus confidence
        confs = data["confidences"]
        data["confidence"] = max(set(confs), key=confs.count)

        # Clean up internal fields
        data.pop("_pct_sum", None)
        data.pop("_pct_count", None)

        recommendations.append(data)

    recommendations.sort(key=lambda x: x["score"], reverse=True)
    return recommendations[:15]
