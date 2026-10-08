"""Pages for national-team tournaments, generated from each tournament's record and closed results only.

`career/Dwyane_Wade/FIBA/README.md` lists every edition; `FIBA/<family>/<edition>/README.md` shows the field, the USA
selection, every group table, the bracket, every game, statistical leaders, the final ranking, each medal team's locked
roster from the medal register (`runtime/national_medals.py`) and the tournament honors. Wade's own
national statistics stay on his National_Team pages (`scripts/update_player_reports.py`). Read-only projections:
edit the record (`runtime/national.py`), then rebuild.
"""
from collections import defaultdict
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAGE_LABEL = {"round_of_16": "Round of 16", "quarterfinal": "Quarterfinals", "semifinal": "Semifinals",
               "final": "Final", "third_place": "Third-place game", "fifth_place": "Fifth-place game",
               "seventh_place": "Seventh-place game", "classification_5_8": "Classification 5-8"}


def _table(headers, rows):
    return ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"] + [
        "| " + " | ".join(str(c) for c in r) + " |" for r in rows]


def _stage(stage):
    return STAGE_LABEL.get(stage) or (f"Group {stage.split('_', 1)[1]}" if stage.startswith("group_") else stage.replace("_", " ").title())


def leaders(e, rec, root=ROOT):
    """Per-game leaders over closed games (at least half the team's games)."""
    from .national import results
    lines = defaultdict(lambda: defaultdict(float))
    team_games = defaultdict(int)
    for r in results(e, rec, root).values():
        res = json.loads((Path(root) / r["result"]).read_text(encoding="utf-8"))
        for side in ("home", "away"):
            team_games[res[side]] += 1
            for p in res["player_stats"][side]:
                if p.get("minutes", 0) <= 0:
                    continue
                t = lines[(p["player_id"], res[side])]
                t["g"] += 1
                for k in ("pts", "ast", "stl", "blk"):
                    t[k] += p[k]
                t["reb"] += p["orb"] + p["drb"]
    out = {}
    for k, label in (("pts", "Points"), ("reb", "Rebounds"), ("ast", "Assists"), ("stl", "Steals"), ("blk", "Blocks")):
        rows = [(name, team, v["g"], v[k] / v["g"]) for (name, team), v in lines.items() if v["g"] * 2 >= team_games[team]]
        out[label] = sorted(rows, key=lambda r: (-r[3], r[0]))[:5]
    return out


def page(e, rec, root=ROOT):
    from .national import USA, folder, results, wade_plays
    closed = results(e, rec, root)
    lines = [f"# {e['name']}", "",
             f"{e['first_game']} to {e['last_game']}" + (f", hosted by {e['host']}" if e.get("host") else "") +
             f". FIBA rules (four 10-minute quarters, five fouls). Every game is played by the engine; "
             f"real results of this event are never used. Rules and sources: `runtime/national.py`, `{e['source_file']}`.", ""]
    status = "closed" if rec.get("closed") else f"{len(closed)} of {len(rec['games'])} games played"
    lines += [f"Status: **{status}**.", ""]
    if rec.get("field", {}).get("replaced"):
        lines += ["## The field", "", "Places earned in earlier simulated tournaments (the real qualifier names only the slot):", ""]
        lines += _table(["Real slot", "Simulated qualifier"], sorted(rec["field"]["replaced"].items())) + [""]
    sel = rec.get("selection")
    if sel:
        lines += ["## USA selection", "", f"USA Basketball's committee, {sel['announced_on']} (ability season "
                  f"{sel['ability_season']}). Rule: {sel['rule']['score']}; positional needs {sel['rule']['quotas']}; "
                  f"each invitee's answer is an engine draw (accept {sel['rule']['accept_chance']}); Wade: his standing rule.", ""]
        lines += _table(["Invited", "Club", "Group", "Score", "Answer"],
                        [(i["player"], i["club"], i["group"], i["score"], i["answer"]) for i in sel["invitations"]]) + [""]
        if sel.get("final"):
            lines += ["Final twelve: " + ", ".join(p["player"] for p in sel["final"]) + ".", ""]
    if rec.get("rosters"):
        lines += ["## Rosters", ""]
        for team, r in sorted(rec["rosters"].items()):
            players = ", ".join(f"{p['player']}" + (" (NBA)" if p.get("bbr_id") else "") for p in
                                sorted(r["players"], key=lambda p: -p.get("trust", 0)))
            lines.append(f"- **{team}**" + (f" (coach {r['coach']})" if r.get("coach") else "") + f": {players}")
        lines.append("")
    if rec.get("tables"):
        lines += ["## Groups", ""]
        for group, table in rec["tables"].items():
            carry = (rec.get("groups") or {}).get(group, {}).get("carry_from")
            lines += [f"### Second round (Group {group}, results among teams of the same first-round group carried)" if carry
                      else f"### Group {group}", ""]
            lines += _table(["Pos", "Team", "W", "L", "PF", "PA", "Pts"],
                            [(r["position"] or "=", f"**{r['team']}**" if r["team"] == USA else r["team"], r["w"], r["l"],
                              r["pf"], r["pa"], r["pts"]) for r in table]) + [""]
    lines += ["## Games", ""]
    by_stage = defaultdict(list)
    for g in sorted(rec["games"].values(), key=lambda g: (g["date"], int(g["number"]))):
        by_stage[g["stage"]].append(g)
    for stage, games in by_stage.items():
        rows = []
        for g in games:
            r = closed.get(int(g["number"]))
            home = g.get("home") or g.get("home_slot")
            away = g.get("away") or g.get("away_slot")
            score = f"{r['home_score']}-{r['away_score']}" if r else ""
            link = ""
            if r:
                import os
                here = (Path(root) / folder(e)).resolve()
                link = f"[box]({os.path.relpath((Path(root) / r['result']).resolve(), here)})"
            rows.append((g["number"], g["date"], home, away, score, link))
        lines += [f"### {_stage(stage)}", ""] + _table(["Game", "Date", "Home", "Away", "Score", "Result"], rows) + [""]
    if closed:
        lines += ["## Leaders (per game)", ""]
        for label, rows in leaders(e, rec, root).items():
            lines += [f"**{label}**: " + "; ".join(f"{n} ({t}) {v:.1f}" for n, t, _, v in rows), ""]
    if rec.get("awards"):
        a = rec["awards"]
        lines += ["## Final placings and honors", "",
                  f"Champion **{a['champion']}**, runner-up {a['runner_up']}" + (f", third {a['third']}" if a.get("third") else "") + ".", "",
                  f"Rule: {a['rule']}.", ""]
        lines += medal_lines(e, rec, root)
        lines += ["### Most Valuable Player", "", f"{a['mvp']['player']} ({a['mvp']['team']})" if a.get("mvp") else "None", ""]
        lines += ["### All-Tournament Team", ""] + _table(["Player", "Team", "G", "Game Score", "PTS"],
                                                          [(r["player"], r["team"], r["games"], r["game_score"], r["pts"]) for r in a["all_tournament"]]) + [""]
    if wade_plays(rec):
        lines += [f"Wade's games and statistics: [National_Team/{e['family']}/{e['edition']}](../../../National_Team/{e['family']}/{e['edition']}/).", ""]
    return "<!-- Generated by runtime/national_pages.py; edit the tournament record, then rebuild. -->\n\n" + "\n".join(lines)


def medal_lines(e, rec, root=ROOT):
    """The closed edition's final ranking and, from its medal register, every medal team's locked roster (each player
    receives the medal, minutes played or not). Nothing before the close."""
    import os
    from .national import USA, folder
    from .national_medals import MEDAL_KEYS, build, read
    if not rec.get("closed") or not rec.get("ranking"):
        return []
    lines = ["### Final ranking", ""] + _table(["Place", "Team", "Medal"], [
        (i, f"**{t}**" if t == USA else t, MEDAL_KEYS[i].title() if i in MEDAL_KEYS else "None")
        for i, t in enumerate(rec["ranking"], start=1)]) + [""]
    register = read(e, root) or build(e, rec, root)
    if not register:
        return lines
    here = (Path(root) / folder(e)).resolve()
    rows = []
    for t in register["teams"]:
        players = [m for m in register["medals"] if m["place"] == t["place"]]
        names = ", ".join(m["player"] + ("" if m["games_played"] else " (did not play)") for m in players)
        source, _, anchor = t["source_result"].partition("#")
        target = os.path.relpath((Path(root) / source).resolve(), here)
        decided = f"[{'ranking' if anchor else 'box'}]({target}{'#' + anchor if anchor else ''})"
        rows.append((t["place"], t["medal"].title(), f"**{t['country']}**" if t["country"] == USA else t["country"],
                     len(players), names, decided))
    lines += ["### Medals", "", "Every player on a medal team's locked tournament roster receives the medal, whether or "
              "not he played; a player not on that roster receives none. The MVP and the All-Tournament Team are separate "
              f"performance awards. Register: `{(folder(e) / 'medals.json').as_posix()}` (`runtime/national_medals.py`); "
              f"awarded {register['closed_on']}.", ""]
    lines += _table(["Place", "Medal", "Team", "Players", "Locked roster (each receives the medal)", "Decided by"], rows) + [""]
    return lines


def hub(root=ROOT):
    from .national import editions, folder, read_record
    rows = []
    for e in sorted(editions(root).values(), key=lambda e: e["first_game"]):
        rec = read_record(e, root)
        state = "not started" if rec is None else ("closed: " + rec["awards"]["champion"] if rec.get("closed") else "in progress")
        rows.append((f"[{e['name']}]({e['family']}/{e['edition']}/README.md)" if rec else e["name"], e["first_game"], state))
    return ("<!-- Generated by runtime/national_pages.py. -->\n\n# FIBA tournaments\n\nNational-team tournaments the "
            "simulation plays (USA editions and the qualifiers that fill their fields). The 2004 Olympic tournament "
            "passed before this pipeline existed and has no record.\n\n" + "\n".join(_table(["Tournament", "Starts", "Status"], rows)) + "\n")


def write(e, rec, root=ROOT):
    from .national import WORLD, folder
    path = Path(root) / folder(e) / "README.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(page(e, rec, root), encoding="utf-8")
    (Path(root) / WORLD / "README.md").write_text(hub(root), encoding="utf-8")
