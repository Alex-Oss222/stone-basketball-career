"""The 2004 NBA Draft for every club (roadmap 17; the user's design and decisions, October 2026).

Every club drafts for itself on June 24, 2004, in the order the simulated lottery and records set
(`runtime/lottery.py`). Each pick and each draft-night trade is an engine decision draw: journaled once, never
re-rolled, and nothing is decided before the draft date. Real 2004 picks are never consulted.

Evidence (draft-night only): eight pre-draft boards and mocks (`nba_2004_predraft_boards.json`, five user-supplied
boards; `nba_2004_prospect_evidence.json`, three dated mocks) and each prospect's last pre-draft season and age.
Medical, work-ethic and basketball-IQ grades are not in any sourced record for this class, so they are neutral
(1.0); nothing is invented.

1. Board and translation. Consensus slot = the mean of the eight sources (a first-round-only board that omits a
   player counts him 31st; a two-round mock, 61st). Median value = MEDIAN_TOP x exp(-MEDIAN_DECAY x (consensus - 1)),
   moved by the translated college line: shooting = 0.55 FT% + 0.30 3P% + 0.15 three-point volume, defence = steals
   and blocks per 40 minutes, each as a z-score within the class (SHOOT_WEIGHT, DEF_WEIGHT of the median).
2. Outcome distribution. Spread = SPREAD_BASE x median x (1 + (23 - age) / 4): floor = median - 1.0 spread (not
   below FLOOR_MIN), ceiling = median + 1.6 spread. Younger prospects get wider, higher ceilings.
3. Risk. Medical and intangible multipliers are 1.0 (no sourced grades).
4. Club utility. Timeline weights by the club's simulated 2003-04 record (50+ wins contending, 30 or fewer
   rebuilding, else middle): contending 0.50/0.35/0.15 (floor/median/ceiling), middle 0.30/0.45/0.25, rebuilding
   0.10/0.30/0.60. Fit over three seasons: the share of the position group's minutes (G 96, F 96, C 48 a game) not
   covered by players under contract, from their simulated 2003-04 minutes, weighted 0.5/0.3/0.2 for 2004-05 to
   2006-07 (x1.15 for the club's largest need at half or more, x1.05 at 30%+, x0.90 at 5% or less); a cornerstone at
   that position under contract two more seasons (simulated Game Score 16+ a game) costs x0.75, or x0.88 for a
   prospect with a second position.
5. Tiers and the pick. The board (0.6 median + 0.4 ceiling) is cut into tiers: a new tier starts where the score falls
   TIER_BREAK below the tier's first player. A
   club takes from the best tier still available (cross-tier dominance); within it, its top three by utility are
   offered to the engine with probabilities proportional to exp(utility / TEMPERATURE).
6. Trades. Trade down: with three or more players left in the club's top tier, the next club within six slots whose
   best player is in that tier and worth TRADE_UP_GAIN more to it than what it expects at its own slot offers its pick
   plus its 2005 second-rounder; the trade must hold up on the pick-value chart (`trades.TOP_PICK_VALUE`, PICK_DECAY);
   the on-clock club's answer is an engine draw (TRADE_DOWN_ACCEPT). At most MAX_TRADES a draft.

Drafted players' rights go to the drafting club (first-rounders sign rookie-scale contracts with the club's free
agency); a real prospect nobody drafts is an undrafted free agent and enters the summer market.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parents[1]
SEASON = "2003-04"
DRAFT_DATE = "2004-06-24"
BOARDS = Path("library/2004/league/nba_2004_predraft_boards.json")
EVIDENCE = Path("library/2004/league/nba_2004_prospect_evidence.json")
FOLDER = Path(f"career/Dwyane_Wade/{SEASON}/09_Draft")
RECORD = FOLDER / "draft_2004.json"
DRAWS = FOLDER / "Draft_Draws"
MIAMI = "Miami Heat"
MEDIAN_TOP, MEDIAN_DECAY = 3.5, 0.05
SHOOT_WEIGHT, DEF_WEIGHT = 0.10, 0.08
SPREAD_BASE, FLOOR_MIN = 0.45, -1.0
TIER_BREAK = 0.25                     # a new tier where the board score falls 25% below the tier's first player
TEMPERATURE = 0.12
TIMELINE = {"contending": (0.50, 0.35, 0.15), "middle": (0.30, 0.45, 0.25), "rebuilding": (0.10, 0.30, 0.60)}
CONTENDING_WINS, REBUILDING_WINS = 50, 30
CORNERSTONE_GMSC = 16.0
TRADE_UP_GAIN, TRADE_DOWN_ACCEPT, MAX_TRADES, TRADE_WINDOW = 1.15, 0.5, 6, 6
GROUP = {"PG": "G", "SG": "G", "G": "G", "SF": "F", "PF": "F", "F": "F", "C": "C"}
TARGET_MINUTES = {"G": 96, "F": 96, "C": 48}
RESEARCH_MOCKS = {"vitale_espn_2004_06_22": 31, "hrr_2004_06_24": 31, "nbadraft_net_2004_mock": 61}
YEAR, SEASON_END = 2004, "2004-04-14"


def _seasons_ahead(n=3):
    return [f"{YEAR + i}-{str(YEAR + i + 1)[-2:]}" for i in range(n)]


class year_context:
    """Run the module for a later draft (R5, October 2026): its season, date, files, folder and the evidence's own mock
    list (`research_mocks` in the evidence file: {key: rank given to an unlisted player}). 2004 keeps its constants."""

    NAMES = ("YEAR", "SEASON", "DRAFT_DATE", "BOARDS", "EVIDENCE", "FOLDER", "RECORD", "DRAWS", "RESEARCH_MOCKS", "SEASON_END")

    def __init__(self, year, root=ROOT):
        self.year, self.root = int(year), Path(root)

    def __enter__(self):
        g = globals()
        self.saved = {k: g[k] for k in self.NAMES}
        if self.year == 2004:
            return self
        from .seasons import dates
        y = self.year
        season = f"{y - 1}-{str(y)[-2:]}"
        lib = Path(f"library/{y}/league")
        calendar = _read(self.root / lib / f"nba_{y}_offseason_calendar.json")
        evidence = _read(self.root / lib / f"nba_{y}_prospect_evidence.json")
        g.update(YEAR=y, SEASON=season, DRAFT_DATE=_calendar_date(calendar, "draft"),
                 BOARDS=lib / f"nba_{y}_predraft_boards.json", EVIDENCE=lib / f"nba_{y}_prospect_evidence.json",
                 FOLDER=Path(f"career/Dwyane_Wade/{season}/09_Draft"),
                 RESEARCH_MOCKS=evidence.get("research_mocks", {}),
                 SEASON_END=dates(season, self.root)["regular_season_end"])
        g["RECORD"] = g["FOLDER"] / f"draft_{y}.json"
        g["DRAWS"] = g["FOLDER"] / "Draft_Draws"
        return self

    def __exit__(self, *exc):
        globals().update(self.saved)
        return False


def _calendar_date(calendar, key):
    """A dated event from an offseason calendar file: the value of `key` or `<key>_date`, plain or {"value": ...}."""
    for k in (key, f"{key}_date", f"{key}_day"):
        v = calendar.get(k)
        if isinstance(v, dict):
            v = v.get("value") or v.get("date")
        if isinstance(v, str) and len(v) >= 10:
            return v[:10]
    for e in calendar.get("events", []):
        if e.get("id") in (key, f"{key}_date"):
            return e.get("date")
    raise KeyError(f"no {key} date in the offseason calendar")


def _read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _key(name):
    from .player_stats import alias
    return alias(name)


# -- 1-3: the board ------------------------------------------------------------------------------------------
def prospects(root=ROOT):
    """{key: prospect} with consensus slot, translated college line, age, position group and value distribution."""
    root = Path(root)
    ev = _read(root / EVIDENCE)
    boards = _read(root / BOARDS)["boards"]
    rows = ev["players_drafted"] + ev["undrafted_candidates"]["players"]
    out = {}
    for p in rows:
        pos = p.get("position")
        pos = (pos.get("value") if isinstance(pos, dict) else pos) or "F"
        r = p.get("pre_draft_rankings") or {}
        ranks = [r[k] if isinstance(r.get(k), (int, float)) else miss for k, miss in RESEARCH_MOCKS.items()]
        for board in boards.values():
            ranks.append(board["rank_by_player"].get(_board_name(board, p), 31))
        stats = (p.get("last_pre_draft_season") or {}).get("stats") if isinstance(p.get("last_pre_draft_season"), dict) else None
        stats = stats or (p.get("last_pre_draft_season") if (p.get("last_pre_draft_season") or {}).get("games") else None)
        out[_key(p["player_id"])] = {"player": p["player_id"], "bbr_id": p.get("bbr_id"), "position": pos,
                                     "group": GROUP.get(pos.split("/")[0], "F"), "second_position": "/" in pos,
                                     "age": p.get("age_on_draft_day") or 21, "consensus": round(statistics.mean(ranks), 2),
                                     "stats": stats}
    _translate(out)
    return out


def _board_name(board, p):
    names = {_key(n): n for n in board["rank_by_player"]}
    for candidate in (p["player_id"], p.get("full_name") or ""):
        if _key(candidate) in names:
            return names[_key(candidate)]
    return None


def _per40(s, key):
    return s[key] / s["minutes"] * 40 if s and s.get("minutes") else None


def _translate(pool):
    shoot, defence = {}, {}
    for k, p in pool.items():
        s = p["stats"]
        if s and s.get("free_throws_attempted") and s.get("field_goals_attempted"):
            ft = s["free_throws_made"] / s["free_throws_attempted"]
            tp = (s["three_pointers_made"] / s["three_pointers_attempted"]) if s.get("three_pointers_attempted") else 0.0
            volume = min(1.0, s.get("three_pointers_attempted", 0) / max(1, s["games"]) / 5)
            shoot[k] = 0.55 * ft + 0.30 * tp + 0.15 * volume
            defence[k] = (_per40(s, "steals") or 0) + (_per40(s, "blocks") or 0)
    z = lambda d: {k: (v - statistics.mean(d.values())) / (statistics.pstdev(d.values()) or 1) for k, v in d.items()} if d else {}
    zs, zd = z(shoot), z(defence)
    for k, p in pool.items():
        base = MEDIAN_TOP * math.exp(-MEDIAN_DECAY * (p["consensus"] - 1))
        median = base * (1 + SHOOT_WEIGHT * zs.get(k, 0.0) + DEF_WEIGHT * zd.get(k, 0.0))
        spread = SPREAD_BASE * median * (1 + (23 - p["age"]) / 4)
        p.update(median=round(median, 4), floor=round(max(FLOOR_MIN, median - spread), 4), ceiling=round(median + 1.6 * spread, 4),
                 shoot_z=round(zs.get(k, 0.0), 3), def_z=round(zd.get(k, 0.0), 3))


def tiers(pool):
    """{key: tier}: a new tier where 0.6 median + 0.4 ceiling falls TIER_BREAK below the tier's first player."""
    score = lambda p: 0.6 * p["median"] + 0.4 * p["ceiling"]
    order = sorted(pool, key=lambda k: (-score(pool[k]), pool[k]["consensus"], k))
    out, tier, head = {}, 1, None
    for k in order:
        if head is not None and score(pool[k]) < (1 - TIER_BREAK) * score(pool[head]):
            tier += 1
            head = k
        head = head or k
        out[k] = tier
    return out


# -- 4: clubs ------------------------------------------------------------------------------------------------
def club_contexts(root=ROOT):
    """{club: {"stance", "need": {G, F, C}, "cornerstone": {G, F, C}}} on the draft date, from evidence of that date:
    the simulated 2003-04 records and lines (minutes, Game Score) and each club's contracts for the next three seasons."""
    from .lottery import records
    from .season_awards import candidates
    from .trades import dated_inventory
    from .valuation import Valuation
    from .write_back import closed_results
    root = Path(root)
    from .lottery import Year
    table = records(root) if YEAR == 2004 else records(root, Year(YEAR, root))
    form, _ = candidates(root, closed_results(root, SEASON, SEASON_END))
    by_bbr = {}
    registry = _read(root / "career/Dwyane_Wade/Stats_and_Awards/League/player_registry.json")
    registry = registry["players"] if isinstance(registry, dict) else registry
    names = {p["bbr_id"]: p["name"] for p in registry if p.get("bbr_id")}
    inventory = dated_inventory(DRAFT_DATE, Valuation(DRAFT_DATE, root), root)
    out = {}
    for club, t in table.items():
        stance = "contending" if t["wins"] >= CONTENDING_WINS else "rebuilding" if t["wins"] <= REBUILDING_WINS else "middle"
        players = _miami_contracts(root) if club == MIAMI else [
            {"name": names.get(p.get("bbr_id"), p.get("player")), "schedule": p.get("schedule") or {}}
            for p in inventory.get(club, {}).get("players", [])]
        need, cornerstone = {}, {}
        for g in ("G", "F", "C"):
            share = 0.0
            for season, weight in zip(_seasons_ahead(), (0.5, 0.3, 0.2)):
                minutes = sum(form[p["name"]]["mpg"] for p in players
                              if p["schedule"].get(season) and p["name"] in form and form[p["name"]]["position"] == g)
                share += weight * max(0.0, TARGET_MINUTES[g] - minutes) / TARGET_MINUTES[g]
            need[g] = round(share, 3)
            cornerstone[g] = any(p["schedule"].get(_seasons_ahead()[1]) and p["name"] in form and form[p["name"]]["position"] == g
                                 and form[p["name"]]["game_score"] >= CORNERSTONE_GMSC for p in players)
        out[club] = {"stance": stance, "record": f"{t['wins']}-{t['losses']}", "need": need, "cornerstone": cornerstone}
    # Charlotte, the expansion club in 2004: no record; rebuilding, with every position open until its roster exists.
    if YEAR == 2004:
        out["Charlotte Bobcats"] = {"stance": "rebuilding", "record": "expansion", "need": {"G": 1.0, "F": 1.0, "C": 1.0},
                                "cornerstone": {"G": False, "F": False, "C": False}}
    from .seasons import club_aliases, label
    for old_name, new_name in club_aliases(label(YEAR)).items():   # a renamed club's picks find its context
        if old_name in out:
            out.setdefault(new_name, out[old_name])
    return out


def _miami_contracts(root):
    sheet = _read(Path(root) / f"career/Dwyane_Wade/{SEASON}/00_Team/Finances/contract_schedules.json")
    return [{"name": p["player"], "schedule": p.get("schedule") or {}} for p in sheet["players"]
            if p.get("status") not in ("renounced", "released", "traded", "signed_elsewhere", "voided", "waived")]


def utility(p, ctx):
    wf, wm, wc = TIMELINE[ctx["stance"]]
    value = wf * p["floor"] + wm * p["median"] + wc * p["ceiling"]
    g = p["group"]
    if ctx["cornerstone"].get(g):
        fit = 0.88 if p["second_position"] else 0.75
    else:
        need = ctx["need"].get(g, 0.0)
        top = max(ctx["need"].values())
        fit = 1.15 if need >= 0.5 and need == top else 1.05 if need >= 0.3 else 0.90 if need <= 0.05 else 1.0
    return value * fit


def pick_value(slot):
    from .trades import PICK_DECAY, TOP_PICK_VALUE
    return TOP_PICK_VALUE * math.exp(-PICK_DECAY * (slot - 1))


# -- 5-6: draft night ----------------------------------------------------------------------------------------
def _draw(root, packet):
    path = Path(root) / DRAWS / f"{packet['event_id']}.decision.json"
    result = path.with_name(path.name.replace(".decision.json", ".decision.result.json"))
    if result.is_file():
        return _read(result)["outcome"]
    if not path.is_file():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(packet, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return None


def _options(scores):
    top = max(scores.values())
    weights = {k: math.exp((v - top) / TEMPERATURE) for k, v in scores.items()}
    total = sum(weights.values())
    probs = {k: max(0.000001, round(w / total, 6)) for k, w in weights.items()}
    drift = round(1 - sum(probs.values()), 6)
    first = max(probs, key=probs.get)
    probs[first] = round(probs[first] + drift, 6)
    return probs


def run(root=ROOT, clock=None):
    """Draft night, replayed from its recorded draws. Returns the record when every pick is made, else None."""
    from .write_back import clock as career_clock
    root = Path(root)
    if (clock or career_clock(root)) < DRAFT_DATE or (root / RECORD).is_file():
        return None
    order_path = root / FOLDER / f"draft_order_{YEAR}.json"
    if not order_path.is_file():
        return None
    order = _read(order_path)["picks"]
    pool, contexts = prospects(root), club_contexts(root)
    tier = tiers(pool)
    owners = {s["pick"]: s["owner_club"] for s in order}
    rounds = {s["pick"]: s["round"] for s in order}            # the order's own rounds (29 first-rounders in 2004, 30 later)
    taken, picks, trades = set(), [], []
    for slot in sorted(owners):
        club = owners[slot]
        available = [k for k in pool if k not in taken]
        best_tier = min(tier[k] for k in available)
        in_tier = [k for k in available if tier[k] == best_tier]
        ctx = contexts[club]
        if len(in_tier) >= 3 and len(trades) < MAX_TRADES:
            partner = _trade_partner(slot, owners, contexts, pool, tier, available, best_tier)
            if partner:
                later, gain = partner
                answer = _draw(root, {"event_id": f"{YEAR}-draft-pick-{slot}-trade-down", "date": DRAFT_DATE,
                                      "question": f"{YEAR} draft: does {club} trade No. {slot} to {owners[later]} for No. {later} and its {YEAR + 1} second-round pick?",
                                      "decider": f"{club} front office (engine draw)",
                                      "options": {"accept": TRADE_DOWN_ACCEPT, "decline": round(1 - TRADE_DOWN_ACCEPT, 6)},
                                      "basis": f"{len(in_tier)} players left in tier {best_tier}; {owners[later]} values its target {gain:.2f}x its "
                                               f"expected pick; chart value No. {slot} {pick_value(slot):.2f} vs No. {later} {pick_value(later):.2f} + a {YEAR + 1} second-rounder (runtime/draft.py)."})
                if answer is None:
                    return None
                if answer == "accept":
                    trades.append({"slot": slot, "from": club, "to": owners[later], "for_slot": later,
                                   "plus": f"{owners[later]} {YEAR + 1} second-round pick"})
                    owners[slot], owners[later] = owners[later], club
                    club, ctx = owners[slot], contexts[owners[slot]]
        scores = {k: utility(pool[k], ctx) for k in in_tier}
        top3 = dict(sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))[:3])
        if len(top3) == 1:
            choice = next(iter(top3))
        else:
            probs = _options(top3)
            choice = _draw(root, {"event_id": f"{YEAR}-draft-pick-{slot}", "date": DRAFT_DATE,
                                  "question": f"{YEAR} draft, No. {slot}: whom does {club} select ({', '.join(pool[k]['player'] for k in top3)})?",
                                  "decider": f"{club} front office (engine draw)",
                                  "options": {pool[k]["player"]: probs[k] for k in top3},
                                  "basis": f"Tier {best_tier} of the draft-night board; {ctx['stance']} club; utilities "
                                           + ", ".join(f"{pool[k]['player']} {v:.2f}" for k, v in top3.items()) + " (runtime/draft.py)."})
            if choice is None:
                return None
            choice = next(k for k in top3 if pool[k]["player"] == choice)
        taken.add(choice)
        p = pool[choice]
        picks.append({"pick": slot, "round": rounds[slot], "club": club, "player": p["player"], "bbr_id": p["bbr_id"],
                      "position": p["position"], "tier": best_tier, "consensus_slot": p["consensus"],
                      "floor": p["floor"], "median": p["median"], "ceiling": p["ceiling"]})
    record = {"schema_version": 1, "kind": "draft", "draft": f"{YEAR} NBA Draft", "date": DRAFT_DATE,
              "rule": __doc__.split("\n\n", 1)[1].strip(), "picks": picks, "trades": trades,
              "undrafted": sorted(pool[k]["player"] for k in pool if k not in taken),
              "board": [{"player": pool[k]["player"], "tier": tier[k], "consensus_slot": pool[k]["consensus"],
                         "floor": pool[k]["floor"], "median": pool[k]["median"], "ceiling": pool[k]["ceiling"]}
                        for k in sorted(pool, key=lambda k: (tier[k], pool[k]["consensus"]))],
              "clubs": contexts}
    (root / RECORD).parent.mkdir(parents=True, exist_ok=True)
    (root / RECORD).write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    _miami_pick_ledger(root, trades)
    return record


def _miami_pick_ledger(root, trades):
    """A draft-night trade that sends Miami's next-year second-round pick away is recorded in Miami's pick ledger."""
    path = Path(root) / f"career/Dwyane_Wade/{SEASON}/00_Team/Finances/draft_picks.json"
    data = _read(path)
    changed = False
    for t in trades:
        if t["to"] != MIAMI:
            continue                       # Miami moved up: it gave its own next-year second-rounder
        for pick in data["picks"]:
            if pick["year"] == YEAR + 1 and pick["round"] == 2 and pick["original_club"] == MIAMI and pick["owned"]:
                pick["owned"] = False
                pick["history"].append({"date": DRAFT_DATE, "to": t["from"], "event": f"traded to {t['from']} with Miami's move from No. "
                                        f"{t['for_slot']} to No. {t['slot']} in the {YEAR} draft", "source": RECORD.as_posix()})
                changed = True
    if changed:
        path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def _trade_partner(slot, owners, contexts, pool, tier, available, best_tier):
    """The first later club (within TRADE_WINDOW) that gains TRADE_UP_GAIN by moving up for a tier player."""
    from .trades import SECOND_ROUND_VALUE
    on_clock = owners[slot]
    for later in range(slot + 1, slot + TRADE_WINDOW + 1):
        club = owners.get(later)
        if club is None or club == on_clock:
            continue
        ctx = contexts[club]
        ranked = sorted(available, key=lambda k: -utility(pool[k], ctx))
        target = ranked[0]
        expected = ranked[min(len(ranked) - 1, later - slot)]
        if tier[target] != best_tier:
            continue
        gain = utility(pool[target], ctx) / max(0.01, utility(pool[expected], ctx))
        if gain >= TRADE_UP_GAIN and pick_value(later) + SECOND_ROUND_VALUE >= 0.9 * pick_value(slot):
            return later, gain
    return None


def miami_choices(root=ROOT):
    """Miami's picks from the recorded draft (empty before it)."""
    path = Path(root) / RECORD
    return [p for p in _read(path)["picks"] if p["club"] == MIAMI] if path.is_file() else []


def drafted_clubs(root=ROOT):
    """{bbr_id: club} for every player drafted in the simulated draft (empty before it)."""
    path = Path(root) / RECORD
    return {p["bbr_id"]: p["club"] for p in _read(path)["picks"] if p.get("bbr_id")} if path.is_file() else {}
