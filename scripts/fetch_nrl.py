"""Fetch NRL fixtures: TheSportsDB live data + static season-draw JSON fallback.

Why: TheSportsDB's free tier returns very little NRL data during bye rounds
(State of Origin, finals, etc.) — sometimes 0-1 events. To guarantee the section
is always populated, we keep a static copy of the season draw in
config/nrl_draw_{year}.json (parsed once from the NRL's official PDF — see
scripts/parse_nrl_pdf.py).

Strategy each run:
  1. Try TheSportsDB (season + next + past endpoints) — these have SCORES for
     completed games.
  2. Load the static JSON draw — has fixtures + times but NO scores.
  3. Merge: live API wins for any given (date, home, away) so we keep scores
     when available. Static fills gaps when the API has no data.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import requests


ROOT = Path(__file__).resolve().parent.parent
NRL_LEAGUE_ID = 4435
BRISBANE = ZoneInfo("Australia/Brisbane")
SYDNEY = ZoneInfo("Australia/Sydney")  # the PDF's AEDT column is really Sydney local
API_KEY = os.environ.get("THESPORTSDB_KEY", "3")
BASE = f"https://www.thesportsdb.com/api/v1/json/{API_KEY}"


# Order matters: multi-word nicknames first
NICKNAMES = [
    "sea eagles",
    "broncos", "bulldogs", "cowboys", "dolphins", "dragons", "eels",
    "knights", "panthers", "rabbitohs", "raiders", "roosters", "sharks",
    "storm", "tigers", "titans", "warriors",
]


def _normalize_team(name: str) -> str:
    """Strip city prefixes so 'New Zealand Warriors' and 'Warriors' match."""
    s = (name or "").lower().strip()
    for nick in NICKNAMES:
        if s.endswith(nick):
            return nick
    return s


def _format_time(dt) -> str:
    return dt.strftime("%I:%M %p").lstrip("0").lower()


# ---------- TheSportsDB ----------

def _get(endpoint: str, params: dict | None = None) -> dict:
    try:
        r = requests.get(f"{BASE}/{endpoint}", params=params or {}, timeout=15)
        print(f"[nrl] GET {endpoint} {params or {}} -> {r.status_code}")
        r.raise_for_status()
        return r.json() or {}
    except Exception as e:
        print(f"[nrl]   FAILED: {e}")
        return {}


def _fetch_events(endpoint: str, params: dict | None = None) -> list[dict]:
    events = _get(endpoint, params).get("events") or []
    print(f"[nrl]   {endpoint}: {len(events)} events")
    return events


def _fetch_team_badges_by_name() -> dict[str, str]:
    """Return {normalized_team_nickname: badge_url}."""
    data = _get("lookup_all_teams.php", {"id": NRL_LEAGUE_ID})
    teams = data.get("teams") or []
    badges: dict[str, str] = {}
    for t in teams:
        nick = _normalize_team(t.get("strTeam") or "")
        badge = t.get("strBadge") or t.get("strTeamBadge") or ""
        if nick and badge:
            badges[nick] = badge
    print(f"[nrl]   team badges loaded: {len(badges)}")
    return badges


def _parse_api_event(ev: dict, badges: dict[str, str], now_utc: datetime):
    date_s = ev.get("dateEvent")
    time_s = ev.get("strTime") or "00:00:00"
    if not date_s:
        return None
    try:
        dt_utc = datetime.fromisoformat(f"{date_s}T{time_s}").replace(tzinfo=timezone.utc)
    except Exception:
        return None

    dt_bne = dt_utc.astimezone(BRISBANE)
    is_past = dt_utc < now_utc
    hs = ev.get("intHomeScore")
    as_ = ev.get("intAwayScore")
    completed = bool(is_past and hs not in (None, "") and as_ not in (None, ""))

    home = ev.get("strHomeTeam") or "TBC"
    away = ev.get("strAwayTeam") or "TBC"
    return {
        "home": home,
        "away": away,
        "home_badge": badges.get(_normalize_team(home), ""),
        "away_badge": badges.get(_normalize_team(away), ""),
        "home_score": int(hs) if completed else None,
        "away_score": int(as_) if completed else None,
        "completed": completed,
        "day": dt_bne.strftime("%a %d %b"),
        "time": _format_time(dt_bne),
        "venue": ev.get("strVenue") or "",
        "datetime_iso": dt_bne.isoformat(),
        "_dt_utc": dt_utc,
        "_key": _fixture_key(date_s, home, away),
    }


def _fetch_from_api(now_utc: datetime, badges: dict[str, str]) -> list[dict]:
    season = str(now_utc.astimezone(BRISBANE).year)
    season_events = _fetch_events("eventsseason.php", {"id": NRL_LEAGUE_ID, "s": season})
    if not season_events:
        season_events = _fetch_events("eventsseason.php", {"id": NRL_LEAGUE_ID, "s": str(int(season) - 1)})

    next_events = _fetch_events("eventsnextleague.php", {"id": NRL_LEAGUE_ID})
    past_events = _fetch_events("eventspastleague.php", {"id": NRL_LEAGUE_ID})

    seen: set[str] = set()
    parsed: list[dict] = []
    for ev in season_events + next_events + past_events:
        eid = ev.get("idEvent")
        if not eid or eid in seen:
            continue
        seen.add(eid)
        p = _parse_api_event(ev, badges, now_utc)
        if p:
            parsed.append(p)
    print(f"[nrl] parsed {len(parsed)} fixtures from TheSportsDB")
    return parsed


# ---------- Static fallback (PDF -> JSON) ----------

def _fixture_key(date_iso: str, home: str, away: str) -> str:
    return f"{date_iso[:10]}|{_normalize_team(home)}|{_normalize_team(away)}"


def _parse_static_time(date_str: str, time_str: str):
    """Convert PDF date + Sydney-local time -> Brisbane-aware datetime. Returns None for TBC."""
    if not time_str or time_str.upper() == "TBC":
        # Use date with 00:00 so we can still sort/show it
        try:
            d = datetime.strptime(date_str, "%Y-%m-%d")
            return d.replace(hour=0, minute=0, tzinfo=SYDNEY).astimezone(BRISBANE)
        except Exception:
            return None
    try:
        # "8:00 PM" or "8:00PM"
        clean = time_str.upper().replace(" ", "")
        # Split off AM/PM
        if clean.endswith("AM"):
            hm, ampm = clean[:-2], "AM"
        elif clean.endswith("PM"):
            hm, ampm = clean[:-2], "PM"
        else:
            hm, ampm = clean, "PM"
        h, m = hm.split(":")
        h, m = int(h), int(m)
        if ampm == "PM" and h < 12:
            h += 12
        if ampm == "AM" and h == 12:
            h = 0
        d = datetime.strptime(date_str, "%Y-%m-%d")
        dt_syd = d.replace(hour=h, minute=m, tzinfo=SYDNEY)
        return dt_syd.astimezone(BRISBANE)
    except Exception:
        return None


def _load_static_fallback(badges: dict[str, str], now_utc: datetime) -> list[dict]:
    year = now_utc.astimezone(BRISBANE).year
    candidates = [
        ROOT / "config" / f"nrl_draw_{year}.json",
        ROOT / "config" / f"nrl_draw_{year - 1}.json",  # in case it's early in the year
    ]
    for path in candidates:
        if path.exists():
            print(f"[nrl] loading static fallback: {path.name}")
            data = json.loads(path.read_text())
            return _flatten_static(data, badges)
    print("[nrl] no static fallback JSON found")
    return []


def _flatten_static(data: dict, badges: dict[str, str]) -> list[dict]:
    out: list[dict] = []
    for r in data.get("rounds") or []:
        for m in r.get("matches") or []:
            date_str = m.get("date")
            if not date_str:
                continue
            time_str = (m.get("aedt_time") or "").strip()
            dt_bne = _parse_static_time(date_str, time_str)
            if not dt_bne:
                continue
            dt_utc = dt_bne.astimezone(timezone.utc)
            home = m.get("home") or "TBC"
            away = m.get("away") or "TBC"
            out.append({
                "home": home,
                "away": away,
                "home_badge": badges.get(_normalize_team(home), ""),
                "away_badge": badges.get(_normalize_team(away), ""),
                "home_score": None,
                "away_score": None,
                "completed": False,  # static has no scores
                "day": dt_bne.strftime("%a %d %b"),
                "time": "TBC" if time_str.upper() == "TBC" else _format_time(dt_bne),
                "venue": m.get("venue") or "",
                "datetime_iso": dt_bne.isoformat(),
                "_dt_utc": dt_utc,
                "_key": _fixture_key(date_str, home, away),
            })
    print(f"[nrl] static fallback yielded {len(out)} fixtures")
    return out


# ---------- Public entrypoint ----------

def fetch_nrl_draw(*, lookback_days: int = 7, lookahead_days: int = 21) -> list[dict]:
    now_utc = datetime.now(timezone.utc)
    badges = _fetch_team_badges_by_name()

    api_fixtures = _fetch_from_api(now_utc, badges)
    static_fixtures = _load_static_fallback(badges, now_utc)

    # Merge: API wins (has scores). Static fills any gap.
    merged: dict[str, dict] = {}
    for f in static_fixtures:
        merged[f["_key"]] = f
    for f in api_fixtures:
        merged[f["_key"]] = f

    lookback = now_utc - timedelta(days=lookback_days)
    lookahead = now_utc + timedelta(days=lookahead_days)
    in_window = [f for f in merged.values() if lookback <= f["_dt_utc"] <= lookahead]
    in_window.sort(key=lambda f: f["_dt_utc"])

    print(f"[nrl] merged total: {len(merged)}; in window: {len(in_window)}")

    for f in in_window:
        f.pop("_dt_utc", None)
        f.pop("_key", None)

    return in_window
