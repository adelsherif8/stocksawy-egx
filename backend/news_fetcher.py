import feedparser
import httpx
import time
import calendar
from datetime import datetime, timezone, timedelta
from typing import List, Dict

CAIRO_TZ = timezone(timedelta(hours=2))

RSS_FEEDS = [
    # ── English feeds ────────────────────────────────────────────────────────
    {
        "url": "https://news.google.com/rss/search?q=EGX+egypt+stock+market&hl=en&gl=EG&ceid=EG:en",
        "label": "EGX Market", "lang": "en"
    },
    {
        "url": "https://news.google.com/rss/search?q=egypt+economy+investment&hl=en&gl=EG&ceid=EG:en",
        "label": "Egypt Economy", "lang": "en"
    },
    {
        "url": "https://news.google.com/rss/search?q=egypt+pound+dollar+CBE+interest+rate&hl=en&gl=EG&ceid=EG:en",
        "label": "Egypt Currency", "lang": "en"
    },
    {
        "url": "https://news.google.com/rss/search?q=oil+gas+price+OPEC+Iran+Saudi+Arabia&hl=en&gl=US&ceid=US:en",
        "label": "Oil & Gas", "lang": "en"
    },
    {
        "url": "https://news.google.com/rss/search?q=Trump+sanctions+Middle+East+economy&hl=en&gl=US&ceid=US:en",
        "label": "Geopolitics", "lang": "en"
    },
    {
        "url": "https://news.google.com/rss/search?q=global+stock+market+Fed+interest+rates&hl=en&gl=US&ceid=US:en",
        "label": "Global Markets", "lang": "en"
    },
    {
        "url": "https://news.google.com/rss/search?q=Suez+Canal+shipping+trade&hl=en&gl=US&ceid=US:en",
        "label": "Suez Canal", "lang": "en"
    },
    {
        "url": "https://news.google.com/rss/search?q=wheat+food+commodity+prices&hl=en&gl=US&ceid=US:en",
        "label": "Commodities", "lang": "en"
    },
    {
        "url": "https://news.google.com/rss/search?q=gold+price+inflation+dollar&hl=en&gl=US&ceid=US:en",
        "label": "Gold & Inflation", "lang": "en"
    },
    {
        "url": "https://news.google.com/rss/search?q=egypt+tourism+real+estate&hl=en&gl=EG&ceid=EG:en",
        "label": "Egypt Tourism & Real Estate", "lang": "en"
    },

    # ── Arabic feeds (Egypt-specific, much better EGX coverage) ─────────────
    {
        "url": "https://news.google.com/rss/search?q=بورصة+مصر+أسهم&hl=ar&gl=EG&ceid=EG:ar",
        "label": "بورصة مصر", "lang": "ar"
    },
    {
        "url": "https://news.google.com/rss/search?q=الاقتصاد+المصري+استثمار&hl=ar&gl=EG&ceid=EG:ar",
        "label": "الاقتصاد المصري", "lang": "ar"
    },
    {
        "url": "https://news.google.com/rss/search?q=البنك+المركزي+الجنيه+الدولار&hl=ar&gl=EG&ceid=EG:ar",
        "label": "العملة المصرية", "lang": "ar"
    },
    {
        "url": "https://news.google.com/rss/search?q=النفط+الغاز+أوبك&hl=ar&gl=EG&ceid=EG:ar",
        "label": "النفط والغاز", "lang": "ar"
    },
    {
        "url": "https://news.google.com/rss/search?q=قناة+السويس+الشحن+التجارة&hl=ar&gl=EG&ceid=EG:ar",
        "label": "قناة السويس", "lang": "ar"
    },
    # Al-Borsa Egyptian financial newspaper RSS
    {
        "url": "https://www.alborsaanews.com/feed/",
        "label": "البورصة نيوز", "lang": "ar"
    },
    # Youm7 economy section
    {
        "url": "https://www.youm7.com/rss/0/4",
        "label": "اليوم السابع اقتصاد", "lang": "ar"
    },
    # Masrawy economy
    {
        "url": "https://www.masrawy.com/rss/economy",
        "label": "مصراوي اقتصاد", "lang": "ar"
    },
]


def _is_recent(ts: float, hours: int = 48) -> bool:
    """Return True if the timestamp is within the last N hours."""
    try:
        return (time.time() - ts) <= hours * 3600
    except Exception:
        return True  # default to including it


def fetch_all_news(max_per_feed: int = 15, today_only: bool = False) -> List[Dict]:
    all_news = []
    seen_titles = set()

    for feed_config in RSS_FEEDS:
        try:
            resp = httpx.get(feed_config["url"], timeout=10, follow_redirects=True,
                             headers={"User-Agent": "Mozilla/5.0 (compatible; StocksawyBot/1.0)"})
            feed = feedparser.parse(resp.text)
            count = 0

            for entry in feed.entries:
                if count >= max_per_feed:
                    break

                title = entry.get("title", "").strip()
                if not title or title in seen_titles:
                    continue

                seen_titles.add(title)

                # Parse published date (published_parsed is UTC, use calendar.timegm)
                try:
                    if hasattr(entry, "published_parsed") and entry.published_parsed:
                        ts = calendar.timegm(entry.published_parsed)  # UTC → unix timestamp
                    else:
                        ts = time.time()
                    pub_str = datetime.fromtimestamp(ts, tz=CAIRO_TZ).strftime("%Y-%m-%d %H:%M")
                except Exception:
                    ts = time.time()
                    pub_str = datetime.now(tz=CAIRO_TZ).strftime("%Y-%m-%d %H:%M")

                # Skip if older than 48 hours
                if not _is_recent(ts, hours=48):
                    continue

                # Clean summary
                import re
                summary = entry.get("summary", entry.get("description", ""))
                summary = re.sub(r"<[^>]+>", "", summary).strip()
                if len(summary) > 400:
                    summary = summary[:400] + "..."

                all_news.append({
                    "id": f"{hash(title) % 10000000:07d}",
                    "title": title,
                    "summary": summary,
                    "source_label": feed_config["label"],
                    "link": entry.get("link", ""),
                    "published": pub_str,
                    "timestamp": ts,
                    "lang": feed_config.get("lang", "en"),
                })
                count += 1

        except Exception as e:
            print(f"Error fetching {feed_config['label']}: {e}")
            continue

    # Sort by most recent
    all_news.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
    return all_news
