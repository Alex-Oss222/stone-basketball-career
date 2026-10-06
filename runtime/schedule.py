"""League regular-season schedules: import, canonical form and validation.

A schedule is pre-season knowledge (dates and matchups), so it may be loaded
before the season. Results are not: any score, overtime, attendance or record
field is stripped on import and refused by validation.

Canonical file: library/<start year>/league/nba_<YYYY>_<YY>_schedule.json
"""
from datetime import date, datetime, timedelta
from pathlib import Path
import csv
import io
import json
import re
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
GAME_FIELDS = {"game_id", "date", "away", "home"}
SCHEDULE_RE = re.compile(r"^nba_(\d{4})_(\d{2})_(preseason_)?schedule\.json$")
KINDS = {"regular_season_schedule": "schedule", "preseason_schedule": "preseason_schedule"}

# Abbreviations used by common sources (Basketball-Reference, ESPN, NBA.com) in
# the mid-2000s, mapped to the club names used in the league library.
ALIASES = {
    "ATL": "Atlanta Hawks", "BOS": "Boston Celtics", "CHI": "Chicago Bulls", "CLE": "Cleveland Cavaliers",
    "DAL": "Dallas Mavericks", "DEN": "Denver Nuggets", "DET": "Detroit Pistons",
    "GS": "Golden State Warriors", "GSW": "Golden State Warriors", "HOU": "Houston Rockets",
    "IND": "Indiana Pacers", "LAC": "Los Angeles Clippers", "LAL": "Los Angeles Lakers",
    "MEM": "Memphis Grizzlies", "MIA": "Miami Heat", "MIL": "Milwaukee Bucks", "MIN": "Minnesota Timberwolves",
    "NJ": "New Jersey Nets", "NJN": "New Jersey Nets", "NO": "New Orleans Hornets", "NOH": "New Orleans Hornets",
    "NY": "New York Knicks", "NYK": "New York Knicks", "ORL": "Orlando Magic", "PHI": "Philadelphia 76ers",
    "PHX": "Phoenix Suns", "PHO": "Phoenix Suns", "POR": "Portland Trail Blazers", "SAC": "Sacramento Kings",
    "SA": "San Antonio Spurs", "SAS": "San Antonio Spurs", "SEA": "Seattle SuperSonics", "TOR": "Toronto Raptors",
    "UTA": "Utah Jazz", "UTAH": "Utah Jazz", "WAS": "Washington Wizards", "WSH": "Washington Wizards",
    "CHA": "Charlotte Bobcats",
}
DATE_KEYS = ("date", "game date", "game_date", "gamedate")
AWAY_KEYS = ("visitor/neutral", "visitor", "away", "away team", "away_team", "road", "visiting team", "visitor team")
HOME_KEYS = ("home/neutral", "home", "home team", "home_team")


# Seasons that legitimately differ from 82 games per club. Each entry records why.
SEASON_EXCEPTIONS = {
    "2011-12": {"games_per_team": {"*": 66}, "preseason_window": ((2011, 12, 1), (2011, 12, 24)),
                "note": "Lockout-shortened season: 66 games per club from December 25, 2011."},
    "2012-13": {"games_per_team": {"Boston Celtics": 81, "Indiana Pacers": 81},
                "note": "Indiana at Boston on April 16, 2013 was cancelled after the Boston Marathon "
                        "bombing and not made up."},
}


def games_per_team(season, team):
    rule = SEASON_EXCEPTIONS.get(season, {}).get("games_per_team", {})
    return rule.get(team, rule.get("*", 82))


def team_count(season):
    """29 clubs through 2003-04; the Charlotte Bobcats made 30 from 2004-05."""
    return 29 if int(season[:4]) <= 2003 else 30


def schedule_path(season, root=ROOT, kind="regular_season_schedule"):
    start = int(season[:4])
    return Path(root) / "library" / str(start) / "league" / f"nba_{start}_{season[-2:]}_{KINDS[kind]}.json"


def season_of_date(d):
    return f"{d.year if d.month >= 7 else d.year - 1}-{str((d.year if d.month >= 7 else d.year - 1) + 1)[-2:]}"


def slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def game_id(day, away, home):
    return f"{day}-{slug(away)}-at-{slug(home)}"


def parse_date(value):
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return date(1899, 12, 30) + timedelta(days=int(value))  # spreadsheet serial date
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%a, %b %d, %Y", "%a %b %d %Y", "%b %d, %Y", "%B %d, %Y",
                "%m/%d/%Y", "%m/%d/%y", "%Y%m%d", "%d-%b-%Y", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    raise ValueError(f"unrecognized date {text!r}")


def normalize_team(value, known=None):
    text = re.sub(r"\s+", " ", str(value)).strip().rstrip("*")
    name = ALIASES.get(text.upper(), text)
    if known is not None and name not in known:
        raise ValueError(f"unknown team {text!r}")
    return name


def _xlsx_rows(path):
    """Minimal .xlsx reader (first worksheet) using only the standard library."""
    ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with zipfile.ZipFile(path) as z:
        shared = []
        if "xl/sharedStrings.xml" in z.namelist():
            for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("m:si", ns):
                shared.append("".join(t.text or "" for t in si.iter(f"{{{ns['m']}}}t")))
        sheet = sorted(n for n in z.namelist() if n.startswith("xl/worksheets/sheet"))[0]
        rows = []
        for row in ET.fromstring(z.read(sheet)).iter(f"{{{ns['m']}}}row"):
            cells = {}
            for c in row.findall("m:c", ns):
                col = re.match(r"[A-Z]+", c.get("r")).group()
                index = 0
                for ch in col:
                    index = index * 26 + ord(ch) - 64
                v = c.find("m:v", ns)
                inline = c.find("m:is", ns)
                if c.get("t") == "s" and v is not None:
                    value = shared[int(v.text)]
                elif inline is not None:
                    value = "".join(t.text or "" for t in inline.iter(f"{{{ns['m']}}}t"))
                elif v is not None:
                    value = float(v.text) if re.fullmatch(r"-?\d+(\.\d+)?", v.text) else v.text
                else:
                    value = ""
                cells[index - 1] = value
            rows.append([cells.get(i, "") for i in range(max(cells) + 1)] if cells else [])
        return rows


def _rows(path):
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".xlsx":
        return _xlsx_rows(path)
    if suffix == ".json":
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        games = data.get("games", data) if isinstance(data, dict) else data
        if not isinstance(games, list) or not games or not isinstance(games[0], dict):
            raise ValueError("JSON schedule must be a list of games or {\"games\": [...]}")
        header = list(games[0])
        return [header] + [[g.get(k, "") for k in header] for g in games]
    text = path.read_text(encoding="utf-8-sig")
    dialect = "excel-tab" if suffix == ".tsv" or text.count("\t") > text.count(",") else "excel"
    return list(csv.reader(io.StringIO(text), dialect))


def _column(header, keys, used=()):
    lowered = [str(h).strip().lower() for h in header]
    for key in keys:
        for i, h in enumerate(lowered):
            if h == key and i not in used:
                return i
    raise ValueError(f"no column for {keys[0]!r} in header {header}")


def source_header(path):
    """(kind, source) declared by a JSON export, when it declares them."""
    if Path(path).suffix.lower() == ".json":
        data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
        if isinstance(data, dict):
            return data.get("kind", "regular_season_schedule"), data.get("source")
    return "regular_season_schedule", None


def read_games(path, known=None):
    """Return (games, stripped_columns) from a CSV/TSV/JSON/XLSX schedule export."""
    rows = [r for r in _rows(path) if any(str(c).strip() for c in r)]
    header_index = next(i for i, r in enumerate(rows)
                        if any(str(c).strip().lower() in DATE_KEYS for c in r))
    header = rows[header_index]
    d, a = _column(header, DATE_KEYS), _column(header, AWAY_KEYS)
    h = _column(header, HOME_KEYS, used={a})
    stripped = sorted({str(c).strip() for i, c in enumerate(header) if i not in (d, a, h) and str(c).strip()})
    games = []
    for row in rows[header_index + 1:]:
        first = str(row[0]).strip().lower() if row else ""
        if first == "playoffs":
            break  # Basketball-Reference marks the start of the postseason this way
        if len(row) <= max(d, a, h) or str(row[d]).strip().lower() in DATE_KEYS:
            continue  # repeated header lines in month-by-month exports
        day = parse_date(row[d])
        away, home = normalize_team(row[a], known), normalize_team(row[h], known)
        games.append({"game_id": game_id(day.isoformat(), away, home), "date": day.isoformat(),
                      "away": away, "home": home})
    return games, stripped


def known_teams(season, root=ROOT):
    """Club names from the library roster file for the season's start year, when one exists."""
    path = Path(root) / "library" / season[:4] / "league" / f"nba_{season[:4]}_end_of_season.json"
    if path.is_file():
        return set(json.loads(path.read_text(encoding="utf-8"))["clubs"])
    return None


def validate_schedule(data, season, root=ROOT, kind="regular_season_schedule"):
    """Regular seasons must be complete (82 per team); preseasons only need clean games."""
    errors = []
    if data.get("league") != "NBA" or data.get("season") != season or data.get("kind") != kind:
        errors.append(f"header must be league NBA, matching season, kind {kind}")
    games = data.get("games")
    if not isinstance(games, list) or not games:
        return errors + ["games must be a nonempty list"]
    known = known_teams(season, root)
    counts, seen_ids, per_day = {}, set(), set()
    start = int(season[:4])
    for g in games:
        if not isinstance(g, dict) or set(g) != GAME_FIELDS:
            errors.append(f"game fields must be exactly {sorted(GAME_FIELDS)} (no results): {g}")
            continue
        day = date.fromisoformat(g["date"])
        if kind == "regular_season_schedule":
            window = (date(start, 10, 1), date(start + 1, 4, 30))
        else:
            custom = SEASON_EXCEPTIONS.get(season, {}).get("preseason_window")
            window = tuple(date(*d) for d in custom) if custom else (date(start, 9, 15), date(start, 10, 31))
        if not window[0] <= day <= window[1]:
            errors.append(f"{g['game_id']}: date outside the regular-season window")
        if g["away"] == g["home"]:
            errors.append(f"{g['game_id']}: team plays itself")
        if g["game_id"] != game_id(g["date"], g["away"], g["home"]) or g["game_id"] in seen_ids:
            errors.append(f"{g['game_id']}: game_id must be unique and match date/away/home")
        seen_ids.add(g["game_id"])
        for team in (g["away"], g["home"]):
            if known is not None and team not in known:
                errors.append(f"{g['game_id']}: {team} is not a club in the library")
            if (team, g["date"]) in per_day:
                errors.append(f"{team} plays twice on {g['date']}")
            per_day.add((team, g["date"]))
            counts[team] = counts.get(team, 0) + 1
    if kind != "regular_season_schedule":
        return errors
    expected = team_count(season)
    if len(counts) != expected:
        errors.append(f"{len(counts)} teams; {season} has {expected}")
    for team, n in sorted(counts.items()):
        if n != games_per_team(season, team):
            errors.append(f"{team} has {n} games, expected {games_per_team(season, team)}")
    total = sum(games_per_team(season, team) for team in counts) // 2
    if len(games) != total:
        errors.append(f"{len(games)} games, expected {total}")
    return errors


def schedule_errors(root=ROOT):
    errors = []
    for path in sorted((Path(root) / "library").glob("*/league/nba_*_schedule.json")):
        rel = path.relative_to(root)
        m = SCHEDULE_RE.match(path.name)
        if not m or path.parent.parent.name != m.group(1):
            errors.append(f"{rel}: must be library/<start year>/league/nba_<YYYY>_<YY>_schedule.json")
            continue
        season = f"{m.group(1)}-{m.group(2)}"
        kind = "preseason_schedule" if m.group(3) else "regular_season_schedule"
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"{rel}: invalid JSON: {exc}")
            continue
        errors += [f"{rel}: {e}" for e in validate_schedule(data, season, root, kind)]
    for path in sorted((Path(root) / "library").glob("*/league/nba_*_schedule_by_team.json")):
        errors += by_team_errors(path, root)
    return errors


def by_team_errors(path, root=ROOT):
    """A season's schedule by team (user-supplied, October 2026) is an independent view of the same games: every club
    plays 82, each game appears in both clubs' lists with matching date and venue, and the set of games equals the
    regular-season schedule the builders play from (`nba_<YYYY>_<YY>_schedule.json` beside it)."""
    rel = Path(path).relative_to(root)
    try:
        teams = json.loads(Path(path).read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"{rel}: invalid JSON: {exc}"]
    errors, seen = [], {}
    for club, rows in teams.items():
        if len(rows) != 82:
            errors.append(f"{rel}: {club} has {len(rows)} games, not 82")
        for g in rows:
            if g.get("home_away") not in ("home", "away"):
                errors.append(f"{rel}: {club} {g.get('date')}: home_away must be home or away")
                continue
            key = (g["date"], g["opponent"], club) if g["home_away"] == "home" else (g["date"], club, g["opponent"])
            seen[key] = seen.get(key, 0) + 1
    errors += [f"{rel}: {d} {a} at {h} is listed by {n} club(s), not both" for (d, a, h), n in sorted(seen.items()) if n != 2]
    games_path = Path(path).with_name(Path(path).name.replace("_by_team", ""))
    if games_path.is_file():
        games = {(g["date"], g["away"], g["home"]) for g in json.loads(games_path.read_text(encoding="utf-8"))["games"]}
        missing, extra = sorted(set(games) - set(seen)), sorted(set(seen) - set(games))
        if missing or extra:
            errors.append(f"{rel}: differs from {games_path.name}: {len(missing)} game(s) only there, {len(extra)} only here "
                          f"(first: {(missing or extra)[0]})")
    return errors
