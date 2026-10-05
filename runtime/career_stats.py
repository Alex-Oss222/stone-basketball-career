"""Read-only player reporting from closed career notes and declared result files.

This module never calls the engine, changes the career clock, or reads historical
player performance. A result without its played note is not career evidence.
"""
from __future__ import annotations

import json
import math
import re
from datetime import date
from pathlib import Path

from .season_rules import month_week, season_start, statistics_bucket

COUNTS = ("pts", "fgm", "fga", "tpm", "tpa", "ftm", "fta", "orb", "drb", "ast", "stl", "blk", "tov", "pf")
PHASES = {
    "02_Summer_League": "summer_league", "05_Preseason": "preseason",
    "06_Regular_Season": "regular", "07_Play_In_Tournament": "play_in",
    "08_Playoffs": "playoff", "10_NBA_Cup": "nba_cup_championship",
}
NATIONAL_TYPES = {"world_cup_qualifier", "world_cup_finals", "olympic_qualifier",
                  "olympic_finals", "continental_qualifier", "continental_finals", "national_friendly"}
NATIONAL_PATHS = {
    ("World_Cup", "Qualifiers"): "world_cup_qualifier",
    ("World_Cup", "Final_Tournament"): "world_cup_finals",
    ("Olympics", "Qualifiers"): "olympic_qualifier",
    ("Olympics", "Final_Tournament"): "olympic_finals",
    ("Continental_Cups", "Qualifiers"): "continental_qualifier",
    ("Continental_Cups", "Final_Tournament"): "continental_finals",
    ("Friendlies", "Games"): "national_friendly",
}


def metadata(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    parts = text.split("---\n", 2)
    if not text.startswith("---\n") or len(parts) != 3:
        raise ValueError(f"{path}: missing or incomplete front matter")
    return dict((k.strip(), v.strip()) for line in parts[1].splitlines() if ":" in line
                for k, v in [line.split(":", 1)])


def identity_at(identity: dict, as_of: str) -> dict:
    cutoff = date.fromisoformat(as_of)
    snapshots = [s for s in identity["snapshots"] if date.fromisoformat(s["as_of"]) <= cutoff]
    if not snapshots:
        raise ValueError(f"no professional identity snapshot available on {as_of}")
    snapshot = max(snapshots, key=lambda s: s["as_of"])
    birth = date.fromisoformat(identity["date_of_birth"])
    age = cutoff.year - birth.year - ((cutoff.month, cutoff.day) < (birth.month, birth.day))
    return {**identity, **snapshot, "age": age, "report_as_of": as_of}


def normalize_line(row: dict, *, weighted_free_throws=False) -> dict:
    """Normalize engine box fields while keeping unavailable optional values null."""
    line = {}
    for key in COUNTS:
        value = row.get(key)
        if type(value) is not int or value < 0:
            raise ValueError(f"{key}: expected a nonnegative observed integer")
        line[key] = value
    seconds = row.get("seconds")
    if isinstance(seconds, bool) or not isinstance(seconds, (int, float)) or not math.isfinite(seconds) or seconds < 0:
        raise ValueError("seconds: expected exact nonnegative playing time")
    line["seconds"] = seconds
    # An engine line without an explicit flag appeared if it has playing time or any box-score contribution: a stint
    # under a second rounds to 0 seconds but can still carry a credited steal (2004-03-05, Dallas at San Antonio).
    appeared = row.get("appeared", seconds > 0 or any(line[k] for k in COUNTS))
    if type(appeared) is not bool:
        raise ValueError("appeared must be a boolean")
    line["appeared"] = appeared
    if not appeared and (seconds > 0 or any(line[k] for k in COUNTS)):
        raise ValueError("DNP cannot have playing time or a box-score contribution")
    started = row.get("started")
    if started is not None and type(started) is not bool:
        raise ValueError("started must be a boolean or null")
    if started and not appeared:
        raise ValueError("a recorded start requires an appearance")
    line["started"] = started
    line["plus_minus"] = row.get("plus_minus")
    if line["plus_minus"] is not None and type(line["plus_minus"]) is not int:
        raise ValueError("plus_minus must be an integer or null")
    if (line["fgm"] > line["fga"] or line["tpm"] > line["tpa"] or
            line["tpm"] > line["fgm"] or line["tpa"] > line["fga"] or
            line["fgm"] - line["tpm"] > line["fga"] - line["tpa"] or line["ftm"] > line["fta"]):
        raise ValueError("impossible shooting line")
    ft_points = row.get("ft_points", None if weighted_free_throws else line["ftm"])
    if type(ft_points) is not int or ft_points < 0:
        raise ValueError("weighted free throws require separately recorded ft_points")
    if not weighted_free_throws and ft_points != line["ftm"]:
        raise ValueError("standard free-throw points must equal free throws made")
    if line["pts"] != 2 * line["fgm"] + line["tpm"] + ft_points:
        raise ValueError("points do not reconcile with recorded shot values")
    line.update(ft_points=ft_points, two_pm=line["fgm"]-line["tpm"],
                two_pa=line["fga"]-line["tpa"], reb=line["orb"]+line["drb"],
                conventional_ts_allowed=not weighted_free_throws)
    return line


def collect_games(player: Path, identity: dict, as_of: str) -> list[dict]:
    """Return canonical game records, including explicit missing-box coverage."""
    aliases = set(identity["aliases"]) | {identity["player_id"]}
    cutoff = date.fromisoformat(as_of)
    records, seen_ids = [], set()
    for note in sorted(player.rglob("Game_*.md")):
        if not re.fullmatch(r"Game_\d+\.md", note.name):
            continue
        relative = note.relative_to(player)
        if relative.parts[0] == "Stats_and_Awards":
            raise ValueError(f"{note}: a summary cannot own a second game record")
        meta = metadata(note)
        status = meta.get("status")
        if meta.get("type") != "game" or status not in {"scheduled", "played", "not_played"}:
            raise ValueError(f"{note}: invalid game type/status")
        if status != "not_played" and (not meta.get("opponent") or meta.get("venue") not in {"home", "away", "neutral"}):
            raise ValueError(f"{note}: scheduled/played games require opponent and home/away/neutral venue")
        if status != "played" and meta.get("result"):
            raise ValueError(f"{note}: an unplayed game cannot have a result")
        if status == "not_played" and not meta.get("reason"):
            raise ValueError(f"{note}: not_played requires a reason")
        national = relative.parts[0] == "National_Team"
        if national:
            kind = meta.get("competition")
            if kind not in NATIONAL_TYPES:
                raise ValueError(f"{note}: national game needs an explicit competition bucket")
            season = meta.get("edition")
            if (len(relative.parts) < 5 or season != relative.parts[2] or
                    NATIONAL_PATHS.get((relative.parts[1], relative.parts[3])) != kind):
                raise ValueError(f"{note}: national edition/competition disagrees with its folder")
            if not meta.get("player_team"):
                raise ValueError(f"{note}: national game needs an explicit national team")
            bucket = kind
        else:
            if len(relative.parts) < 3:
                raise ValueError(f"{note}: game is outside a season phase")
            season = relative.parts[0]
            season_start(season)
            kind = PHASES.get(relative.parts[1])
            if kind is None:
                raise ValueError(f"{note}: game is outside a statistical phase")
            if meta.get("competition") and meta["competition"] != kind:
                raise ValueError(f"{note}: competition conflicts with its owning folder")
            bucket = statistics_bucket(kind, season, meta.get("cup_stage") or None)
            if kind == "nba_cup_championship" and (len(relative.parts) != 4 or relative.parts[2] != "Championship"):
                raise ValueError(f"{note}: only the championship has a canonical Cup-folder game")
        day = meta.get("date", "")
        if status != "not_played" or day:
            date.fromisoformat(day)
        if not national and day:
            year = season_start(season)
            if not date(year, 6, 1) <= date.fromisoformat(day) <= date(year + 1, 6, 30):
                raise ValueError(f"{note}: game date is outside its NBA season cycle")
        if status == "played" and (date.fromisoformat(day) > cutoff or not meta.get("result")):
            raise ValueError(f"{note}: played game needs a result on/before the career cutoff")
        if kind == "regular" and day:
            d = date.fromisoformat(day)
            expected_year = season_start(season) + (d.month < 7)
            if (len(relative.parts) != 5 or d.year != expected_year or
                    relative.parts[2].split("_", 1)[0] != f"{d.month:02d}" or relative.parts[3] != f"Week_{month_week(d.day)}"):
                raise ValueError(f"{note}: game date disagrees with its month/week")
        record = dict(note=note, status=status, date=day, season=season, competition=bucket,
                      opponent=meta.get("opponent") or "Not recorded", venue=meta.get("venue") or "Unknown",
                      result=meta.get("result") or "Not played", event_id=None, line=None,
                      appearance="Not played", coverage="not_played", cup_stage=meta.get("cup_stage") or ("championship" if kind == "nba_cup_championship" else None),
                      team=meta.get("player_team") or identity_at(identity, min(day or as_of, as_of))["team"])
        if status != "played":
            records.append(record)
            continue
        record.update(coverage="missing_box", appearance="Unknown: missing player box")
        result_file = meta.get("result_file")
        if not result_file:
            records.append(record)
            continue
        source = (note.parent / result_file).resolve()
        if source.parent != note.parent.resolve() or not source.is_file():
            raise ValueError(f"{note}: result_file must identify an existing adjacent JSON file")
        raw = json.loads(source.read_text(encoding="utf-8"))
        if not raw.get("terminated") or raw.get("game_date") != day or raw.get("game_type") != kind:
            raise ValueError(f"{note}: result is unfinished or disagrees with note date/competition")
        if not national and raw.get("season") != season:
            raise ValueError(f"{note}: result season disagrees with owning season")
        if national and raw.get("edition") != season:
            raise ValueError(f"{note}: result edition disagrees with owning event")
        event_id = raw.get("event_id")
        if not isinstance(event_id, str) or not event_id or event_id in seen_ids:
            raise ValueError(f"{note}: missing or duplicate canonical event ID")
        if meta.get("event_id") and meta["event_id"] != event_id:
            raise ValueError(f"{note}: event IDs disagree")
        seen_ids.add(event_id)
        scores = raw["final_score"]
        if (type(raw.get("game_seconds")) not in (int, float) or not math.isfinite(raw["game_seconds"]) or
                raw["game_seconds"] <= 0 or raw.get("free_throw_mode", "standard") not in {"standard", "weighted"}):
            raise ValueError(f"{note}: invalid game duration/free-throw mode")
        if any(type(scores.get(s)) is not int or scores[s] < 0 for s in ("home", "away")) or scores["home"] == scores["away"]:
            raise ValueError(f"{note}: invalid final score")
        matches = [(side, r) for side in ("home", "away") for r in raw["player_stats"][side] if r["player_id"] in aliases]
        inactive = [s for s in ("home", "away") if aliases.intersection(raw.get("inactive", {}).get(s, []))]
        listed = None
        if not matches and not inactive:
            # Not in the box because his club had him on its dated injured list for this game (Miami's ledger,
            # `00_Team/Transactions/injured_list.json`): a recorded non-appearance, not missing data.
            listed = _injured_list_entry(Path(note), aliases, raw.get("game_date"))
            if listed:
                inactive = [s for s in ("home", "away") if raw[s] == listed["club"]]
        if len(matches) + len(inactive) > 1:
            raise ValueError(f"{note}: duplicate or contradictory player participation")
        record.update(event_id=event_id, source=source)
        side = matches[0][0] if matches else (inactive[0] if inactive else None)
        if side:
            other = "away" if side == "home" else "home"
            if meta.get("player_team") and meta["player_team"] != raw[side]:
                raise ValueError(f"{note}: recorded player team disagrees with result")
            if meta.get("opponent") != raw[other]:
                raise ValueError(f"{note}: opponent disagrees with result")
            result_label = f"{'W' if scores[side] > scores[other] else 'L'} {scores[side]}-{scores[other]}"
            actual_venue = "neutral" if raw.get("venue") == "neutral" else side
            if meta["result"] != result_label or meta["venue"] != actual_venue:
                raise ValueError(f"{note}: score/venue disagrees with result")
            record.update(team=raw[side], opponent=raw[other], venue="neutral" if raw.get("venue") == "neutral" else side,
                          result=result_label,
                          win=scores[side] > scores[other])
        if matches:
            line = normalize_line(matches[0][1], weighted_free_throws=raw.get("free_throw_mode") == "weighted")
            if line["seconds"] > raw["game_seconds"] + .01:
                raise ValueError(f"{note}: player minutes exceed game duration")
            record.update(line=line, coverage="complete", appearance="Played" if line["appeared"] else "DNP: active")
        elif inactive and listed:
            record.update(coverage="complete", appearance=f"DNP: injured list since {listed['placed']}")
        elif inactive:
            record.update(coverage="complete", appearance="DNP: inactive (reason not specified)")
        # An absent player row is not evidence of either an appearance or a DNP.
        records.append(record)
    return sorted(records, key=lambda r: (r["date"], str(r["note"])))


def _injured_list_entry(note, aliases, game_date):
    """The dated injured-list entry covering `game_date` for the player, from the season's Miami ledger, or None."""
    season = next((p for p in note.parents if p.parent.name == "Dwyane_Wade" and p.name[:2] in ("19", "20")), None)
    ledger = season / "00_Team/Transactions/injured_list.json" if season else None
    if not ledger or not game_date or not ledger.is_file():
        return None
    import json as _json
    for e in _json.loads(ledger.read_text(encoding="utf-8")).get("entries", []):
        if e["player"] in aliases and e["placed"] <= game_date and (e.get("activated") is None or game_date < e["activated"]):
            return {**e, "club": "Miami Heat"}
    return None


def ratio(numerator, denominator):
    return numerator / denominator if denominator else None


def aggregate(records: list[dict]) -> dict:
    if len({r["competition"] for r in records}) > 1:
        raise ValueError("different competitions require separate totals")
    ids = [r["event_id"] for r in records if r.get("event_id")]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate game ID in aggregate")
    closed = [r for r in records if r["status"] == "played"]
    complete = all(r["coverage"] == "complete" for r in closed)
    rows = [r["line"] for r in closed if r.get("line") and r["line"]["appeared"]]
    keys = (*COUNTS, "seconds", "ft_points", "two_pm", "two_pa", "reb")
    totals = {k: sum(r[k] for r in rows) if complete else None for k in keys}
    gp = len(rows) if complete else None
    starts = sum(r["started"] for r in rows) if rows and complete and all(r["started"] is not None for r in rows) else None
    plus_minus = sum(r["plus_minus"] for r in rows) if rows and complete and all(r["plus_minus"] is not None for r in rows) else None
    rates = {}
    for name, made, att in (("fg_pct", "fgm", "fga"), ("two_pct", "two_pm", "two_pa"), ("three_pct", "tpm", "tpa"), ("ft_pct", "ftm", "fta")):
        rates[name] = ratio(totals[made], totals[att]) if complete else None
    rates["efg_pct"] = ratio(totals["fgm"] + .5 * totals["tpm"], totals["fga"]) if complete else None
    ts_allowed = all(r["conventional_ts_allowed"] for r in rows)
    rates["ts_pct"] = ratio(totals["pts"], 2 * (totals["fga"] + .44 * totals["fta"])) if complete and ts_allowed else None
    for name, numerator, denominator in (("ast_to", "ast", "tov"), ("three_rate", "tpa", "fga"), ("ft_rate", "fta", "fga")):
        rates[name] = ratio(totals[numerator], totals[denominator]) if complete else None
    pg = {k: ratio(v, gp) if complete else None for k, v in totals.items()}
    minutes = totals["seconds"] / 60 if complete else None
    pg["minutes"] = ratio(minutes, gp) if complete else None
    per36 = {k: ratio(v * 36, minutes) if complete else None for k, v in totals.items() if k != "seconds"}
    highs = {k: max((r[k] for r in rows), default=None) if complete else None for k in ("pts", "reb", "ast", "stl", "blk", "tov")}
    achievements = [sum(r[k] >= 10 for k in ("pts", "reb", "ast", "stl", "blk")) for r in rows]
    return dict(gp=gp, gs=starts, minutes=minutes, totals=totals, rates=rates, pg=pg, per36=per36,
                plus_minus=plus_minus, closed=len(closed), covered=sum(r["coverage"] == "complete" for r in closed),
                dnp=sum(r["coverage"] == "complete" and r["appearance"].startswith("DNP") for r in closed),
                complete=complete, highs=highs, double_doubles=sum(n >= 2 for n in achievements) if complete else None,
                triple_doubles=sum(n >= 3 for n in achievements) if complete else None, ts_allowed=ts_allowed)


def select(records, *, competition=None, season=None, start=None, end=None):
    return [r for r in records if (competition is None or r["competition"] == competition)
            and (season is None or r["season"] == season)
            and (start is None or r["date"] and r["date"] >= start)
            and (end is None or r["date"] and r["date"] <= end)]
