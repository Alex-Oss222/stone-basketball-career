"""Symmetric league, phase 1: every club's cap book on a date (docs/symmetric_league_design.md).

Read-only. For each real club on the date: its contracts (`trades.dated_inventory`, the June 26, 2003 terms
moved by the world's dated moves), 2003-04 payroll, cap room, tax position, roster count, whether its
mid-level exception is still open, and an owner payroll ceiling. Miami's book is its own ledger and is not
rebuilt here. Nothing in the league reads this book while `SYMMETRIC_FROM` is None.

Judgement constants:
- OWNER_CEILING: an owner pays up to the tax line, or 2% over his current payroll if already above it.
- A mid-level exception counts as used when the club, over the cap, made a summer signing reported above
  the minimum to a player whose Bird rights it did not hold (an inference; the 1999 CBA allows one MLE a season).
"""
import json
from pathlib import Path

from .trades import (CAP_RULES_PATH, MIAMI, SEASON, TRANSACTIONS_PATH, UNDER_CONTRACT, dated_inventory,
                     read_json)

ROOT = Path(__file__).resolve().parents[1]
SYMMETRIC_FROM = "2003-12-03"        # the user's switch: a date turns the league symmetric from then; None keeps option D
OWNER_OVER_TAX_STRETCH = 1.02


def club_cap(club, season, cap, root=ROOT):
    """A club's salary cap for the season: the league cap, or an expansion club's own cap where the season's offseason
    calendar records one (Charlotte 2004-05: $29.25M, `charlotte_cap_and_floor_2004_05`)."""
    from .seasons import start_year
    year = start_year(season)
    path = Path(root) / f"library/{year}/league/nba_{year}_offseason_calendar.json"
    if not path.is_file():
        return cap
    key = f"{club.split()[0].lower()}_cap_and_floor_{season.replace('-', '_')}"
    entry = json.loads(path.read_text(encoding="utf-8")).get(key)
    return entry["value"]["cap"] if entry else cap


def owner_ceiling(payroll, tax_line):
    return max(tax_line, int(payroll * OWNER_OVER_TAX_STRETCH)) if payroll > tax_line else tax_line


class LeagueBook:
    def __init__(self, on, market, root=ROOT):
        self.on, self.root = on, Path(root)
        self.valuation = market.valuation
        from .seasons import path as season_path, season_of_date, start_year
        self.season = season_of_date(on)
        if self.season == SEASON:
            rules = read_json(CAP_RULES_PATH, root)
            self.cap, self.tax_line = rules["salary_cap"], rules.get("luxury_tax_line_projection_july_2003", 57000000)
            self.signings = [r for r in read_json(TRANSACTIONS_PATH, root)["signings"]
                             if not r.get("involves_miami") and (r.get("date") or "9999") <= on]
        else:
            rules = read_json(season_path(self.season, "cap_rules"), root)
            year = start_year(self.season)
            calendar = read_json(f"library/{year}/league/nba_{year}_offseason_calendar.json", root)
            self.cap = rules["salary_cap"]
            self.tax_line = rules.get("luxury_tax_line") or calendar[f"luxury_tax_threshold_{self.season.replace('-', '_')}"]["value"]
            market_path = root / f"career/Dwyane_Wade/{self.previous()}/10_Free_Agency/free_agency_{year}.json"
            events = read_json(market_path.relative_to(root), root)["events"] if market_path.is_file() else []
            self.signings = [{"to": e["club"], "kind": "mid_level"} for e in events if e.get("route") == "mid_level"]
        self.minimum = self.valuation.minimum(0)
        self.inventory = dated_inventory(on, self.valuation, root)

    def previous(self):
        from .seasons import previous_season
        return previous_season(self.season)

    def club(self, name):
        if name == MIAMI:
            raise ValueError("Miami's book is its own ledger (runtime/gm.py, runtime/signing.py)")
        players = self.inventory.get(name, {}).get("players", [])
        signed = [p for p in players if p.get("status") in UNDER_CONTRACT or "option_exercised" in (p.get("status") or "")]
        payroll = sum(int(p["schedule"].get(self.season) or 0) for p in signed)
        if self.season == SEASON:
            mle_used = any(r.get("to") == name and r.get("kind") == "signing" and (r.get("total") or 0) / max(1, r.get("years") or 1) > self.minimum * 1.5
                           for r in self.signings) and payroll > self.cap
        else:
            mle_used = any(r["to"] == name for r in self.signings)
        cap = club_cap(name, self.season, self.cap, self.root)
        return {"club": name, "on": self.on, "payroll": payroll, "cap_room": max(0, cap - payroll), "cap": cap,
                "over_tax": payroll > self.tax_line, "roster": len([p for p in players if p.get("bbr_id")]),
                "under_contract": len(signed), "mid_level_open": payroll > cap and not mle_used,
                "owner_ceiling": owner_ceiling(payroll, self.tax_line)}

    def all(self):
        return {name: self.club(name) for name in sorted(self.inventory) if name != MIAMI}


def active(on):
    """Whether the symmetric league is switched on for this date."""
    return SYMMETRIC_FROM is not None and on >= SYMMETRIC_FROM
