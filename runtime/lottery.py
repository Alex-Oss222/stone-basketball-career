"""The 2004 draft lottery and draft order from the simulated league (the user's decision, October 2026).

On the lottery date the 13 clubs that missed the simulated playoffs are seeded by their simulated records (worst
first); an exact tie in record is ordered by an engine drawing. Picks 1 to 3 are three engine draws, each weighted by
the lottery combinations of the clubs not yet drawn (tied clubs split their seeds' combinations; a drawing orders
them and takes any remainder) (`library/2004/league/nba_2004_lottery_rules.json`). Charlotte,
the expansion club, holds No. 4 in each round and is not in the lottery. The other lottery clubs take picks 5 to 14
in seed order; the playoff clubs take the rest of the first round by record, worst first (Minnesota's first-round pick
is forfeited by a pre-career sanction); the second round runs in reverse record of all 29 clubs, Charlotte at No. 33.
Every chance answer is an engine draw, journaled and never re-rolled. Pick ownership follows
`library/2004/league/nba_2004_pick_ownership.json`. The result is `09_Draft/draft_order_2004.json`.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEASON = "2003-04"
RULES = Path("library/2004/league/nba_2004_lottery_rules.json")
OWNERSHIP = Path("library/2004/league/nba_2004_pick_ownership.json")
ROSTERS = Path("library/2004/league/nba_2004_05_team_rosters.json")
FOLDER = Path(f"career/Dwyane_Wade/{SEASON}/09_Draft")
RECORD = FOLDER / "draft_order_2004.json"
DRAWS = FOLDER / "Lottery_Draws"
LOTTERY_DATE = "2004-05-26"
SEASON_END = "2004-04-14"
MIAMI, MIA = "Miami Heat", "MIA"


def _read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def codes(root=ROOT):
    out = {club: v["code"] for club, v in _read(Path(root) / ROSTERS)["clubs"].items()}
    out[MIAMI] = MIA
    return out


def records(root=ROOT):
    from .standings import standings_on
    return standings_on(SEASON_END, root, SEASON)


def playoff_clubs(root=ROOT):
    from .playoffs import read
    record = read(root)
    return {row["club"] for conf in ("East", "West") for row in record["seeds"][conf]}


def _packet(event_id, question, options, basis, date=LOTTERY_DATE):
    total = sum(options.values())
    probs = {k: round(v / total, 6) for k, v in options.items()}
    top = max(probs, key=probs.get)
    probs[top] = round(probs[top] + 1 - sum(probs.values()), 6)      # rounding drift on the largest option
    return {"event_id": event_id, "date": date, "question": question, "decider": "NBA draft lottery (engine draw)",
            "options": probs, "basis": basis}


def _draw(root, packet):
    """The drawn outcome, or None after writing the packet for the engine."""
    root = Path(root)
    path = root / DRAWS / f"{packet['event_id']}.decision.json"
    result = path.with_name(path.name.replace(".decision.json", ".decision.result.json"))
    if result.is_file():
        return _read(result)["outcome"]
    if not path.is_file():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(packet, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return None


def order_by_record(clubs, table, root, label, worst_first=True):
    """Clubs ordered by winning percentage (worst first); exact ties ordered by an engine drawing. None while waiting."""
    groups = {}
    for c in clubs:
        groups.setdefault(table[c]["pct"], []).append(c)
    out = []
    for pct in sorted(groups, reverse=not worst_first):
        tied = sorted(groups[pct])
        while len(tied) > 1:
            first = _draw(root, _packet(f"2004-draft-{label}-tie-{'-'.join(codes(root)[c].lower() for c in tied)}",
                                        f"2004 draft order ({label}): which of " + ", ".join(tied) + f" (tied at {pct:.3f}) goes first?",
                                        {c: 1 for c in tied}, "Equal simulated records; ordered by a drawing (runtime/lottery.py)."))
            if first is None:
                return None
            out.append(first)
            tied.remove(first)
        out += tied
    return out


def build(root=ROOT):
    """The draft order record, or None while an engine draw is pending."""
    root = Path(root)
    rules, own = _read(root / RULES), _read(root / OWNERSHIP)
    table, playoff, code = records(root), playoff_clubs(root), codes(root)
    clubs = sorted(table)
    lottery = [c for c in clubs if c not in playoff]
    seeds = order_by_record(lottery, table, root, "lottery-seeding")
    if seeds is None:
        return None
    combos = rules["combinations_by_seed"]
    chances = {}
    for c in seeds:                                    # tied clubs split their seeds' combinations evenly; the
        tied = [x for x in seeds if table[x]["pct"] == table[c]["pct"]]          # drawing order takes any remainder
        idx = [seeds.index(x) for x in tied]
        total = sum(combos[i] for i in idx)
        chances[c] = total // len(tied) + (1 if tied.index(c) < total % len(tied) else 0)
    winners = []
    for n in range(1, rules["picks_drawn"] + 1):
        left = {c: w for c, w in chances.items() if c not in winners}
        won = _draw(root, _packet(f"2004-draft-lottery-pick-{n}", f"2004 NBA draft lottery: which club wins pick No. {n}?",
                                  left, f"Lottery combinations by simulated record ({RULES.as_posix()}); clubs already drawn removed."))
        if won is None:
            return None
        winners.append(won)
    rest = [c for c in seeds if c not in winners]
    expansion = own["expansion"]["club"]
    first_round = winners + rest
    first_round.insert(own["expansion"]["round_1_slot"] - 1, "__CHA__")     # Charlotte's fixed No. 4
    playoffs_order = order_by_record(sorted(playoff), table, root, "playoff-clubs")
    if playoffs_order is None:
        return None
    forfeit = set(own["forfeited"]["round_1"])
    names = {v: k for k, v in code.items()}
    names[expansion] = "Charlotte Bobcats"
    first_round += [c for c in playoffs_order if code[c] not in forfeit]
    # Second round: reverse order of record for all 29 clubs, tied clubs in the opposite order to round one.
    round_one_rank = {c: i for i, c in enumerate(seeds + playoffs_order)}
    second = sorted(clubs, key=lambda c: (table[c]["pct"], -round_one_rank[c]))
    second.insert(own["expansion"]["round_2_slot"] - len(first_round) - 1, "__CHA__")
    slots = []
    for rnd, seq, owners in ((1, first_round, own["round_1"]), (2, second, own["round_2"])):
        for club in seq:
            original = expansion if club == "__CHA__" else code[club]
            owner = owners.get(original, {}).get("owner", original)
            slots.append({"pick": len(slots) + 1, "round": rnd, "original": original, "owner": owner,
                          "owner_club": names.get(owner, owner)})
    return {"schema_version": 1, "kind": "draft_order", "draft": "2004 NBA Draft", "lottery_date": LOTTERY_DATE,
            "rule": __doc__.split("\n\n", 1)[1].strip(), "lottery_seeds": [{"seed": i + 1, "club": c, "record":
            f"{table[c]['wins']}-{table[c]['losses']}", "combinations": chances[c]} for i, c in enumerate(seeds)],
            "lottery_winners": winners, "picks": slots}


def run(root=ROOT, clock=None):
    """On or after the lottery date: write the order once every draw is in. Returns the record or None."""
    from .write_back import clock as career_clock
    root = Path(root)
    if (clock or career_clock(root)) < LOTTERY_DATE or (root / RECORD).is_file():
        return None
    record = build(root)
    if record:
        (root / RECORD).parent.mkdir(parents=True, exist_ok=True)
        (root / RECORD).write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return record
