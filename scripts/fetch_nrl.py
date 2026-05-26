"""Fetch NRL fixtures (past results + upcoming) with team badges via TheSportsDB."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import requests


NRL_LEAGUE_ID = 4435  # National Rugby League on TheSportsDB
BRISBANE = ZoneInfo("Australia/Brisbane")
BASE = "https://www.thesportsdb.com/api/v1/json/3"


def _format_time(dt) -> str:
    """'7:50 pm' — strip leading zero on hour."""
    return dt.strftime("%I:%M %p").lstrip("0").lower()


def _fetch_events(endpoint: str) -> list[dict]:
    url = f"{BASE}/{endpoint}?id={NRL_LEAGUE_ID}"
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        return (r.json() or {}).get("events") or []
    except Exception as e:
        print(f"[nrl] fetch {endpoint} failed: {e}")
        return []


def _fetch_team_badges() -> dict[str, str]:
    """Returns {team_id: badge_url} for every NRL team — one API call total."""
    url = f"{BASE}/lookup_all_teams.php?id={NRL_LEAGUE_ID}"
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        teams = (r.json() or {}).get("teams") or []
        return {
            t["idTeam"]: (t.get("strBadge") or t.get("strTeamBadge") or "")
            for t in teams
            if t.get("idTeam")
        }
    except Exception as e:
        print(f"[nrl] team badges fetch failed: {e}")
        return {}


def fetch_nrl_draw(*, lookback_days: int = 4, lookahead_days: int = 7) -> list[dict]:
    """Combine past results + upcoming fixtures into a single window."""
    upcoming = _fetch_events("eventsnextleague.php")
    past = _fetch_events("eventspastleague.php")
    badges = _fetch_team_badges()

    now = datetime.now(timezone.utc)
    lookback = now - timedelta(days=lookback_days)
    lookahead = now + timedelta(days=lookahead_days)

    seen_ids: set[str] = set()
    fixtures: list[dict] = []

    for ev in past + upcoming:
        ev_id = ev.get("idEvent")
        if not ev_id or ev_id in seen_ids:
            continue
        seen_ids.add(ev_id)

        date_s = ev.get("dateEvent")
        time_s = ev.get("strTime") or "00:00:00"
        if not date_s:
            continue
        try:
            dt_utc = datetime.fromisoformat(f"{date_s}T{time_s}").replace(tzinfo=timezone.utc)
        except Exception:
            continue
        if dt_utc < lookback or dt_utc > lookahead:
            continue

        dt_bne = dt_utc.astimezone(BRISBANE)
        is_past = dt_utc < now
        home_score = ev.get("intHomeScore")
        away_score = ev.get("intAwayScore")
        # treat as completed only if past AND both scores present
        completed = bool(is_past and home_score not in (None, "") and away_score not in (None, ""))

        fixtures.append({
            "home": ev.get("strHomeTeam") or "TBC",
            "away": ev.get("strAwayTeam") or "TBC",
            "home_badge": badges.get(ev.get("idHomeTeam") or "", ""),
            "away_badge": badges.get(ev.get("idAwayTeam") or "", ""),
            "home_score": int(home_score) if completed else None,
            "away_score": int(away_score) if completed else None,
            "completed": completed,
            "day": dt_bne.strftime("%a %d %b"),       # "Fri 30 May"
            "time": _format_time(dt_bne),             # "7:50 pm"
            "venue": ev.get("strVenue") or "",
            "datetime_iso": dt_bne.isoformat(),
        })

    fixtures.sort(key=lambda f: f["datetime_iso"])
    return fixtures
