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

Every later draft (R5, October 2026) runs the same way from its own year's files (`library/<year>/league/
nba_<year>_lottery_rules.json` and `nba_<year>_pick_ownership.json`), its season's simulated record and playoff field,
into `career/Dwyane_Wade/<season>/09_Draft/draft_order_<year>.json`: every non-playoff club enters the lottery unless
the ownership file fixes an expansion slot, a club the rules file makes ineligible for a pick (`ineligible`:
{code: [picks]}) is left out of that pick's draw, and forfeited picks are skipped.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIAMI, MIA = "Miami Heat", "MIA"


class Year:
    """A draft year's files, folders and dates."""

    def __init__(self, year=2004, root=ROOT):
        from .seasons import dates
        self.year = int(year)
        self.season = f"{self.year - 1}-{str(self.year)[-2:]}"
        self.next_season = f"{self.year}-{str(self.year + 1)[-2:]}"
        lib = Path(f"library/{self.year}/league")
        self.rules_path = lib / f"nba_{self.year}_lottery_rules.json"
        self.ownership_path = lib / f"nba_{self.year}_pick_ownership.json"
        self.rosters_path = lib / f"nba_{self.year}_{str(self.year + 1)[-2:]}_team_rosters.json"
        self.folder = Path(f"career/Dwyane_Wade/{self.season}/09_Draft")
        self.record = self.folder / f"draft_order_{self.year}.json"
        self.draws = self.folder / "Lottery_Draws"
        rules = _read(Path(root) / self.rules_path) if (Path(root) / self.rules_path).is_file() else {}
        self.lottery_date = rules.get("lottery_date")
        self.season_end = dates(self.season, root)["regular_season_end"]


# The 2004 names other modules and records use.
SEASON = "2003-04"
RULES = Path("library/2004/league/nba_2004_lottery_rules.json")
OWNERSHIP = Path("library/2004/league/nba_2004_pick_ownership.json")
ROSTERS = Path("library/2004/league/nba_2004_05_team_rosters.json")
FOLDER = Path(f"career/Dwyane_Wade/{SEASON}/09_Draft")
RECORD = FOLDER / "draft_order_2004.json"
DRAWS = FOLDER / "Lottery_Draws"
LOTTERY_DATE = "2004-05-26"
SEASON_END = "2004-04-14"


def _read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def protected(entry, year, pick):
    """Whether a traded first-round pick is protected at this slot in this year (`protection` in the ownership file:
    "lottery-protected" = picks 1-14, "protected 1-N"); anything else conveys. Protections only; a later real move
    that changed one is not applied (ownership is fixed at the December 3, 2003 activation)."""
    import re
    terms = (entry.get("protection") or {}).get(str(year))
    if not terms:
        return False
    if terms.startswith("lottery-protected"):
        return pick <= 14
    m = re.match(r"protected 1-(\d+)", terms)
    return bool(m) and pick <= int(m.group(1))


def codes(root=ROOT, y=None):
    """{club: code} from the next season's rosters, with a renamed club also under its old name (the closed season's
    standings use it: `seasons.club_aliases`)."""
    from .seasons import club_aliases
    out = {club: v["code"] for club, v in _read(Path(root) / (y.rosters_path if y else ROSTERS))["clubs"].items()}
    out[MIAMI] = MIA
    if y is not None:
        for old, new in club_aliases(y.next_season).items():
            if new in out:
                out.setdefault(old, out[new])
    return out


def records(root=ROOT, y=None):
    from .standings import standings_on
    return standings_on(y.season_end if y else SEASON_END, root, y.season if y else SEASON)


def playoff_clubs(root=ROOT, y=None):
    from .playoffs import read
    record = read(root, y.season if y else SEASON)
    return {row["club"] for conf in ("East", "West") for row in record["seeds"][conf]}


def _packet(event_id, question, options, basis, date=LOTTERY_DATE):
    total = sum(options.values())
    probs = {k: round(v / total, 6) for k, v in options.items()}
    top = max(probs, key=probs.get)
    probs[top] = round(probs[top] + 1 - sum(probs.values()), 6)      # rounding drift on the largest option
    return {"event_id": event_id, "date": date, "question": question, "decider": "NBA draft lottery (engine draw)",
            "options": probs, "basis": basis}


def _draw(root, packet, y=None):
    """The drawn outcome, or None after writing the packet for the engine."""
    root = Path(root)
    path = root / (y.draws if y else DRAWS) / f"{packet['event_id']}.decision.json"
    result = path.with_name(path.name.replace(".decision.json", ".decision.result.json"))
    if result.is_file():
        return _read(result)["outcome"]
    if not path.is_file():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(packet, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return None


def order_by_record(clubs, table, root, label, worst_first=True, y=None):
    """Clubs ordered by winning percentage (worst first); exact ties ordered by an engine drawing. None while waiting."""
    year = y.year if y else 2004
    date = (y.lottery_date if y else LOTTERY_DATE)
    groups = {}
    for c in clubs:
        groups.setdefault(table[c]["pct"], []).append(c)
    out = []
    for pct in sorted(groups, reverse=not worst_first):
        tied = sorted(groups[pct])
        while len(tied) > 1:
            first = _draw(root, _packet(f"{year}-draft-{label}-tie-{'-'.join(codes(root, y)[c].lower() for c in tied)}",
                                        f"{year} draft order ({label}): which of " + ", ".join(tied) + f" (tied at {pct:.3f}) goes first?",
                                        {c: 1 for c in tied}, "Equal simulated records; ordered by a drawing (runtime/lottery.py).",
                                        date), y)
            if first is None:
                return None
            out.append(first)
            tied.remove(first)
        out += tied
    return out


def miami_pick_trades(root, season, year, code):
    """Miami's own picks of this draft that simulated Miami traded, as {(round, "MIA"): owner code}. The ownership file
    is fixed at the December 3, 2003 activation and never sees a simulated trade; Miami's pick ledger
    (`00_Team/Finances/draft_picks.json`, appended by the trade write-back) does. The last recorded holder owns it."""
    path = Path(root) / f"career/Dwyane_Wade/{season}/00_Team/Finances/draft_picks.json"
    if not path.is_file():
        return {}
    out = {}
    for p in _read(path).get("picks", []):
        moves = [h for h in p.get("history", []) if h.get("to")]
        if int(p["year"]) != int(year) or p.get("owned", True) or not moves:
            continue
        holder = moves[-1]["to"]
        out[(int(p["round"]), code[p["original_club"]])] = code.get(holder, holder)
    return out


def build(root=ROOT, year=2004):
    """The draft order record, or None while an engine draw is pending."""
    root = Path(root)
    y = None if int(year) == 2004 else Year(year, root)
    rules, own = _read(root / (y.rules_path if y else RULES)), _read(root / (y.ownership_path if y else OWNERSHIP))
    table, playoff, code = records(root, y), playoff_clubs(root, y), codes(root, y)
    year = int(year)
    date = y.lottery_date if y else LOTTERY_DATE
    clubs = sorted(table)
    lottery = [c for c in clubs if c not in playoff]
    seeds = order_by_record(lottery, table, root, "lottery-seeding", y=y)
    if seeds is None:
        return None
    combos = rules["combinations_by_seed"]
    chances = {}
    for c in seeds:                                    # tied clubs split their seeds' combinations evenly; the
        tied = [x for x in seeds if table[x]["pct"] == table[c]["pct"]]          # drawing order takes any remainder
        idx = [seeds.index(x) for x in tied]
        total = sum(combos[i] for i in idx)
        chances[c] = total // len(tied) + (1 if tied.index(c) < total % len(tied) else 0)
    ineligible = rules.get("ineligible", {})
    winners = []
    for n in range(1, rules["picks_drawn"] + 1):
        left = {c: w for c, w in chances.items() if c not in winners and n not in ineligible.get(code[c], [])}
        won = _draw(root, _packet(f"{year}-draft-lottery-pick-{n}", f"{year} NBA draft lottery: which club wins pick No. {n}?",
                                  left, f"Lottery combinations by simulated record ({(y.rules_path if y else RULES).as_posix()}); "
                                  "clubs already drawn or ineligible for this pick removed.", date), y)
        if won is None:
            return None
        winners.append(won)
    rest = [c for c in seeds if c not in winners]
    expansion = (own.get("expansion") or {}).get("club")
    from .seasons import club_aliases
    renamed = set(club_aliases(y.next_season)) if y is not None else set()
    names = {v: k for k, v in code.items() if k not in renamed}          # a code names the club as it is now called
    first_round = winners + rest
    if expansion and own["expansion"].get("round_1_slot"):
        first_round.insert(own["expansion"]["round_1_slot"] - 1, "__EXP__")     # an expansion club's fixed slot
        names[expansion] = own["expansion"].get("name", "Charlotte Bobcats")
    playoffs_order = order_by_record(sorted(playoff), table, root, "playoff-clubs", y=y)
    if playoffs_order is None:
        return None
    forfeit = set((own.get("forfeited") or {}).get("round_1", []))
    first_round += [c for c in playoffs_order if code[c] not in forfeit]
    # Second round: reverse order of record for every club, tied clubs in the opposite order to round one.
    round_one_rank = {c: i for i, c in enumerate(seeds + playoffs_order)}
    second = sorted(clubs, key=lambda c: (table[c]["pct"], -round_one_rank[c]))
    forfeit_2 = set((own.get("forfeited") or {}).get("round_2", []))
    second = [c for c in second if code[c] not in forfeit_2]
    if expansion and own["expansion"].get("round_2_slot"):
        second.insert(own["expansion"]["round_2_slot"] - len(first_round) - 1, "__EXP__")
    miami_traded = miami_pick_trades(root, y.season if y else SEASON, year, code)
    slots = []
    for rnd, seq, owners in ((1, first_round, own["round_1"]), (2, second, own["round_2"])):
        for club in seq:
            original = expansion if club == "__EXP__" else code[club]
            owner = owners.get(original, {}).get("owner", original)
            if protected(owners.get(original, {}), year, len(slots) + 1):
                owner = original                       # a protected pick stays with its club this year
            owner = miami_traded.get((rnd, original), owner)    # a simulated Miami trade of the pick wins
            slots.append({"pick": len(slots) + 1, "round": rnd, "original": original, "owner": owner,
                          "owner_club": names.get(owner, owner)})
    return {"schema_version": 1, "kind": "draft_order", "draft": f"{year} NBA Draft", "lottery_date": date,
            "rule": __doc__.split("\n\n", 1)[1].strip(), "lottery_seeds": [{"seed": i + 1, "club": c, "record":
            f"{table[c]['wins']}-{table[c]['losses']}", "combinations": chances[c]} for i, c in enumerate(seeds)],
            "lottery_winners": winners, "picks": slots}


def run(root=ROOT, clock=None, year=2004):
    """On or after the lottery date: write the order once every draw is in. Returns the record or None."""
    from .write_back import clock as career_clock
    root = Path(root)
    y = None if int(year) == 2004 else Year(year, root)
    date, record_path = (y.lottery_date, y.record) if y else (LOTTERY_DATE, RECORD)
    if not date or (clock or career_clock(root)) < date or (root / record_path).is_file():
        return None
    record = build(root, year)
    if record:
        (root / record_path).parent.mkdir(parents=True, exist_ok=True)
        (root / record_path).write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return record
