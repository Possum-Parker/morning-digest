"""Fetch news headlines via Google News RSS (no API key required)."""
from __future__ import annotations

import urllib.parse
from datetime import datetime, timedelta, timezone

import feedparser


GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q={query}&hl=en-AU&gl=AU&ceid=AU:en"


def _within_last_hours(published_parsed, hours: int) -> bool:
    if not published_parsed:
        return True
    try:
        published = datetime(*published_parsed[:6], tzinfo=timezone.utc)
    except Exception:
        return True
    return published >= datetime.now(timezone.utc) - timedelta(hours=hours)


def fetch_query(query: str, *, max_items: int = 8, lookback_hours: int = 36, exclude_keywords: list[str] | None = None) -> list[dict]:
    url = GOOGLE_NEWS_RSS.format(query=urllib.parse.quote(query))
    feed = feedparser.parse(url)
    excludes = [k.lower() for k in (exclude_keywords or [])]

    items: list[dict] = []
    for entry in feed.entries:
        title = entry.get("title", "")
        if any(k in title.lower() for k in excludes):
            continue
        if not _within_last_hours(entry.get("published_parsed"), lookback_hours):
            continue
        items.append({
            "title": title,
            "source": (entry.get("source", {}) or {}).get("title", ""),
            "link": entry.get("link", ""),
            "published": entry.get("published", ""),
        })
        if len(items) >= max_items:
            break
    return items


def fetch_topic(queries: list[str], *, exclude_keywords: list[str] | None = None, per_query_max: int = 5) -> list[dict]:
    """Fetch multiple queries for one topic and dedupe by title."""
    seen: set[str] = set()
    combined: list[dict] = []
    for q in queries:
        for item in fetch_query(q, max_items=per_query_max, exclude_keywords=exclude_keywords):
            key = item["title"].strip().lower()
            if key in seen:
                continue
            seen.add(key)
            combined.append(item)
    return combined
