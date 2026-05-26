"""Fetch news headlines via Google News RSS, then extract real article text with trafilatura.

Why: Google News RSS only gives us titles. Without article text, Claude can only paraphrase
headlines — it can't tell you *which* player was injured or *what number* a policy is changing.
Trafilatura fetches each article and extracts the main body text, which we pass to Claude so
the digest blurbs become self-contained and specific.
"""
from __future__ import annotations

import urllib.parse
from datetime import datetime, timedelta, timezone

import feedparser

try:
    import trafilatura
    _CAN_EXTRACT = True
except Exception as e:  # pragma: no cover
    print(f"[news] trafilatura unavailable, blurbs will be vague: {e}")
    _CAN_EXTRACT = False


GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q={query}&hl=en-AU&gl=AU&ceid=AU:en"


def _within_last_hours(published_parsed, hours: int) -> bool:
    if not published_parsed:
        return True
    try:
        published = datetime(*published_parsed[:6], tzinfo=timezone.utc)
    except Exception:
        return True
    return published >= datetime.now(timezone.utc) - timedelta(hours=hours)


def fetch_query(
    query: str,
    *,
    max_items: int = 8,
    lookback_hours: int = 36,
    exclude_keywords: list[str] | None = None,
) -> list[dict]:
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


def _extract_article_text(url: str, *, max_chars: int = 1800) -> str:
    """Fetch + extract main article text. Returns empty string on failure (paywalls, JS-only, etc.)."""
    if not _CAN_EXTRACT or not url:
        return ""
    try:
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            return ""
        text = trafilatura.extract(
            downloaded,
            include_comments=False,
            include_tables=False,
            favor_precision=True,
        )
        if not text:
            return ""
        text = " ".join(text.split())  # collapse whitespace
        return text[:max_chars].strip()
    except Exception as e:
        print(f"[news] extract failed for {url[:80]}: {e}")
        return ""


def fetch_topic(
    queries: list[str],
    *,
    exclude_keywords: list[str] | None = None,
    per_query_max: int = 5,
    enrich_top_n: int = 6,
) -> list[dict]:
    """Fetch multiple queries for one topic, dedupe by title, enrich top N with full article text."""
    seen: set[str] = set()
    combined: list[dict] = []
    for q in queries:
        for item in fetch_query(q, max_items=per_query_max, exclude_keywords=exclude_keywords):
            key = item["title"].strip().lower()
            if key in seen:
                continue
            seen.add(key)
            combined.append(item)

    enriched = 0
    for item in combined[:enrich_top_n]:
        text = _extract_article_text(item.get("link", ""))
        if text:
            item["text"] = text
            enriched += 1

    print(f"[news] topic: {len(combined)} items, {enriched}/{min(enrich_top_n, len(combined))} enriched with body text")
    return combined
