"""Fetch NRL fixtures (past results + upcoming) with team badges via TheSportsDB."""
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
    """Returns {team_id: badge_url} for every NRL team — one API call total."""
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


def fetch_nrl_draw(*, lookback_days: int = 4, lookahead_days: int = 7) -> list[dict]:
    upcoming = _fetch_events("eventsnextleague.php", {"id": NRL_LEAGUE_ID})
    past = _fetch_events("eventspastleague.php", {"id": NRL_LEAGUE_ID})

    # Fallback: if both primary endpoints return nothing, try the current season
    if not upcoming and not past:
        season = str(datetime.now(BRISBANE).year)
        print(f"[nrl] primary endpoints empty — trying season fallback ({season})")
        season_events = _fetch_events("eventsseason.php", {"id": NRL_LEAGUE_ID, "s": season})
        past = season_events
        upcoming = []

    badges = _fetch_team_badges()
    now_utc = datetime.now(timezone.utc)
    lookback = now_utc - timedelta(days=lookback_days)
    lookahead = now_utc + timedelta(days=lookahead_days)

    seen_ids: set[str] = set()
    fixtures: list[dict] = []

    for ev in past + upcoming:
        ev_id = ev.get("idEvent")
        if not ev_id or ev_id in seen_ids:
            continue
        seen_ids.add(ev_id)

        parsed = _parse_event(ev, badges, now_utc)
        if not parsed:
            continue
        if parsed["_dt_utc"] < lookback or parsed["_dt_utc"] > lookahead:
            continue

        parsed.pop("_dt_utc", None)
        fixtures.append(parsed)

    fixtures.sort(key=lambda f: f["datetime_iso"])
    print(f"[nrl] final window fixtures: {len(fixtures)}")
    return fixtures
