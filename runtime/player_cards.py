"""Live Shooting and Awards views from closed career evidence.

No preview fixture or historical player data is imported here. Coordinates are
read only from an explicitly declared, dated shot_file beside a closed note.
The module returns artifacts; it never writes career state or runs the engine.
"""
from __future__ import annotations

import calendar
import hashlib
from datetime import date
from html import escape
import json
import os
from pathlib import Path
import re

from .career_stats import aggregate, identity_at, metadata, select
from .season_rules import month_week
from .shot_chart import NBA_GEOMETRY, ZONES, aggregate_shots

GENERATED = "<!-- Generated from closed career records by scripts/update_player_reports.py. -->\n"
NBA_SHOT_COMPETITIONS = {"regular", "preseason", "playoff", "play_in", "nba_cup_championship"}
COMPETITIONS = {"regular": "NBA regular season", "preseason": "NBA preseason", "playoff": "NBA playoffs",
    "play_in": "Play-In", "nba_cup_championship": "NBA Cup championship", "summer_league": "Summer League",
    "world_cup_qualifier": "World Cup qualifiers", "world_cup_finals": "World Cup final tournament",
    "olympic_qualifier": "Olympic qualifiers", "olympic_finals": "Olympic tournament",
    "continental_qualifier": "Continental qualifiers", "continental_finals": "Continental tournament",
    "national_friendly": "National-team friendlies"}


def relative(page, target):
    return Path(os.path.relpath(target, page.parent)).as_posix()


def period_id(competition, season, kind="season", start=None, event_id=None):
    if kind == "game":
        token = hashlib.sha256(str(event_id).encode()).hexdigest()[:16]
    else:
        token = start or ""
    return re.sub(r"[^a-zA-Z0-9_-]", "-", "-".join(filter(None, (competition, season, kind, token))))


def period_for_scope(scope, records, page=None, player=None):
    competition, season = scope.get("competition") or "regular", scope.get("season")
    if not season:
        return None
    if page and re.fullmatch(r"Game_\d+\.md", page.name) and len(records) == 1:
        r = records[0]
        fallback = Path(r["note"]).relative_to(player).as_posix() if player else str(r.get("note"))
        return period_id(competition, season, "game", event_id=r.get("event_id") or fallback)
    start, end = scope.get("start"), scope.get("end")
    if start and end and start[:7] == end[:7]:
        if int(start[-2:]) == 1 and int(end[-2:]) >= 28:
            return period_id(competition, season, "month", start=start)
        return period_id(competition, season, "week", start=start)
    return period_id(competition, season)


def identity_payload(identity, cutoff):
    p = identity_at(identity, cutoff)
    return dict(name=p.get("display_name", p["full_name"]), team=p["team"], jersey=p["jersey"],
        position=" / ".join(p["positions"]), age=p["age"], height=p["height_in_shoes"],
        weight=f'{p["weight_lb"]} lb', shoots=p["shooting_hand"], entry=p["entry"],
        photo_url=p.get("photo_url"), initials="".join(w[0] for w in p.get("display_name", p["full_name"]).split())[:2],
        status=p["roster_status"], cutoff=cutoff)


def award_scope(award):
    """Optional explicit scope plus conservative legacy annual classifications."""
    name = award.get("name", "").casefold()
    explicit = award.get("scope")
    if explicit is not None and explicit not in {"annual", "weekly", "monthly", "event", "career"}:
        raise ValueError("award scope must be annual, weekly, monthly, event or career")
    if re.search(r"\bweek\b", name):
        return "weekly"
    if re.search(r"\bmonth\b", name):
        return "monthly"
    if explicit is not None:
        return explicit
    if award.get("competition") not in {"regular", "playoff"}:
        return "unclassified"
    if "all-star" in name or "all star" in name:
        # A sourced season selection belongs on the user's yearly banner.
        # The exhibition's MVP remains an event unless explicitly classified.
        return "event" if "mvp" in name or "most valuable" in name else "annual"
    annual_names = (r"\b(?:most valuable player|mvp|defensive player of the year|rookie of the year|"
                    r"most improved player|sixth man of the year|sixth player of the year)\b",
                    r"\ball[ -](?:nba|defensive|rookie)\b", r"\bnba champion(?:ship)?\b")
    return "annual" if any(re.search(pattern, name) for pattern in annual_names) else "unclassified"


def earned_annual_awards(awards, season, cutoff):
    return [a for a in awards if a.get("status") == "earned" and a.get("season") == season
            and a.get("awarded_on") and a["awarded_on"] <= cutoff and award_scope(a) == "annual"]


def load_recorded_shots(player, identity, records, clock):
    """Read only declared adjacent shot files for matching closed player boxes.

    Envelope schema: schema_version=1, record_type='recorded_player_shots',
    player_id, event_id, date, season, competition, recorded_on,
    coordinate_system='nba_feet_from_basket', source_type in
    {'recorded_event_feed','recorded_manual_tracking'}, source_label, shots.
    Each shot supplies shot_id, x/y (numeric feet or null), made and value.
    Missing feeds return no coordinates. Invalid or synthetic feeds fail closed.
    """
    shots, sources = [], {}
    for r in records:
        if r.get("status") != "played":
            continue
        if r.get("date", "") > clock:
            raise ValueError("shot source game is after the career cutoff")
        note = Path(r["note"])
        declaration = metadata(note).get("shot_file")
        if not declaration:
            continue
        if r.get("competition") not in NBA_SHOT_COMPETITIONS:
            raise ValueError("this competition requires a separately verified shot geometry adapter")
        path = (note.parent / declaration).resolve()
        if path.parent != note.parent.resolve() or not path.is_relative_to(player.resolve()) or path.suffix != ".json" or not path.is_file():
            raise ValueError("shot_file must identify an existing adjacent JSON file inside the player career")
        raw = json.loads(path.read_text(encoding="utf-8"))
        if raw.get("schema_version") != 1 or raw.get("record_type") != "recorded_player_shots":
            raise ValueError("shot_file requires recorded_player_shots schema version 1; illustrative locations are not live evidence")
        if raw.get("coordinate_system") != "nba_feet_from_basket":
            raise ValueError("shot_file coordinate system is not supported")
        if raw.get("source_type") not in {"recorded_event_feed", "recorded_manual_tracking"} or not isinstance(raw.get("source_label"), str) or not raw["source_label"].strip():
            raise ValueError("shot_file requires recorded source provenance")
        for key, expected in (("player_id", identity["player_id"]), ("event_id", r.get("event_id")),
                              ("date", r["date"]), ("season", r["season"]), ("competition", r["competition"])):
            if expected is None or raw.get(key) != expected:
                raise ValueError(f"shot_file {key} disagrees with the closed player game")
        recorded_on = raw.get("recorded_on")
        if not isinstance(recorded_on, str) or not date.fromisoformat(r["date"]) <= date.fromisoformat(recorded_on) <= date.fromisoformat(clock):
            raise ValueError("shot_file recorded_on must fall between the game date and career cutoff")
        if not isinstance(raw.get("shots"), list):
            raise ValueError("shot_file requires a shots list")
        game_shots = []
        for shot in raw["shots"]:
            if not isinstance(shot, dict):
                raise ValueError("recorded shots must be objects")
            if shot.get("example_only") or shot.get("synthetic") or str(shot.get("source_ref", "")).startswith("example:"):
                raise ValueError("illustrative or synthetic shot records cannot enter a live feed")
            if any(key in shot and shot[key] != value for key, value in (("game_id", r["event_id"]), ("date", r["date"]))):
                raise ValueError("shot record date or event disagrees with its envelope")
            game_shots.append({**shot, "game_id": r["event_id"], "date": r["date"],
                               "source_ref": path.relative_to(player.resolve()).as_posix()})
        # Enforces type, geometry, made/missed buckets, DNP and box reconciliation.
        aggregate_shots([r], game_shots)
        shots.extend(game_shots)
        sources[r["event_id"]] = dict(path=path, label=raw["source_label"], recorded_on=recorded_on)
    ids = [s["shot_id"] for s in shots]
    if len(ids) != len(set(ids)):
        raise ValueError("recorded shot IDs must be unique across source games")
    return shots, sources


def player_cards_data(player, identity, records, awards, clock):
    page = player / "Stats_and_Awards/player_cards.html"
    closed = [r for r in records if r["status"] == "played" and r["date"] <= clock]
    shots, shot_sources = load_recorded_shots(player, identity, closed, clock)
    seasons = sorted({p.name for p in player.iterdir() if p.is_dir() and re.fullmatch(r"\d{4}-\d{2}", p.name)
                      and p.name[:4] + "-06-01" <= clock})
    if not seasons:
        seasons = sorted({r["season"] for r in closed if re.fullmatch(r"\d{4}-\d{2}", r["season"])})
    if not seasons:
        raise ValueError("live player cards require a reached NBA season")
    groups = sorted({(r["competition"], r["season"]) for r in closed} | {("regular", s) for s in seasons},
                    key=lambda item: (item[1], item[0] != "regular", item[0]))
    periods = []

    def append_period(competition, season, kind, start, end, rows, label, event_id=None):
        pid = period_id(competition, season, kind, start if kind != "season" else None, event_id)
        summary = aggregate(rows)
        ids = {r["event_id"] for r in rows}
        current_shots = [s for s in shots if s["game_id"] in ids]
        shooting = aggregate_shots(rows, current_shots)
        competition_label = COMPETITIONS.get(competition, competition)
        if not rows:
            source_note = "No closed games in this competition at the current career checkpoint. No appearance or shot sample is implied."
        elif competition not in NBA_SHOT_COMPETITIONS:
            source_note = "Box scores are available separately. This competition has no verified court-geometry adapter; no NBA shot locations are inferred."
        elif not current_shots:
            source_note = "Only closed box-score evidence is available. No declared recorded shot feed supplies locations; all location statistics remain unavailable where attempts exist."
        else:
            source_note = "Shot locations come only from the declared recorded shot files linked with each closed source game. Partial feeds keep complete-period location rates unavailable."
        source_games = []
        for r in rows:
            item = dict(id=r["event_id"], date=r["date"], opponent=r["opponent"], status=r["status"],
                        appearance=r["appearance"], href=relative(page, r["note"]))
            if r.get("source"):
                item["result_href"] = relative(page, r["source"])
            if r["event_id"] in shot_sources:
                item["shot_href"] = relative(page, shot_sources[r["event_id"]]["path"])
            source_games.append(item)
        periods.append(dict(id=pid, label=label, kind=kind, season=season, competition=competition,
            competition_label=competition_label, start=start, end=end, cutoff=end, games=summary["closed"],
            appearances=summary["gp"], dnp=summary["dnp"], box=summary["totals"], rates=summary["rates"],
            pg=summary["pg"], per36=summary["per36"], source_games=source_games, shots=current_shots, shooting=shooting,
            identity=identity_payload(identity, end), geometry_supported=competition in NBA_SHOT_COMPETITIONS,
            source_note=source_note))

    for competition, season in groups:
        rows = select(closed, competition=competition, season=season)
        if re.fullmatch(r"\d{4}-\d{2}", season):
            start, end = season[:4] + "-06-01", min(clock, f"{int(season[:4]) + 1}-06-30")
        else:
            start, end = min(r["date"] for r in rows), max(r["date"] for r in rows)
        label = f"{season} · {COMPETITIONS.get(competition, competition)} · through {end}"
        append_period(competition, season, "season", start, end, rows, label)
        for month in sorted({r["date"][:7] for r in rows}):
            first = month + "-01"
            last = min(end, f"{month}-{calendar.monthrange(int(month[:4]), int(month[5:]))[1]:02d}")
            month_rows = select(rows, start=first, end=last)
            append_period(competition, season, "month", first, last, month_rows,
                          f"{month} · {COMPETITIONS.get(competition, competition)}")
            for week in sorted({month_week(int(r["date"][-2:])) for r in month_rows}):
                lo = f"{month}-{1 + (week - 1) * 7:02d}"
                hi = min(last, f"{month}-{week * 7:02d}") if week < 4 else last
                week_rows = select(month_rows, start=lo, end=hi)
                append_period(competition, season, "week", lo, hi, week_rows,
                              f"{lo} to {hi} · {COMPETITIONS.get(competition, competition)}")
        for r in rows:
            append_period(competition, season, "game", r["date"], r["date"], [r],
                f'{r["date"]} vs {r["opponent"]} · {r["appearance"]} · {COMPETITIONS.get(competition, competition)}',
                r["event_id"] or Path(r["note"]).relative_to(player).as_posix())
    scenarios = []
    for season in seasons:
        cutoff = clock
        annual = []
        for a in earned_annual_awards(awards, season, cutoff):
            source, _, anchor = a["source"].partition("#")
            annual.append({**a, "scope": "annual", "source_href": relative(page, player / source) + ("#" + anchor if anchor else ""),
                           "source_label": a["source"], "description": "Earned annual recognition from the dated career award record."})
        scenarios.append(dict(id=season, label=season, season=season, cutoff=cutoff, records=annual,
            identity=identity_payload(identity, cutoff),
            notice=f"Only earned annual awards announced on or before {cutoff} appear. Weekly, monthly and unclassified recognition remains in the full award register."))
    default = period_id("regular", seasons[-1])
    return dict(schema_version=1, mode="live", identity=identity_payload(identity, clock), clock=clock,
        notice=f"Career evidence through {clock}. Closed games, recorded locations and earned awards only; no projected results or synthetic shot locations.",
        links=dict(stats="README.md", shooting="Shooting.md", awards="Awards.md",
                   definitions=relative(page, Path(__file__).resolve().parents[1] / "docs/player_statistics.md"),
                   milestones="../Milestones/index.html"),
        geometry=NBA_GEOMETRY, zones=ZONES, default_period=default, periods=periods,
        awards=dict(default_scenario=seasons[-1], scenarios=scenarios))


def navigation_badge(label, subtitle, color):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="620" height="92" viewBox="0 0 620 92" role="img" aria-label="{escape(label)}">
<rect width="620" height="92" rx="12" fill="#141517"/><rect width="8" height="92" rx="4" fill="{color}"/>
<text x="28" y="40" fill="{color}" font-family="sans-serif" font-size="27" font-weight="700">{escape(label)}</text>
<text x="28" y="69" fill="#cbd0d7" font-family="sans-serif" font-size="16">{escape(subtitle)}</text>
<text x="580" y="56" fill="{color}" font-family="sans-serif" font-size="29">›</text></svg>\n'''


def _value(value, percent=False):
    return "N/A" if value is None else f"{value:.1%}" if percent else f"{value:.2f}" if isinstance(value, float) else str(value)


def _table(headers, rows):
    clean = lambda x: str(x).replace("|", "&#124;").replace("\n", " ")
    return "| " + " | ".join(headers) + " |\n| " + " | ".join("---" for _ in headers) + " |\n" + "".join(
        "| " + " | ".join(clean(v) for v in row) + " |\n" for row in rows) + "\n"


def build_player_cards(root, player, identity, records, awards, clock):
    payload = player_cards_data(player, identity, records, awards, clock)
    folder = player / "Stats_and_Awards"
    page = folder / "player_cards.html"
    payload["links"]["definitions"] = relative(page, root / "docs/player_statistics.md")
    template = (Path(__file__).parent / "assets/player_cards.html").read_text(encoding="utf-8")
    if template.count("__PLAYER_CARD_DATA__") != 1:
        raise ValueError("runtime player-card template must contain exactly one data token")
    data_json = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    encoded = json.dumps(payload, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    outputs = {page: template.replace("__PLAYER_CARD_DATA__", encoded), folder / "player_cards_data.json": data_json}
    outputs[folder / "assets/shooting_link.svg"] = navigation_badge("Shooting", "Recorded court locations · full zone statistics · period selector", "#e34e67")
    outputs[folder / "assets/awards_link.svg"] = navigation_badge("Awards", "Earned annual awards · season selector · dated source records", "#efbf58")
    shooting = GENERATED + f'\n# Shooting | {payload["identity"]["name"]}\n\n'
    shooting += f'Career cutoff: **{clock}**. [Open interactive Shooting](player_cards.html#shooting) · [Full statistics](README.md) · [Awards](Awards.md)\n\n'
    shooting += "The detailed court and tables open by default. Missing locations remain unavailable even when a complete box score exists. Field-goal points exclude free throws; rates use every recorded appearance in the selected period. Competitions and seasons stay separate.\n\n"
    for p in payload["periods"]:
        shooting += f'## {p["label"]}\n\n[Open this period](player_cards.html?period={p["id"]}#shooting)\n\n'
        shooting += _table(["Appearances", "DNP", "Closed games", "FGM / FGA", "FG%", "3PM / 3PA", "PTS", "Location coverage"], [[
            _value(p["appearances"]), p["dnp"], p["games"], f'{_value(p["box"]["fgm"])} / {_value(p["box"]["fga"])}',
            _value(p["rates"]["fg_pct"], True), f'{_value(p["box"]["tpm"])} / {_value(p["box"]["tpa"])}',
            _value(p["box"]["pts"]), p["shooting"]["coverage"]["status"]]])
        shooting += p["source_note"] + "\n\n"
        shooting += _table(["Zone", "FGM", "FGA", "FG%", "FG points / game", "FGA / game", "Observed located attempts"], [
            [z["label"], _value(z["fgm"]), _value(z["fga"]), _value(z["fg_pct"], True),
             _value(z["fg_ppg"]), _value(z["fga_per_game"]), z["observed_fga"]] for z in p["shooting"]["zones"]])
        if p["source_games"]:
            shooting += _table(["Date", "Opponent", "Participation", "Closed game", "Player box", "Shot source"], [[
                g["date"], g["opponent"], g["appearance"], f'[Game]({g["href"]})',
                f'[Result]({g["result_href"]})' if g.get("result_href") else "Not available",
                f'[Recorded shots]({g["shot_href"]})' if g.get("shot_href") else "Not recorded"] for g in p["source_games"]])
        else:
            shooting += "No closed source games in this period. Zero appearances do not establish a 0.0% shooting percentage.\n\n"
    outputs[folder / "Shooting.md"] = shooting
    annual_md = GENERATED + f'\n# Annual awards | {payload["identity"]["name"]}\n\n'
    annual_md += f'Career cutoff: **{clock}**. [Open interactive Awards](player_cards.html#awards) · [All earned awards](../Awards.md) · [Full statistics](README.md)\n\n'
    for s in payload["awards"]["scenarios"]:
        annual_md += f'## {s["season"]}\n\n{s["notice"]}\n\n'
        if s["records"]:
            annual_md += _table(["Earned award", "Season", "Announced", "Decision record"], [[
                a["name"], a["season"], a["awarded_on"], f'[Source]({a["source_href"]})'] for a in s["records"]])
            for a in s["records"]:
                token = hashlib.sha256(a["id"].encode()).hexdigest()[:16]
                asset = folder / f"assets/annual_{token}.svg"
                outputs[asset] = navigation_badge(a["name"], f'{s["season"]} · Earned {a["awarded_on"]}', "#efbf58")
                annual_md += f'![{a["name"]}]({relative(folder / "Awards.md", asset)})\n\n'
        else:
            annual_md += "No earned annual awards are recorded by this season's displayed cutoff. Nominations, pending decisions and historical Wade awards are not earned career awards.\n\n"
    outputs[folder / "Awards.md"] = annual_md
    return outputs
