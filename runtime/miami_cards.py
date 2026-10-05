"""Keep Miami's personnel cards current with the season (Player_Cards/*.md).

The cards were written at the June 26, 2003 import. Through the season this refresh rewrites only the dated,
record-owned parts of each card on Miami's register, from the owning records:
- **Role** and "Not yet established": the latest dated rotation (camp `Depth_Chart/rotation.json`, then each
  `Depth_Chart/Reviews/<date>/rotation.json`) and the injured list (`Transactions/injured_list.json`);
- the header's "Statistics through" date and the 2003-04 row of the regular-season table: closed results
  (`write_back.miami_lines`), the same evidence as the Team pages;
- the coverage sentence, and one "Changes and coaching notes" row per rotation review that set his role.
Grades, scouting text, sources and the history of earlier rows are never touched. A player no longer on the
register keeps his card as it stood.
"""
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def _season(root=None):
    from .seasons import active
    return active(root or ROOT)


def team_dir(season):
    return Path(f"career/Dwyane_Wade/{season}/00_Team/Team")
GONE = ("released", "traded", "signed_elsewhere", "voided", "waived", "renounced", "declined")


def _read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def rotations(root, season=None):
    """[(date, rotation dict, relative source)] oldest first: the camp rotation, then each review's."""
    from .seasons import dates
    root = Path(root)
    season = season or _season(root)
    TEAM = team_dir(season)
    out = []
    camp = root / TEAM / "Depth_Chart/rotation.json"
    if camp.is_file():
        data = _read(camp)
        out.append((data.get("as_of", dates(season, root)["roster_cut"]), data, "../Depth_Chart/rotation.json"))
    for path in sorted((root / TEAM / "Depth_Chart/Reviews").glob("*/rotation.json")):
        data = _read(path)
        out.append((data.get("as_of", path.parent.name), data, f"../Depth_Chart/Reviews/{path.parent.name}/rotation.json"))
    return sorted(out, key=lambda r: r[0])


def role_in(rotation, name):
    starters = {v: k for k, v in (rotation.get("starters") or {}).items()}
    row = next((p for p in rotation.get("players", []) if p["player_id"] == name), None)
    if name in starters:
        return f"starter at {starters[name]}, staff plan {row['minutes']:.0f} minutes" if row else f"starter at {starters[name]}"
    if row and row.get("minutes"):
        return f"rotation at {row.get('position', 'N/A')}, staff plan {row['minutes']:.0f} minutes"
    return "reserve outside the planned rotation"


def injured_on(root, name, on, season=None):
    season = season or _season(root)
    ledger = Path(root) / f"career/Dwyane_Wade/{season}/00_Team/Transactions/injured_list.json"
    if not ledger.is_file():
        return None
    for e in _read(ledger)["entries"]:
        if e["player"] == name and e["placed"] <= on and (e["activated"] is None or e["activated"] > on):
            return e
    return None


def _pct(made, att):
    return f"{100 * made / att:.1f}%" if att else "N/A"


def season_row(records, season):
    played = [r for r in records if r.get("line") and r["line"].get("appeared")]
    g = len(played)
    if not g:
        return None
    t = lambda k: sum(r["line"].get(k) or 0 for r in played)
    gs = sum(1 for r in played if r["line"].get("started"))
    per = lambda k: f"{t(k) / g:.1f}"
    return [season, "MIA", str(g), str(gs), f"{t('seconds') / 60 / g:.1f}", per("pts"), per("reb"), per("ast"), per("stl"),
            per("blk"), per("tov"), _pct(t("fgm"), t("fga")), _pct(t("tpm"), t("tpa")), _pct(t("ftm"), t("fta"))]


def refresh(root=ROOT, write=True):
    """Refresh every register player's card. Returns the changed card paths."""
    root = Path(root)
    from .write_back import clock, miami_lines
    now = clock(root)
    season = _season(root)
    TEAM = team_dir(season)
    roster = _read(root / TEAM / "Roster/roster.json")
    lines, games = miami_lines(root, season, now)
    rots = rotations(root, season)
    changed = []
    for p in roster["players"]:
        if any(w in (p.get("status") or "") for w in GONE):
            continue
        card = root / TEAM / "Player_Cards" / Path(p.get("player_card", "")).name
        if not card.is_file():
            continue
        name = p["name"]
        text = card.read_text(encoding="utf-8")
        new = text
        latest = [r for r in rots if r[0] <= now]
        if latest:
            day, rot, src = latest[-1]
            role = role_in(rot, name)
            hurt = injured_on(root, name, now)
            extra = (f" On the injured list since {hurt['placed']} ({hurt['reason']})." if hurt else "")
            new = re.sub(r"^\*\*Role:\*\*.*$",
                         f"**Role:** {role[0].upper() + role[1:]} (staff rotation dated {day}, [record]({src})).{extra}",
                         new, count=1, flags=re.M)
            new = re.sub(r"^- \*\*Not yet established:\*\*.*$",
                         f"- **Not yet established:** closing role and Miami staff grades beyond the camp review. "
                         f"Rotation role and minute target: staff rotation dated {day}.", new, count=1, flags=re.M)
            # One dated note per staff rotation that set his role (idempotent: a date already noted is skipped).
            for rday, rrot, rsrc in latest:
                marker = f"Staff rotation of {rday}"
                if marker in new or "## Changes and coaching notes" not in new:
                    continue
                note = f"| {rday} | {marker}: {role_in(rrot, name)}. | [Rotation]({rsrc}) |"
                new = re.sub(r"(## Changes and coaching notes\n\n\| Date \|[^\n]*\n\| ---[^\n]*\n(?:\|[^\n]*\n)*)",
                             lambda m: m.group(1) + note + "\n", new, count=1)
        new = re.sub(r"\*\*Statistics through:\*\* [^\n·]*", f"**Statistics through:** {now} ", new, count=1)
        row = season_row(lines.get(name, []), season)
        cells = row or [season, "Miami Heat", "0"] + ["N/A"] * 11
        line = "| " + " | ".join(cells) + " |"
        if re.search(rf"^\| {season} \|", new, flags=re.M):
            new = re.sub(rf"^\| {season} \|[^\n]*$", line, new, count=1, flags=re.M)
        else:                                                         # a new season's row goes after the last one
            new = re.sub(r"(## Regular-season statistics by year\n(?:(?!\n## )[\s\S])*?\| Season \|[^\n]*\n\| ---[^\n]*\n(?:\|[^\n]*\n)*)",
                         lambda m: m.group(1) + line + "\n", new, count=1)
        tail = (f"{season}: {row[2]} closed Miami game(s) through {now}." if row else
                f"{season}: no Miami appearance through {now}.")
        # The generated coverage line only: the 2003 import's wording, or "Closed Miami results" on later cards.
        cov = re.search(r"^\*\*Coverage:\*\* (?:2002-03 regular season imported\.|Closed Miami results)[^\n]*$", new, flags=re.M)
        if cov:
            text_cov = cov.group(0)
            if f"; {season}:" in text_cov:
                updated = text_cov[:text_cov.index(f"; {season}:")] + "; " + tail
            else:
                updated = text_cov.rstrip(".") + "; " + tail if text_cov.endswith(".") else text_cov + "; " + tail
            new = new[:cov.start()] + updated + new[cov.end():]
        if new != text:
            changed.append(card)
            if write:
                card.write_text(new, encoding="utf-8")
    return changed
