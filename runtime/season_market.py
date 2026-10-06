"""The market Miami's front office reads on a date in a season after the first (camp invites, cap room, trades).

The first season's front office read the 2003 summer market (`runtime/market.py`: the real 2003 rights files and
transactions). From 2004-05 the summer is simulated for every club (`runtime/free_agency_2004.py`), so the season's
market is that record: who was left unsigned when it closed, with his rights and service, priced by the season's
valuation (`runtime/valuation.py`, which reads the simulated prior season). The cap is the season's published figure
once its publication date has passed (`league_cap_history.json`), else the prior season's.

`for_date(on)` returns the right one, so callers never name a season.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIRST = "2003-04"


def _read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def season_for(on):
    from .seasons import season_of_date
    return season_of_date(on) if on >= "2003-07-01" else FIRST


def for_date(on, root=ROOT):
    """The market for a front-office date: the 2003 market in the first season, the simulated summer's after."""
    if season_for(on) == FIRST:
        from .market import Market
        return Market(on, root)
    return SeasonMarket(on, root)


def summer_record(season, root=ROOT):
    """The summer market's record that opened the season, or None before it closed."""
    from .free_agency_2004 import NEW, RECORD
    path = Path(root) / RECORD
    if season != NEW or not path.is_file():
        return None
    return _read(path)


class SeasonMarket:
    """The interface `gm.FrontOffice`, `camp` and `trades` read from a market, for a season after the first."""

    def __init__(self, on, root=ROOT):
        from .valuation import Valuation
        self.on, self.root = on, Path(root)
        self.season = season_for(on)
        self.valuation = Valuation(on, root)
        self.record = summer_record(self.season, root)
        if self.record is None:
            raise RuntimeError(f"{on}: the {self.season} summer market has not closed; the season's market is its record")
        from .free_agency_2004 import identity
        ident = identity(self.root)
        service = {b: e.get("service") for b, e in ident.items()}
        self.players = {}
        for p in self.record["unsigned_pool"]:
            self.players[p["bbr_id"]] = {"player": p["player"], "bbr_id": p["bbr_id"], "club": None, "rights": p.get("rights"),
                                         "price": p.get("price"), "nba_seasons_before_2003_04": service.get(p["bbr_id"]),
                                         "nba_history": service.get(p["bbr_id"]) is not None}
        self._signed = self._signed_after()

    def _signed_after(self):
        """{bbr_id: (date, club)} for pool players a club signed in the season after the summer closed."""
        from .league_moves import read
        out = {}
        for m in sorted(read(self.season, self.root)["entries"], key=lambda m: m["date"]):
            if m.get("to") and m.get("bbr_id") in self.players:
                out.setdefault(m["bbr_id"], (m["date"], m["to"]))
        return out

    # -- availability --------------------------------------------------------------------------
    def restricted(self, bbr_id):
        """An unsigned player whose club still holds a restricted right of first refusal."""
        rights = (self.players.get(bbr_id) or {}).get("rights") or ""
        return "restricted" in str(rights)

    def exit(self, bbr_id):
        return self._signed.get(bbr_id)

    def available(self, bbr_id, on=None):
        on = on or self.on
        e = self._signed.get(bbr_id)
        return bbr_id in self.players and (e is None or e[0] > on)

    def pool(self, on=None):
        """Free agents a club may sign on the date: unsigned, and playing in the NBA that season in history
        (`runtime/availability.py`: a retired player or one who sat the season out is never signed)."""
        on = on or self.on
        from .availability import signable
        return {b: p for b, p in self.players.items() if self.available(b, on) and signable(b, self.season, self.root)}

    # -- the cap -------------------------------------------------------------------------------
    def cap_known(self, on=None):
        on = on or self.on
        from .seasons import active
        history = self.root / f"career/Dwyane_Wade/{active(self.root)}/00_Team/Finances/league_cap_history.json"
        if not history.is_file():
            history = self.root / "career/Dwyane_Wade/2003-04/00_Team/Finances/league_cap_history.json"
        row = next((r for r in _read(history)["seasons"] if r.get("season") == self.season), None)
        published = (row or {}).get("published_date")
        return bool(published) and published <= on

    def planning_cap(self, on=None):
        on = on or self.on
        from .seasons import path, previous_season
        if self.cap_known(on):
            return _read(self.root / path(self.season, "cap_rules"))["salary_cap"]
        return _read(self.root / path(previous_season(self.season), "cap_rules"))["salary_cap"]
