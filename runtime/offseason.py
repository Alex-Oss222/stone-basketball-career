"""Symmetric league, phase 5: the 2004 offseason for the 28 real clubs and Charlotte (docs/symmetric_league_design.md).

The result is the 2004-05 opening book: every club's players on the first day of the 2004-05 season, each with the
rule that placed him, written to `career/Dwyane_Wade/2004-05/League/opening_rosters.json` and read by the 2004-05
league (`league_moves` activation for the season). Miami is never placed here: its offseason is its own front office.

Principles (unchanged from phases 1 to 4): ability follows real careers; no real player with real 2004-05 minutes is
left without a club; no club decides on hindsight; Miami's real transactions are skipped (AGENTS.md rule 1).

Once the simulated 2004 market is complete (`runtime/free_agency_2004.py`, the user's choice of a fully simulated
offseason), it alone places every player: rule 7, his club under a 2004-05 contract after the market (Miami's
included, which its rollover reads); rule 8, a player with a real 2004-05 role left unsigned starts in the free-agent
pool for the in-season market. The rules below are the history-following book used before then.

For each real player, in this order:
1. **Miami holds him** on the opening date (rule 2): he is Miami's, not placed here.
2. **No real 2004-05 minutes** (retired, abroad, out of the league): he leaves the league with history.
3. **Real Miami sent him away** (`nba_2004_miami_transactions.json`, the July 14 Shaquille O'Neal trade): rule 1
   skips the move; he stays with his simulated 2003-04 club.
4. **Undrifted** (his simulated club at the season's end is his real club at the season's end): he follows history
   to his real 2004-05 opening club — re-signings, option outcomes, real summer trades, free-agent moves, Charlotte's
   expansion draft and the draft itself — because nothing simulated conflicts.
5. **Drifted** (a simulated trade, claim or signing moved him in 2003-04): a contract that runs through 2004-05
   (salary, not an option) stays with his simulated club, as an assigned agreement; otherwise he is a free agent and
   signs where history signed him.
6. **New to the league** (2004 draftees, returning or overseas players with no 2003-04 NBA club): his real club.
   A 2004 prospect drafted in the simulated draft (`draft.py`) goes to the club that drafted him.
A player's real 2004-05 opening club is his first 2004-05 stint; a later real arrival is placed with that club from
opening day (his games share keeps his real part of the season). Each club then keeps its fifteen largest real
2004-05 roles (never letting go of a rookie-scale contract); the rest start in the free-agent pool, as at the
December 3, 2003 activation.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD, NEW = "2003-04", "2004-05"
SEASON_END = "2004-06-30"
CHARLOTTE = "Charlotte Bobcats"
MIAMI = "Miami Heat"
SKIPPED = Path("library/2004/league/nba_2004_miami_transactions.json")
DRAFT = Path("library/2004/league/nba_2004_draft_class.json")
BOOK = Path(f"career/Dwyane_Wade/{NEW}/League/opening_rosters.json")
ROSTER_MAX = 15


def _read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def real_clubs(season, root=ROOT):
    """{bbr_id: (first club, last club, role)} from the season's real rosters (stints by window)."""
    from .rotations import load_rosters
    stints = defaultdict(list)
    for club, entry in load_rosters(season, root).items():
        for p in entry["players"]:
            if p.get("bbr_id"):
                stints[p["bbr_id"]].append(((p.get("window") or [0.0, 1.0])[0], club, p))
    out = {}
    for b, rows in stints.items():
        rows.sort(key=lambda r: r[0])
        role = {"player_id": rows[0][2]["player_id"], "bbr_id": b, "position": rows[0][2]["position"],
                "games": sum(r[2]["games"] for r in rows), "minutes": sum(r[2]["minutes"] for r in rows)}
        out[b] = (rows[0][1], rows[-1][1], role)
    return out


def simulated_clubs(root=ROOT, on=SEASON_END):
    """{bbr_id: club} for the real clubs at the end of 2003-04 in the symmetric league (Miami excluded)."""
    from .league_moves import effective_roster
    from .rotations import load_rosters
    out = {}
    for club in load_rosters(OLD, root):
        for p in effective_roster(club, on, OLD, root):
            if p.get("bbr_id"):
                out[p["bbr_id"]] = club
    return out


def miami_players(root=ROOT, on=SEASON_END):
    """Players simulated Miami holds (rule 2), including the draft rights it took on June 24 (`runtime/draft.py`)."""
    from .rotations import miami_holds
    held = set(miami_holds(OLD, on, root))
    from .draft import miami_choices
    held |= {c["bbr_id"] for c in miami_choices(root) if c.get("bbr_id")}
    return held


def skipped_moves(root=ROOT):
    path = Path(root) / SKIPPED
    if not path.is_file():
        return set()
    return {p["bbr_id"] for t in _read(path)["transactions"] for p in t["players_out_of_miami"]}


def continuing(root=ROOT, on=SEASON_END):
    """{bbr_id: club} for contracts with a 2004-05 salary (not an option) on the date, as the league book holds them."""
    from .contract_terms import existing_terms
    sim = simulated_clubs(root, on)
    out = {b: sim.get(b) or t["club"] for b, t in existing_terms(root).items() if t["kind"] == "contract"}
    return {b: c for b, c in out.items() if c and c != MIAMI}


def draft_swaps(root=ROOT):
    """{bbr_id: club} for every player the simulated 2004 draft gave to a club (`runtime/draft.py`), else {}."""
    from .draft import drafted_clubs
    return {b: c for b, c in drafted_clubs(root).items() if c != MIAMI}


def placements(root=ROOT, on=SEASON_END):
    """[{bbr_id, player_id, club, rule, from_club}] for every real player with a 2004-05 role or a 2003-04 club."""
    old, new = real_clubs(OLD, root), real_clubs(NEW, root)
    sim, miami, skip, cont, swaps = simulated_clubs(root, on), miami_players(root, on), skipped_moves(root), continuing(root, on), draft_swaps(root)
    from .expansion import charlotte_players
    from .free_agency_2004 import signed_clubs
    expanded, market = charlotte_players(root), signed_clubs(root)
    out = []
    for b in sorted(set(old) | set(new) | set(sim) | set(market)):
        role_new = new.get(b)
        name = (role_new or old.get(b) or (None, None, {"player_id": b}))[2]["player_id"]
        s_club = sim.get(b)
        if market:                                      # the simulated 2004 market decides every 2004-05 club
            if b in market:
                out.append(dict(bbr_id=b, player_id=name, club=market[b], rule="7_contract_after_the_2004_market", from_club=s_club))
            else:
                out.append(dict(bbr_id=b, player_id=name, club=None, rule="8_unsigned_after_the_2004_market", from_club=s_club))
            continue
        if b in miami:
            out.append(dict(bbr_id=b, player_id=name, club=MIAMI, rule="1_miami_holds", from_club=s_club))
            continue
        if role_new is None:
            out.append(dict(bbr_id=b, player_id=name, club=None, rule="2_no_real_2004_05_minutes", from_club=s_club))
            continue
        r_open = role_new[0]
        if b in swaps:
            out.append(dict(bbr_id=b, player_id=name, club=swaps[b], rule="6_drafted_in_the_simulated_draft", from_club=None))
        elif b in expanded:
            out.append(dict(bbr_id=b, player_id=name, club=CHARLOTTE, rule="5_expansion_draft", from_club=s_club))
        elif b in skip and s_club:
            out.append(dict(bbr_id=b, player_id=name, club=s_club, rule="3_real_miami_move_skipped", from_club=s_club))
        elif s_club is None:
            out.append(dict(bbr_id=b, player_id=name, club=r_open, rule="6_new_to_the_league", from_club=None))
        elif b in old and s_club == old[b][1]:
            out.append(dict(bbr_id=b, player_id=name, club=r_open, rule="4_undrifted_follows_history", from_club=s_club))
        elif cont.get(b) == s_club:
            out.append(dict(bbr_id=b, player_id=name, club=s_club, rule="5_drifted_contract_continues", from_club=s_club))
        else:
            out.append(dict(bbr_id=b, player_id=name, club=r_open, rule="5_drifted_free_agent_signs_with_history", from_club=s_club))
    return out, new


def opening_book(root=ROOT, on=SEASON_END):
    """{club: [players]} with the fifteen-player limit applied; the rest go to the pool."""
    rows, new = placements(root, on)
    clubs = defaultdict(list)
    for r in rows:
        if r["club"] and r["club"] != MIAMI:
            role = (new.get(r["bbr_id"]) or (None, None, {}))[2]
            clubs[r["club"]].append(dict(r, games=role.get("games", 0), minutes=role.get("minutes", 0),
                                         position=role.get("position")))
    pool = []
    for club, players in clubs.items():
        players.sort(key=lambda p: (-p["minutes"], p["bbr_id"]))
        if len(players) > ROSTER_MAX:
            pool += [dict(p, rule=p["rule"] + "+pool_over_fifteen") for p in players[ROSTER_MAX:]]
            clubs[club] = players[:ROSTER_MAX]
    # A real player the summer market left unsigned starts the season in the free-agent pool, where every club's
    # market can sign him (career continuity: never out of the league while history gave him minutes).
    for r in rows:
        if r["club"] is None:
            role = (new.get(r["bbr_id"]) or (None, None, {}))[2]
            pool.append(dict(r, games=role.get("games", 0), minutes=role.get("minutes", 0), position=role.get("position"),
                             rule=r["rule"] + "+pool_unsigned"))
    out = [r for r in rows if r["club"] == MIAMI]
    return {"schema_version": 1, "season": NEW, "kind": "opening_rosters", "as_of": on,
            "rule": __doc__.split("\n\n", 1)[1].strip(),
            "clubs": {c: clubs[c] for c in sorted(clubs)}, "pool": sorted(pool, key=lambda p: -p["minutes"]),
            "not_placed": out,
            "counts": dict(Counter(r["rule"] for r in rows))}


def write(root=ROOT, on=SEASON_END):
    book = opening_book(root, on)
    path = Path(root) / BOOK
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(book, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return book


def book_for(season):
    """The season's opening book (`league_moves.book_path`)."""
    from .league_moves import book_path
    return book_path(season)


def later_book(season, root=ROOT):
    """A later season's opening book (R5): the simulated summer market alone places every player (rules 7 and 8). Each
    club keeps its fifteen with the most real minutes for the season; the rest, and every real player the market left
    unsigned, start in the free-agent pool unless his real career has ended (runtime/availability.py: a retired player
    never comes back; one who sits the season out is not in the pool)."""
    from .availability import status
    from .free_agency_2004 import market_year, record_path
    root = Path(root)
    record = _read(root / record_path(market_year(season)))
    new = real_clubs(season, root)
    role = lambda b: (new.get(b) or (None, None, {}))[2]
    clubs, pool, held, counts = defaultdict(list), [], set(), Counter()
    for club, rows in record["clubs"].items():
        for r in rows:
            b = r.get("bbr_id")
            if not b:
                continue
            held.add(b)
            row = dict(bbr_id=b, player_id=r["player"], club=club, rule="7_contract_after_the_summer_market",
                       from_club=r.get("from"), games=role(b).get("games", 0), minutes=role(b).get("minutes", 0),
                       position=role(b).get("position") or r.get("position"))
            counts[row["rule"]] += 1
            clubs[club].append(row)
    miami = clubs.pop(MIAMI, [])
    for club, players in clubs.items():
        players.sort(key=lambda p: (-p["minutes"], p["bbr_id"]))
        if len(players) > ROSTER_MAX:
            pool += [dict(p, rule=p["rule"] + "+pool_over_fifteen") for p in players[ROSTER_MAX:]]
            clubs[club] = players[:ROSTER_MAX]
    for p in record.get("unsigned_pool", []):
        b = p.get("bbr_id")
        if not b or b in held or status(b, season, root) != "available":
            continue
        counts["8_unsigned_after_the_summer_market"] += 1
        pool.append(dict(bbr_id=b, player_id=p["player"], club=None, rule="8_unsigned_after_the_summer_market+pool_unsigned",
                         from_club=p.get("rights"), games=role(b).get("games", 0), minutes=role(b).get("minutes", 0),
                         position=role(b).get("position") or p.get("position")))
    return {"schema_version": 1, "season": season, "kind": "opening_rosters", "as_of": f"{market_year(season)}-09-30",
            "rule": later_book.__doc__.strip(), "clubs": {c: clubs[c] for c in sorted(clubs)},
            "pool": sorted(pool, key=lambda p: -p["minutes"]), "not_placed": miami, "counts": dict(counts)}


def write_season(season, root=ROOT):
    """Write the season's opening book: 2004-05 by its own rules, later seasons from their summer market."""
    if season == NEW:
        return write(root)
    book = later_book(season, root)
    path = Path(root) / book_for(season)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(book, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return book
