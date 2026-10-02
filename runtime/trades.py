"""Trades between simulated Miami and a real club (docs/front_office_design.md, section 7).

Legality follows the 1999 rules as recorded in `nba_1999_cba_rules.json` (the module
names the rule it used, inferred ones included). Values follow the design: a
player's production value above replacement with a contract term, picks from a
1999-era chart placed by the owning club's last record, a star premium before
summing. A real club's answer is a logistic draw of its value change under its
posture, written as a decision packet the engine draws; the same proposal on
the same date gives the same packet. Nothing here writes career records.
"""
from datetime import date, timedelta
import hashlib
import json
import math
from pathlib import Path

from .contracts import club_ledger
from .valuation import read

ROOT = Path(__file__).resolve().parents[1]
SEASON = "2003-04"
MIAMI = "Miami Heat"
TEAM = Path(f"career/Dwyane_Wade/{SEASON}/00_Team")
CBA_PATH = Path("library/2003/league/nba_1999_cba_rules.json")
CAP_RULES_PATH = Path("library/2003/league/nba_2003_04_cap_rules.json")
STANDINGS_PATH = Path("library/2003/league/nba_2002_03_standings.json")
CONTRACTS_PATH = Path("library/2003/league/nba_2003_contracts.json")
END_OF_SEASON_PATH = Path("library/2003/league/nba_2003_end_of_season.json")
TRANSACTIONS_PATH = Path("library/2003/league/nba_2003_offseason_transactions.json")
PICKS_PATH = TEAM / "Finances/draft_picks.json"
MORATORIUM = ("2003-07-01", "2003-07-15")
PROTAGONIST = "Dwyane Wade"

# Judgement constants (design 7.2 to 7.4), named so they can be revisited.
REPLACEMENT_VALUE = 5.0                  # efficiency per game of a minimum player (valuation.py)
POINTS_PER_EFFICIENCY = 0.25             # value points per efficiency point above replacement (a 25-a-game star is 5)
CONTRACT_YEARS_COUNTED = 3               # seasons of surplus or burden counted
CONTRACT_TERM_LIMITS = (-2.0, 2.0)       # value points
EXPIRING_RELIEF_PER_5M = 0.3             # for a club over the tax projection
NEGATIVE_SHARE = 0.05                    # a negative asset counts at a twentieth
STAR_EXPONENT = 7                        # Basketball GM: assets above 1 are raised to this before summing
TOP_PICK_VALUE, PICK_DECAY = 4.0, 0.0555  # chart: value(slot) = TOP x exp(-decay x (slot - 1)); 1st pick about 5x the 30th
SECOND_ROUND_VALUE = 0.1
FUTURE_PICK_REGRESSION = 0.5             # slots regress halfway to the middle each year further out
MIAMI_PICK_PESSIMISM = 4                 # Miami's own picks are placed this many slots later than its record says
POSTURE = {"contending": {"players": 1.15, "picks": 0.7, "old_players": 1.0}, "middle": {"players": 1.0, "picks": 1.0, "old_players": 1.0},
           "rebuilding": {"players": 0.9, "picks": 1.3, "old_players": 0.7}}
CONTENDING_WINS, REBUILDING_WINS, OLD_AGE = 50, 30, 30
ACCEPT_SLOPE, ACCEPT_LIMITS = 6.0, (0.02, 0.90)   # on the relative value change (-1 to 1)
MAX_OUT, MAX_IN = 2, 2                   # players a search proposal moves each way
SEARCH_MIN_GAIN = 0.05                   # Miami's value gain for a proposal to be worth making


def read_json(path, root=ROOT):
    return read(path, root)


# -- assets ------------------------------------------------------------------------------------
class Assets:
    """Values of players and picks on a date, from on-date evidence."""

    def __init__(self, on, market, root=ROOT):
        self.on, self.market, self.root = on, market, Path(root)
        self.valuation = market.valuation
        self.standings = read_json(STANDINGS_PATH, root)["clubs"]
        self.contracts = read_json(CONTRACTS_PATH, root)["clubs"]
        self.cap_rules = read_json(CAP_RULES_PATH, root)
        self.tax_line = self.cap_rules.get("luxury_tax_line_projection_july_2003", 57000000)
        self.positions = {}
        for club, entry in read_json(END_OF_SEASON_PATH, root)["clubs"].items():
            for p in entry["players"]:
                if p.get("bbr_id"):
                    self.positions[p["bbr_id"]] = (club, p.get("position") or "SF", p.get("depth") or 9)

    def posture(self, club):
        wins = self.standings.get(club, {}).get("wins", 41)
        return "contending" if wins >= CONTENDING_WINS else "rebuilding" if wins <= REBUILDING_WINS else "middle"

    def payroll(self, club):
        if club == MIAMI:
            return None   # Miami's ledger is the front office's
        return club_ledger(club, SEASON, self.root)["known_total"]

    def salary(self, player):
        """2003-04 salary of a player entry (Miami sheet or inventory shape)."""
        return int(player["schedule"].get(SEASON) or 0)

    def years_left(self, player):
        return sum(1 for s, v in player["schedule"].items() if s >= SEASON and v and player.get("amount_kind", {}).get(s) == "contract_salary")

    def player_value(self, player, for_club=None):
        """Value points of a player under contract: production above replacement plus his contract term."""
        bbr = player.get("bbr_id")
        value = self.valuation.value(bbr) if bbr else None
        if value is None:
            production = 0.0
            basis = "no 2002-03 evidence: production counted at replacement"
        else:
            production = max(0.0, value - REPLACEMENT_VALUE) * POINTS_PER_EFFICIENCY
            basis = f"2002-03 production value {value:.1f}"
        salary, years = self.salary(player), min(CONTRACT_YEARS_COUNTED, max(1, self.years_left(player)))
        worth = self.valuation.comparables_price(value) if value is not None else self.valuation.minimum(0)
        term = (worth - salary) * years / self.valuation.mid_level * 0.5 if salary else 0.0
        term = max(CONTRACT_TERM_LIMITS[0], min(CONTRACT_TERM_LIMITS[1], term))
        total = production + term
        age = self.valuation.age(bbr) if bbr else None
        if age is None and player.get("date_of_birth"):
            from .valuation import age_on
            age = age_on(player["date_of_birth"], self.on)
        relief = 0.0
        if for_club and years == 1 and self.payroll(for_club) and self.payroll(for_club) > self.tax_line:
            relief = EXPIRING_RELIEF_PER_5M * salary / 5000000
        total += relief
        if total < 0:
            total *= NEGATIVE_SHARE
        return {"player": player["player"], "bbr_id": bbr, "value": round(total, 3), "production": round(production, 3),
                "contract_term": round(term, 3), "relief": round(relief, 3), "salary": salary, "years": years,
                "age": age, "basis": basis}

    def pick_value(self, pick, owner_record_club, miami_own=False):
        """A draft pick from the chart, placed by the owning club's last record and regressed for later years."""
        if pick["round"] == 2:
            return {"value": SECOND_ROUND_VALUE, "slot": None, "basis": "second-round pick"}
        wins = self.standings.get(owner_record_club, {}).get("wins", 41)
        order = sorted(self.standings.values(), key=lambda r: r["wins"])
        slot = 1 + sum(1 for r in order if r["wins"] < wins)      # worst record picks first (lottery ignored)
        years_out = max(0, pick["year"] - 2004)
        slot = 15 + (slot - 15) * FUTURE_PICK_REGRESSION ** years_out
        if miami_own:
            slot += MIAMI_PICK_PESSIMISM
        slot = max(1, min(29, slot))
        value = TOP_PICK_VALUE * math.exp(-PICK_DECAY * (slot - 1))
        return {"value": round(value, 3), "slot": round(slot, 1), "basis": f"{owner_record_club} {wins} wins in 2002-03; {pick['year']} first regressed {years_out} year(s)"}

    @staticmethod
    def premium(values):
        """Sum with the star premium: every asset above 1 is raised to STAR_EXPONENT first."""
        return sum(v ** STAR_EXPONENT if v > 1 else v for v in values)

    @staticmethod
    def effective(values):
        """The premium sum brought back to the scale of one asset (its STAR_EXPONENT-th root), so a
        package is compared as the single player it would be worth: two 2s make about a 2.2, not a 4."""
        total = Assets.premium(values)
        return total ** (1 / STAR_EXPONENT) if total > 1 else total


# -- legality ------------------------------------------------------------------------------------
def months_after(day, months):
    d = date.fromisoformat(day)
    month = d.month - 1 + months
    return date(d.year + month // 12, month % 12 + 1, min(d.day, 28)).isoformat()


class TradeDesk:
    """Legality and acceptance of a proposal between Miami and one real club on a date."""

    def __init__(self, on, front_office, root=ROOT):
        self.on, self.fo, self.root = on, front_office, Path(root)
        self.market = front_office.market
        self.assets = Assets(on, self.market, root)
        self.cba = read_json(CBA_PATH, root)
        self.cap = self.market.planning_cap(on)
        self.signings = {r["bbr_id"]: r for r in read_json(TRANSACTIONS_PATH, root)["signings"]
                         if r.get("bbr_id") and r["kind"] in ("signing", "re_sign", "sign_and_trade", "match", "match_declined", "rookie_signing")
                         and r["to"] != MIAMI and r["date"] <= on}
        self.picks = read_json(PICKS_PATH, root) if (self.root / PICKS_PATH).exists() else {"picks": []}

    # -- lookups ------------------------------------------------------------------------------
    def miami_player(self, name):
        """Miami's sheet entry (with the register's bbr_id, which the sheet may lack) and register entry."""
        p = next((p for p in self.fo.sheet["players"] if p["player"] == name), None)
        r = next((r for r in self.fo.roster["players"] if r["name"] == name), None)
        if p is not None and r is not None:
            p = dict(p, bbr_id=p.get("bbr_id") or r.get("bbr_id"), date_of_birth=r.get("date_of_birth"))
        return p, r

    def partner_player(self, club, name):
        entry = self.assets.contracts.get(club)
        if not entry:
            return None
        return next((p for p in entry["players"] if p["player"] == name), None)

    def miami_tradeable(self):
        """Miami players under contract who may be traded on the date, with the rule that blocks the others."""
        out = []
        for entry in self.fo.sheet["players"]:
            p, r = self.miami_player(entry["player"])
            if not r or not p["schedule"].get(SEASON) or p["status"] in ("renounced", "released", "traded", "signed_elsewhere"):
                continue
            if any(w in p["status"] for w in ("free_agent", "declined", "pending", "unsigned", "draft")):
                continue
            block = self.blocked(p)
            if not block:
                out.append(p)
        return out

    def blocked(self, player):
        """Why a player cannot be traded on the date (newly signed, signed first-round pick, Wade)."""
        if player["player"] == PROTAGONIST:
            return "Wade's trade would change the simulated club (AGENTS.md); not supported"
        signed = player.get("signed_date")
        if signed and signed >= "2003-07-01":
            rule = self.cba["trades"]
            if player.get("route") == "rookie_scale":
                until = (date.fromisoformat(signed) + timedelta(days=rule["signed_first_round_pick_restriction_days"]["days"])).isoformat()
                if self.on < until:
                    return f"signed first-round pick: not tradable until {until} ({rule['signed_first_round_pick_restriction_days']['status']})"
            else:
                until = max(months_after(signed, 3), "2003-12-15")
                if self.on < until:
                    return f"newly signed: not tradable until {until} ({rule['newly_signed_free_agent_restriction']['status']})"
        return None

    def partner_blocked(self, club, player):
        row = self.signings.get(player.get("bbr_id"))
        if row and row["date"] >= "2003-07-01":
            until = max(months_after(row["date"], 3), "2003-12-15")
            if self.on < until:
                return f"newly signed on {row['date']}: not tradable until {until}"
        return None

    def matching_salary(self, player, outgoing_from_miami):
        """Salary for matching: base-year compensation for a Bird or Early Bird re-signing at a raise over 20%."""
        salary = self.assets.salary(player)
        if outgoing_from_miami and player.get("route") in ("bird", "early_bird"):
            prior = (player.get("prior_season_salary") or {}).get("amount") or player.get("previous_salary")
            if prior and salary > prior * 1.2:
                return max(salary * 0.5, prior), "base-year compensation (inferred for 1999)"
        return salary, None

    # -- legality ------------------------------------------------------------------------------
    def errors(self, trade):
        """Everything that makes the proposal illegal on the date, each naming its rule."""
        errors, rules = [], self.cba["trades"]
        deadline = rules["deadline_2003_04"][:10]
        if self.on > deadline:
            errors.append(f"after the {deadline} trade deadline")
        if MORATORIUM[0] <= self.on <= MORATORIUM[1]:
            errors.append("no trade during the July moratorium (calendar)")
        club = trade["partner"]
        if club == MIAMI or club not in self.assets.contracts:
            errors.append(f"unknown partner club {club!r}")
            return errors
        out_salary = in_salary = 0.0
        byc_notes = []
        for name in trade.get("miami_out", []):
            p, r = self.miami_player(name)
            if not p or not r:
                errors.append(f"{name} is not on Miami's register")
                continue
            if any(w in p["status"] for w in ("free_agent", "declined", "pending", "renounced", "traded", "signed_elsewhere", "unsigned", "draft")):
                errors.append(f"{name}: a {p['status']} player cannot be traded (a sign-and-trade is not modeled)")
                continue
            block = self.blocked(p)
            if block:
                errors.append(f"{name}: {block}")
            salary, note = self.matching_salary(p, True)
            out_salary += salary
            if note:
                byc_notes.append(f"{name}: {note}")
        for name in trade.get("miami_in", []):
            p = self.partner_player(club, name)
            if not p or p["status"] not in ("under_contract", "under_rookie_contract", "under_contract_unverified", "minimum_contract_unverified"):
                errors.append(f"{name} is not under contract with {club} on the inventory")
                continue
            block = self.partner_blocked(club, p)
            if block:
                errors.append(f"{name}: {block}")
            in_salary += self.assets.salary(p)
        cash_out, cash_in = trade.get("cash_out", 0) or 0, trade.get("cash_in", 0) or 0
        if max(cash_out, cash_in) > rules["cash_per_season_max"]["amount"]:
            errors.append(f"cash above ${rules['cash_per_season_max']['amount']:,} a season ({rules['cash_per_season_max']['status']})")
        # Salary matching for a club over the cap after the trade (115% + $100,000, reported for 1999).
        pct, plus = rules["matching_over_cap"]["incoming_max_percent_of_outgoing"] / 100, rules["matching_over_cap"]["plus_dollars"]
        room = self.fo.cap_room()
        miami_after = room["committed"] + room["holds"] - out_salary + in_salary
        if miami_after > self.cap and in_salary > out_salary * pct + plus:
            errors.append(f"Miami over the cap after the trade: incoming ${in_salary:,.0f} exceeds {pct:.0%} of outgoing ${out_salary:,.0f} plus ${plus:,} "
                          f"({rules['matching_over_cap']['status']})" + (f"; {'; '.join(byc_notes)}" if byc_notes else ""))
        partner_payroll = self.assets.payroll(club)
        partner_after = partner_payroll - in_salary + out_salary
        if partner_after > self.cap and out_salary > in_salary * pct + plus:
            errors.append(f"{club} over the cap after the trade: incoming ${out_salary:,.0f} exceeds {pct:.0%} of its outgoing ${in_salary:,.0f} plus ${plus:,}")
        # Rosters of at most 15 after the trade (Miami; the partner's count is not on the inventory for the date).
        active = sum(1 for r in self.fo.roster["players"] if not any(w in r["status"] for w in ("free_agent", "renounced", "released", "traded", "signed_elsewhere", "declined", "pending")))
        if active - len(trade.get("miami_out", [])) + len(trade.get("miami_in", [])) > rules["roster_max_after_trade"]:
            errors.append(f"Miami would carry more than {rules['roster_max_after_trade']} players")
        # Picks: ownership and the Stepien rule.
        owned = {(p["year"], p["round"]) for p in self.picks.get("picks", []) if p.get("owned")}
        for pick in trade.get("picks_out", []):
            if (pick["year"], pick["round"]) not in owned:
                errors.append(f"Miami does not own its {pick['year']} round-{pick['round']} pick on the record (Finances/draft_picks.json)")
        firsts_after = sorted(y for (y, r) in owned if r == 1) 
        firsts_after = [y for y in firsts_after if {"year": y, "round": 1} not in trade.get("picks_out", [])]
        years = [p["year"] for p in self.picks.get("picks", []) if p["round"] == 1]
        for y in range(min(years, default=2004), max(years, default=2004)):
            if y not in firsts_after and y + 1 not in firsts_after and (y, 1) in owned | {(p["year"], 1) for p in trade.get("picks_out", [])}:
                errors.append(f"Stepien rule: Miami would lack a first-round pick in {y} and {y + 1} ({rules['stepien_rule']})")
                break
        return errors

    # -- values and acceptance ----------------------------------------------------------------
    def valuation(self, trade):
        """Each side's value before and after, with the posture multipliers of the partner."""
        club = trade["partner"]
        posture = self.assets.posture(club)
        mult = POSTURE[posture]
        miami_out = [self.assets.player_value(self.miami_player(n)[0], for_club=club) for n in trade.get("miami_out", [])]
        miami_in = [self.assets.player_value(self.partner_player(club, n), for_club=MIAMI) for n in trade.get("miami_in", [])]
        picks_out = [dict(self.assets.pick_value(p, MIAMI, miami_own=True), pick=p) for p in trade.get("picks_out", [])]
        picks_in = [dict(self.assets.pick_value(p, club), pick=p) for p in trade.get("picks_in", [])]

        def partner_view(players, picks):
            vals = []
            for v in players:
                factor = mult["old_players"] if (v["age"] or 0) >= OLD_AGE else mult["players"]
                vals.append(max(0.0, v["value"]) * factor if v["value"] > 0 else v["value"])
            vals += [p["value"] * mult["picks"] for p in picks]
            return Assets.effective(vals)

        def miami_view(players, picks):
            needs = self.fo.needs()
            vals = []
            for v in players:
                pos = self.assets.positions.get(v["bbr_id"], (None, "SF", 9))[1].split("-")[0]
                fit = self.fo.fit(pos, needs)
                vals.append(v["value"] * (0.75 + 0.5 * fit) if v["value"] > 0 else v["value"])
            vals += [p["value"] for p in picks]
            return Assets.effective(vals)

        # Relative change of the effective values, so a star-for-prospects deal and a swap of reserves sit on one scale.
        def relative(after, before):
            return (after - before) / max(after, before, 1.0)

        partner_gain = relative(partner_view(miami_out, picks_out), partner_view(miami_in, picks_in))
        miami_gain = relative(miami_view(miami_in, picks_in), miami_view(miami_out, picks_out))
        return {"partner": club, "posture": posture, "miami_out": miami_out, "miami_in": miami_in, "picks_out": picks_out,
                "picks_in": picks_in, "partner_gain": round(partner_gain, 3), "miami_gain": round(miami_gain, 3)}

    def fits_partner(self, trade):
        """The partner has minutes for the arriving positions (at most two incumbents at depth 1-2 there)
        and is not left without a depth-1 or depth-2 player at a position it empties."""
        club = trade["partner"]
        leaving = {self.partner_player(club, n).get("bbr_id") for n in trade.get("miami_in", []) if self.partner_player(club, n)}
        arriving_positions = {self.assets.positions.get(self.miami_player(n)[0].get("bbr_id"), (None, "SF", 9))[1].split("-")[0]
                              for n in trade.get("miami_out", []) if self.miami_player(n)[0]}
        for bbr in leaving:
            c, position, depth = self.assets.positions.get(bbr, (None, "SF", 9))
            pos = position.split("-")[0]
            if depth <= 2 and pos not in arriving_positions:
                left = sum(1 for b, (cc, pp, d) in self.assets.positions.items() if cc == club and pp.split("-")[0] == pos and d <= 2 and b not in leaving)
                if left == 0:
                    return False
        for name in trade.get("miami_out", []):
            p = self.miami_player(name)[0]
            pos = self.assets.positions.get(p.get("bbr_id"), (None, "SF", 9))[1].split("-")[0]
            incumbents = sum(1 for b, (c, position, depth) in self.assets.positions.items()
                             if c == club and position.split("-")[0] == pos and depth <= 2 and b not in {self.partner_player(club, n).get("bbr_id") for n in trade.get("miami_in", [])})
            if incumbents >= 3:
                return False
        return True

    def trade_id(self, trade):
        key = json.dumps({k: trade.get(k) for k in ("partner", "miami_out", "miami_in", "picks_out", "picks_in", "cash_out", "cash_in")}, sort_keys=True)
        return f"{self.on}-{hashlib.sha256(key.encode()).hexdigest()[:10]}"

    def acceptance_packet(self, trade):
        """The partner's answer as a decision packet, or None with the reasons when it cannot be asked."""
        errors = self.errors(trade)
        if errors:
            return None, errors
        if not self.fits_partner(trade):
            return None, [f"{trade['partner']} has no minutes at the arriving positions"]
        v = self.valuation(trade)
        p = 1 / (1 + math.exp(-ACCEPT_SLOPE * max(-10.0, min(10.0, v["partner_gain"]))))
        p = round(min(ACCEPT_LIMITS[1], max(ACCEPT_LIMITS[0], p)), 3)
        outs = ", ".join(trade.get("miami_out", []) + [f"{x['year']} round {x['round']}" for x in trade.get("picks_out", [])]) or "nothing"
        ins = ", ".join(trade.get("miami_in", []) + [f"{x['year']} round {x['round']}" for x in trade.get("picks_in", [])]) or "nothing"
        return {"event_id": f"trade-{self.trade_id(trade)}", "date": self.on,
                "question": f"Does {trade['partner']} accept Miami's proposal: {outs} for {ins}?",
                "decider": f"{trade['partner']} (real club, drawn by rule)", "options": {"accept": p, "decline": round(1 - p, 3)},
                "basis": (f"{trade['partner']} posture {v['posture']} (2002-03 record); its relative value change {v['partner_gain']:+.3f} "
                          f"(star premium {STAR_EXPONENT}, pick chart, contract terms); logistic slope {ACCEPT_SLOPE} kept inside {ACCEPT_LIMITS}. "
                          f"Miami's own gain {v['miami_gain']:+.3f}.")}, v

    # -- Miami's search ----------------------------------------------------------------------
    def search(self, requests=(), standing="unsigned_rookie", limit=10):
        """Proposals Miami's front office would make: legal, likely to be accepted, and a gain for Miami."""
        from .gm import STANDING_WEIGHT
        needs = self.fo.needs()
        need_positions = [pos for pos, n in needs.items() if n["minutes_short"] > 0 or n["quality_gap"] >= 0.3]
        wanted = {r["player"] for r in requests if r.get("subject") == "trade_target"}
        opposed = {r["player"] for r in requests if r.get("subject") == "trade_opposed"}
        tradeable = [p for p in self.miami_tradeable()]
        combos = [[p["player"]] for p in tradeable] + [[a["player"], b["player"]] for i, a in enumerate(tradeable) for b in tradeable[i + 1:]]
        found = []
        for club, entry in self.assets.contracts.items():
            if club == MIAMI:
                continue
            candidates = []
            for p in entry["players"]:
                if p["status"] not in ("under_contract", "under_rookie_contract", "under_contract_unverified") or not p.get("bbr_id"):
                    continue
                pos = self.assets.positions.get(p["bbr_id"], (None, "SF", 9))[1].split("-")[0]
                value = self.assets.player_value(p, for_club=MIAMI)
                if (pos in need_positions and value["production"] >= 0.5) or p["player"] in wanted:
                    candidates.append(p["player"])
            for name in candidates[:8]:
                for outs in combos:
                    trade = {"partner": club, "miami_out": outs, "miami_in": [name], "picks_out": [], "picks_in": []}
                    packet, v = self.acceptance_packet(trade)
                    if packet is None:
                        continue
                    gain = v["miami_gain"]
                    if name in wanted:
                        gain *= 1 + STANDING_WEIGHT[standing]
                    if any(o in opposed for o in outs):
                        gain *= 1 - STANDING_WEIGHT[standing]
                    if gain < SEARCH_MIN_GAIN:
                        continue
                    found.append({"trade": trade, "miami_gain": round(gain, 3), "partner_gain": v["partner_gain"],
                                  "accept": packet["options"]["accept"], "score": round(gain * packet["options"]["accept"], 3),
                                  "wade_request": name in wanted or any(o in opposed for o in outs)})
        found.sort(key=lambda f: -f["score"])
        return found[:limit]
