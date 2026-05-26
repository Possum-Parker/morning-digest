"""One-shot parser: NRL season-draw PDF -> structured JSON.

Usage (run manually, ~once per year when the NRL releases the new draw):

    pip install pdfplumber
    python scripts/parse_nrl_pdf.py path/to/nrl-draw-YYYY.pdf YYYY config/nrl_draw_YYYY.json

The output JSON is used as a fallback by fetch_nrl.py when TheSportsDB's free tier
returns insufficient fixture data (which happens often during bye rounds, finals,
or for less-popular leagues on the free key).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pdfplumber  # type: ignore


MONTH_MAP = {"Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
             "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12}

# Order matters: multi-word nicknames first so they match before single-word ones.
TEAMS = [
    "Sea Eagles", "Wests Tigers",
    "Broncos", "Bulldogs", "Cowboys", "Dolphins", "Dragons", "Eels",
    "Knights", "Panthers", "Rabbitohs", "Raiders", "Roosters", "Sharks",
    "Storm", "Tigers", "Titans", "Warriors",
]

ROUND_RE = re.compile(r"^Round\s+(.+?)\s*$", re.IGNORECASE)
DATE_HEADER_RE = re.compile(r"^(\w+day),?\s+(\w+)\s+(\d+)\s+STADIUM", re.IGNORECASE)
BYES_RE = re.compile(r"^Byes?:\s*(.+)$", re.IGNORECASE)
TIMES_TAIL_RE = re.compile(
    r"\s+(TBC|\d{1,2}:\d{2}\s*[AP]M)\s+(TBC|\d{1,2}:\d{2}\s*[AP]M)\s*$",
    re.IGNORECASE,
)


def parse_date(text: str, year: int):
    m = re.match(r"(\w+day),?\s+(\w+)\s+(\d+)", text)
    if not m:
        return None
    month = MONTH_MAP.get(m.group(2)[:3].capitalize())
    if not month:
        return None
    return f"{year}-{month:02d}-{int(m.group(3)):02d}"


def parse_match(line: str):
    m = TIMES_TAIL_RE.search(line)
    if not m:
        return None
    aedt_time = m.group(1).strip()
    local_time = m.group(2).strip()
    head = line[: m.start()].strip()

    # Optional network in parens
    network = ""
    net = re.search(r"\s*\(([^)]+)\)\s*$", head)
    if net:
        network = net.group(1).strip()
        head = head[: net.start()].strip()

    vs = re.search(r"\s+vs\.?\s+", head, re.IGNORECASE)
    if not vs:
        return None
    home = head[: vs.start()].strip()
    after = head[vs.end():].strip()

    away = None
    venue = ""
    for team in TEAMS:
        if after.startswith(team + " ") or after == team:
            away = team
            venue = after[len(team):].strip()
            break
    if not away:
        parts = after.split(maxsplit=1)
        away = parts[0]
        venue = parts[1] if len(parts) > 1 else ""

    return {
        "home": home,
        "away": away,
        "venue": venue,
        "network": network,
        "aedt_time": aedt_time,
        "local_time": local_time,
    }


def parse_pdf(pdf_path: Path, year: int) -> dict:
    rounds: list[dict] = []
    current_round: dict | None = None
    current_date: str | None = None

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            for raw in text.split("\n"):
                line = raw.strip()
                if not line:
                    continue

                rm = ROUND_RE.match(line)
                if rm:
                    if current_round and (current_round["matches"] or current_round["byes"]):
                        rounds.append(current_round)
                    current_round = {"round": rm.group(1).strip(), "matches": [], "byes": []}
                    current_date = None
                    continue

                dm = DATE_HEADER_RE.match(line)
                if dm and current_round is not None:
                    current_date = parse_date(f"{dm.group(1)}, {dm.group(2)} {dm.group(3)}", year)
                    continue

                bm = BYES_RE.match(line)
                if bm and current_round is not None:
                    teams = [t.strip() for t in re.split(r"[,;]", bm.group(1)) if t.strip()]
                    current_round["byes"].extend(teams)
                    continue

                match = parse_match(line)
                if match and current_round is not None and current_date:
                    match["date"] = current_date
                    current_round["matches"].append(match)

    if current_round and (current_round["matches"] or current_round["byes"]):
        rounds.append(current_round)

    return {"season": year, "rounds": rounds}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python parse_nrl_pdf.py <pdf> [year] [output.json]")
        sys.exit(1)
    src = Path(sys.argv[1])
    year = int(sys.argv[2]) if len(sys.argv) > 2 else 2026
    out = Path(sys.argv[3]) if len(sys.argv) > 3 else Path(f"nrl_draw_{year}.json")
    data = parse_pdf(src, year)
    out.write_text(json.dumps(data, indent=2))
    total = sum(len(r["matches"]) for r in data["rounds"])
    print(f"Parsed {len(data['rounds'])} rounds, {total} matches -> {out}")
