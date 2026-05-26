"""Fetch NRL fixtures (past results + upcoming) with team badges via TheSportsDB.

Strategy: TheSportsDB's "next/past 15 events" endpoints often miss data during bye
weeks (State of Origin, finals window, etc.). We fix this by:
  1. Pulling the entire current season via eventsseason.php (most complete).
  2. Combining with next+past for safety.
  3. Filtering to a wide window (-7 to +21 days) so we typically get the current
     round + the next round even when the schedule is irregular.
  4. If literally nothing falls in the window (rare), falling back to the 8 events
     closest to today so the section is never empty for no good reason.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import requests


NRL_LEAGUE_ID = 4435  # National Rugby League on TheSportsDB
BRISBANE = ZoneInfo("Australia/Brisbane")
API_KEY = os.environ.get("THESPORTSDB_KEY", "3")  # "3" = public test key
BASE = f"https://www.thesportsdb.com/api/v1/json/{API_KEY}"


def _format_time(dt) -> str:
    return dt.strftime("%I:%M %p").lstrip("0").lower()


def _get(endpoint: str, params: dict | None = None) -> dict:
    url = f"{BASE}/{endpoint}"
    try:
        r = requests.get(url, params=params or {}, timeout=15)
        print(f"[nrl] GET {endpoint} {params or {}} -> {r.status_code}")
        r.raise_for_status()
        return r.json() or {}
    except Exception as e:
        print(f"[nrl]   FAILED: {e}")
        return {}


def _fetch_events(endpoint: str, params: dict | None = None) -> list[dict]:
    data = _get(endpoint, params)
    events = data.get("events") or []
    print(f"[nrl]   {endpoint}: {len(events)} events")
    return events


def _fetch_team_badges() -> dict[str, str]:
    data = _get("lookup_all_teams.php", {"id": NRL_LEAGUE_ID})
    teams = data.get("teams") or []
    badges = {
        t["idTeam"]: (t.get("strBadge") or t.get("strTeamBadge") or "")
        for t in teams
        if t.get("idTeam")
    }
    print(f"[nrl]   team badges loaded: {len(badges)}")
    return badges


def _parse_event(ev: dict, badges: dict[str, str], now_utc: datetime) -> dict | None:
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
    home_score = ev.get("intHomeScore")
    away_score = ev.get("intAwayScore")
    completed = bool(is_past and home_score not in (None, "") and away_score not in (None, ""))

    return {
        "home": ev.get("strHomeTeam") or "TBC",
        "away": ev.get("strAwayTeam") or "TBC",
        "home_badge": badges.get(ev.get("idHomeTeam") or "", ""),
        "away_badge": badges.get(ev.get("idAwayTeam") or "", ""),
        "home_score": int(home_score) if completed else None,
        "away_score": int(away_score) if completed else None,
        "completed": completed,
        "day": dt_bne.strftime("%a %d %b"),
        "time": _format_time(dt_bne),
        "venue": ev.get("strVenue") or "",
        "datetime_iso": dt_bne.isoformat(),
        "_dt_utc": dt_utc,
    }


def fetch_nrl_draw(*, lookback_days: int = 7, lookahead_days: int = 21) -> list[dict]:
    now_bne = datetime.now(BRISBANE)
    season = str(now_bne.year)

    # Primary: pull the entire current season
    season_events = _fetch_events("eventsseason.php", {"id": NRL_LEAGUE_ID, "s": season})

    # If empty (e.g. very early in the year), try last year too
    if not season_events:
        prev = str(now_bne.year - 1)
        season_events = _fetch_events("eventsseason.php", {"id": NRL_LEAGUE_ID, "s": prev})

    # Belt-and-braces: also pull next+past in case they have something season doesn't
    next_events = _fetch_events("eventsnextleague.php", {"id": NRL_LEAGUE_ID})
    past_events = _fetch_events("eventspastleague.php", {"id": NRL_LEAGUE_ID})

    # Dedupe across sources by event id
    seen_ids: set[str] = set()
    all_events: list[dict] = []
    for ev in season_events + next_events + past_events:
        eid = ev.get("idEvent")
        if not eid or eid in seen_ids:
            continue
        seen_ids.add(eid)
        all_events.append(ev)

    print(f"[nrl] combined unique events from all sources: {len(all_events)}")

    badges = _fetch_team_badges()
    now_utc = datetime.now(timezone.utc)
    lookback = now_utc - timedelta(days=lookback_days)
    lookahead = now_utc + timedelta(days=lookahead_days)

    # Parse everything once
    parsed_all: list[dict] = []
    for ev in all_events:
        p = _parse_event(ev, badges, now_utc)
        if p:
            parsed_all.append(p)

    # Filter to the date window
    in_window = [p for p in parsed_all if lookback <= p["_dt_utc"] <= lookahead]
    in_window.sort(key=lambda p: p["_dt_utc"])
    print(f"[nrl] fixtures in window (-{lookback_days}d to +{lookahead_days}d): {len(in_window)}")

    # Last-resort fallback: if nothing's in the window, show the 8 events closest to today
    if not in_window and parsed_all:
        parsed_all.sort(key=lambda p: abs((p["_dt_utc"] - now_utc).total_seconds()))
        in_window = sorted(parsed_all[:8], key=lambda p: p["_dt_utc"])
        print(f"[nrl] window was empty — falling back to {len(in_window)} closest events")

    # Strip internal datetime field before returning
    for p in in_window:
        p.pop("_dt_utc", None)

    print(f"[nrl] final fixtures returned: {len(in_window)}")
    return in_window
