"""Every club's roster on a career date, its strength in projected wins, and a player's role there.

A free agent weighs where he is going and where he is coming from by the rosters as they stand on
the date, with him on them (runtime/player_utility.py, contention and role). Rosters therefore move
with every signing: a club that has just added a guard offers the next guard a smaller role, and a
club that has added a starter projects more wins.

Real clubs: the end-of-2002-03 rosters (`nba_2003_end_of_season.json`), changed by the real
offseason moves dated on or before the date (signings, trades, waivers), with the user's conflict
rules: a real move involving Miami is skipped and a player Miami holds leaves his real club (option
D, AGENTS.md). Miami: the players its ledger counts as under contract on the date.

Strength: each club's top players by production value (runtime/valuation.py) weighted by rotation
share, turned into wins by a straight line fitted on the 2002-03 rosters against the 2002-03
standings: last season's evidence only, refitted whenever the data changes, never this season's
results. A player without a 2002-03 line (a rookie) adds nothing; that is a stated limit.
"""
from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path

from .player_stats import alias

ROOT = Path(__file__).resolve().parents[1]
END_OF_SEASON = Path("library/2003/league/nba_2003_end_of_season.json")
STANDINGS = Path("library/2003/league/nba_2002_03_standings.json")
TRANSACTIONS = Path("library/2003/league/nba_2003_offseason_transactions.json")
STATS = Path("library/2003/league/nba_2002_03_player_stats.json")
LEDGER = Path("career/Dwyane_Wade/2003-04/00_Team/Finances/contract_schedules.json")
MIAMI = "Miami Heat"
ROTATION = (0.15, 0.14, 0.13, 0.12, 0.11, 0.10, 0.08, 0.07, 0.05, 0.03, 0.02)   # share of minutes by value rank (judgement)
WINS_LIMITS = (12, 66)
GROUP = {"PG": "G", "SG": "G", "SF": "F", "PF": "F", "C": "C"}
ROLE_BY_RANK = (34, 26, 16, 8)        # minutes for the 1st, 2nd, 3rd and later player in his position group (judgement)
NOT_ON_ROSTER = ("free_agent", "declined", "unsigned", "renounced", "signed_elsewhere", "traded", "waived", "released")


def _read(path, root):
    return json.loads((Path(root) / path).read_text(encoding="utf-8"))


class League:
    """The league's rosters on one date; `value` is a callable bbr_id -> production value or None."""

    def __init__(self, on, value, root=ROOT):
        self.on, self.value, self.root = on, value, Path(root)
        end = _read(END_OF_SEASON, root)["clubs"]
        self.position = {}
        self.names = {}
        for club, entry in end.items():
            for p in entry["players"]:
                if p.get("bbr_id"):
                    self.position[p["bbr_id"]] = GROUP.get((p.get("position") or "SF").split("-")[0], "F")
                    self.names[alias(p.get("player_id") or "")] = p["bbr_id"]
        for r in _read(STATS, root)["records"]:
            self.names.setdefault(alias(r["player_name"]), r["bbr_id"])
        self.baseline = {club: {p["bbr_id"] for p in e["players"] if p.get("bbr_id")} for club, e in end.items()}
        self.rosters = self._on_date()
        self.line = self._fit()

    def bbr(self, name):
        return self.names.get(alias(name.split(" (")[0]))

    def miami(self):
        out = set()
        path = self.root / LEDGER
        if path.is_file():
            for p in _read(LEDGER, self.root)["players"]:
                if not any(word in p["status"] for word in NOT_ON_ROSTER):
                    key = p.get("bbr_id") or self.bbr(p["player"])
                    if key:
                        out.add(key)
        return out

    def _on_date(self):
        rosters = {club: set(players) for club, players in self.baseline.items()}
        moves = _read(TRANSACTIONS, self.root)
        events = []
        from .market import UNDATED_EXIT
        for row in moves["signings"]:
            if (row["date"] or UNDATED_EXIT) <= self.on and not row.get("involves_miami"):
                events.append((row["date"] or UNDATED_EXIT, "sign", row))
        for row in moves["trades"]:
            if row["date"] <= self.on and not row.get("involves_miami"):
                events.append((row["date"], "trade", row))
        for row in moves["waivers"]:
            if row["date"] <= self.on and not row.get("involves_miami"):
                events.append((row["date"], "waive", row))
        for _, kind, row in sorted(events, key=lambda e: e[0]):
            if kind == "sign":
                key = row.get("bbr_id") or self.bbr(row["player"])
                if key and row["to"] in rosters:
                    for members in rosters.values():
                        members.discard(key)
                    rosters[row["to"]].add(key)
            elif kind == "waive":
                key = row.get("bbr_id") or self.bbr(row["player"])
                rosters.get(row["club"], set()).discard(key)
            else:
                for club, sides in row["clubs"].items():
                    for name in sides.get("out", []):
                        key = self.bbr(name)
                        if key and club in rosters:
                            rosters[club].discard(key)
                    for name in sides.get("in", []):
                        key = self.bbr(name)
                        if key and club in rosters:
                            rosters[club].add(key)
        held = self.miami()
        for club in rosters:
            rosters[club] -= held                       # rule 2: a player Miami holds is not on a real club
        rosters[MIAMI] = held
        return rosters

    def raw_strength(self, members):
        values = sorted((v for v in (self.value(b) for b in members) if v), reverse=True)
        return sum(w * v for w, v in zip(ROTATION, values))

    def _fit(self):
        standings = _read(STANDINGS, self.root)["clubs"]
        points = [(self.raw_strength(self.baseline[c]), standings[c]["wins"]) for c in self.baseline if c in standings]
        n = len(points)
        mx = sum(x for x, _ in points) / n
        my = sum(y for _, y in points) / n
        sxx = sum((x - mx) ** 2 for x, _ in points) or 1.0
        slope = sum((x - mx) * (y - my) for x, y in points) / sxx
        return {"intercept": my - slope * mx, "slope": slope, "clubs": n}

    def wins(self, club, add=(), remove=()):
        members = (set(self.rosters.get(club, set())) | set(add)) - set(remove)
        w = self.line["intercept"] + self.line["slope"] * self.raw_strength(members)
        return round(max(WINS_LIMITS[0], min(WINS_LIMITS[1], w)), 1)

    def role_minutes(self, club, bbr_id):
        """His minutes from his value rank inside his position group on the club, with him on it."""
        group = self.position.get(bbr_id, "F")
        mine = self.value(bbr_id) or 0
        ahead = sum(1 for b in self.rosters.get(club, set())
                    if b != bbr_id and self.position.get(b, "F") == group and (self.value(b) or 0) > mine)
        return ROLE_BY_RANK[min(ahead, len(ROLE_BY_RANK) - 1)]

    def situation(self, club, bbr_id):
        """Projected wins with him on the club and his role there: what he weighs about that club."""
        return {"club": club, "strength": self.wins(club, add=[bbr_id]), "role_minutes": self.role_minutes(club, bbr_id),
                "strength_basis": f"{club} roster on {self.on} with him: fitted line {self.line['intercept']:.1f} + "
                                  f"{self.line['slope']:.3f} x rotation-weighted production value"}
