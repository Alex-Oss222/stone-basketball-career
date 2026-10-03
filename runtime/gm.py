"""Miami's front office in free agency (docs/front_office_design.md, section 5).

Reads only Miami's own records and evidence dated on or before the career date:
the cap sheet, the rights file, the holdings, the depth chart, the owner's budget
and the market's asking prices. Writes nothing; the free-agency driver writes
the plan, the offers and the decisions it produces.

Every constant is a judgement constant, named here.
"""
import json
from pathlib import Path

from .standing import STANDING_WEIGHT
from .trades import SIGN_AND_TRADE_RIGHTS
from .valuation import read

ROOT = Path(__file__).resolve().parents[1]
SEASON = "2003-04"
MIAMI = "Miami Heat"
TEAM = Path(f"career/Dwyane_Wade/{SEASON}/00_Team")
POSITIONS = ("PG", "SG", "SF", "PF", "C")
ROTATION_MINUTES = {"PG": 48, "SG": 48, "SF": 48, "PF": 48, "C": 48}   # a full rotation covers 48 at each spot
STARTER_MINUTES = 32
ROSTER_CHARGE_SPOTS = 12                 # cap charge for empty roster spots below this count (minimum salary each)
OPEN_SHARE, CONCESSION_STEPS = 0.875, (0.925, 0.975, 1.0)   # open at 87.5% of the ask, then concede toward the valuation
WALK_AWAY_OVER_VALUATION = 1.10          # never go past 110% of Miami's own valuation
MAX_ROUNDS = 3
RAISE = {"bird": 0.125, "other": 0.10}
AVERAGE_VALUE = 9.0                      # league-average production value (efficiency per game) for the gap term
ROOKIE_VALUE_SHARE = 0.7                 # a first-round rookie counts at this share of average until he has played
ROOM_OVER_RIGHTS_SCORE = 20.0                # a target this good is worth renouncing cheap rights for
REPLACEMENT_VALUE, STAR_EXPONENT = 5.0, 1.5   # target score: (value above replacement)^1.5 per mid-level of ask
MATCH_SURPLUS_SLOPE, MATCH_OVER_TAX_FACTOR = 2.5, 0.3   # a real incumbent matching an offer sheet (design 4.5)
ROLE_CEILING_SHARE = {"starter": None, "rotation": 1.0, "reserve": 0.3}   # of the mid-level: what a role is worth to Miami
HOLD_KEEP_FACTOR = 1.5                   # keep a free agent's rights while his hold is under this times his valuation
SIGN_AND_TRADE_MIN_SCORE = 20.0          # a target worth a sign-and-trade package scores at least ROOM_OVER_RIGHTS_SCORE
RESIGN_AND_TRADE_FIT = 0.6               # Miami signs-and-trades an agreed own free agent only when his position fit is below this (run_free_agency shop_own, run_trade --shop)


class FrontOffice:
    def __init__(self, on, market, root=ROOT):
        self.on, self.market, self.root = on, market, Path(root)
        self.valuation = market.valuation
        self.config = read(TEAM / "team_config.json", root)
        self.sheet = read(TEAM / "Finances/contract_schedules.json", root)
        self.rights = read(TEAM / "Finances/free_agent_rights.json", root)
        self.roster = read(TEAM / "Team/Roster/roster.json", root)
        self.depth = read(TEAM / "Team/Depth_Chart/depth_chart.json", root)
        self.budget = self.config.get("budget", {})

    # -- ledger --------------------------------------------------------------------------------
    def committed(self):
        """Salary and holds Miami carries for the season on this date (options as decided)."""
        total, rows = 0, []
        for p in self.sheet["players"]:
            amount, kind = p["schedule"].get(SEASON), p["amount_kind"].get(SEASON)
            status = p["status"]
            if amount is None:
                continue
            if status in ("team_option_declined", "player_option_declined", "renounced", "released", "traded", "signed_elsewhere"):
                continue
            if status in ("team_option_pending", "player_option_pending") and self.on >= "2003-07-01":
                continue   # June 30 decisions must have resolved these; a pending one past June 30 is not counted
            total += amount
            rows.append((p["player"], amount, kind, status))
        return total, rows

    def holds(self):
        """Cap holds of unrenounced free agents (rights file), priced where the file prices them."""
        total, rows = 0, []
        for p in self.rights["players"]:
            if p.get("renounced") or p.get("signed_elsewhere") or p.get("re_signed"):
                continue
            hold = p.get("cap_hold")
            if hold:
                total += hold
                rows.append((p["player"], hold, p["bird_status"]))
        return total, rows

    def cap_room(self, renounce=()):
        cap = self.market.planning_cap(self.on)
        committed, _ = self.committed()
        holds = sum(h for name, h, _ in self.holds()[1] if name not in renounce)
        counted = sum(1 for p in self.sheet["players"] if p["status"] not in ("renounced", "released", "traded", "signed_elsewhere", "team_option_declined", "player_option_declined") and p["schedule"].get(SEASON))
        charge = max(0, ROSTER_CHARGE_SPOTS - counted) * self.valuation.minimum(0)
        return {"cap": cap, "cap_known": self.market.cap_known(self.on), "committed": committed, "holds": holds,
                "roster_charge": charge, "room": cap - committed - holds - charge}

    def exceptions(self):
        return {"mid_level": self.valuation.mid_level, "million": 1500000, "minimum": self.valuation.minimum(0)}

    def payroll_ceiling(self):
        return self.budget.get("payroll_ceiling", 57000000)

    # -- needs ---------------------------------------------------------------------------------
    def roster_values(self):
        """Production value of each player Miami holds for the season, at his first listed position."""
        out = {}
        for p in self.roster["players"]:
            status = p["status"]
            if any(w in status for w in ("expiring", "free_agent", "renounced", "released", "traded", "signed_elsewhere", "declined")):
                continue                     # a free agent is not under Miami's control until he re-signs
            if "option_pending" in status and self.on >= "2003-07-01":
                continue   # resolved on June 30; the register must say which way
            bbr = p.get("bbr_id")
            value = self.valuation.value(bbr) if bbr else None
            if value is None and "draft_rights" in status:
                value = AVERAGE_VALUE * ROOKIE_VALUE_SHARE
            out[p["name"]] = {"position": p["positions"][0], "positions": p["positions"], "value": value or 0.0, "status": status}
        return out

    def needs(self):
        """Minutes short and quality gap at each position from the players Miami holds.

        Each player counts at his first listed position. A starter covers 32 minutes, the next
        player 16; the gap is how far the best player falls short of league-average production."""
        held = self.roster_values()
        needs = {}
        for pos in POSITIONS:
            players = sorted((v for v in held.values() if v["position"] == pos), key=lambda v: -v["value"])
            covered = min(ROTATION_MINUTES[pos], STARTER_MINUTES * len(players[:1]) + 16 * len(players[1:2]))
            best = players[0]["value"] if players else 0.0
            gap = max(0.0, AVERAGE_VALUE - best) / AVERAGE_VALUE
            needs[pos] = {"minutes_short": ROTATION_MINUTES[pos] - covered, "quality_gap": round(gap, 2),
                          "incumbents": [n for n, v in held.items() if v["position"] == pos][:3]}
        return needs

    def fit(self, position, needs):
        n = needs.get(position, {"minutes_short": 0, "quality_gap": 0})
        return round(0.5 + 0.5 * min(1.0, n["minutes_short"] / 48) + 0.5 * n["quality_gap"], 3)

    # -- plan ----------------------------------------------------------------------------------
    def valuation_of(self, bbr_id):
        """What Miami would pay per season: the comparables price of his production, no pressure."""
        p = self.market.players.get(bbr_id)
        if not p:
            return None
        return self.valuation.price(bbr_id, p.get("nba_seasons_before_2003_04"), p.get("prior_salary_2002_03"))

    def targets(self, requests=(), standing="unsigned_rookie", limit=12):
        """Ranked free agents: surplus (Miami's valuation minus the ask) times fit, plus Wade's requests."""
        needs = self.needs()
        positions = self._positions()
        rows = []
        for bbr, p in self.market.pool(self.on).items():
            if p["club"] == "Miami Heat":
                continue
            own = self.valuation_of(bbr)
            if own is None:
                continue
            ask = self.market.asking(bbr, self.on)
            pos = positions.get(bbr, "SF")
            surplus = (own - ask["first_year"]) / max(ask["first_year"], 1)
            weight = self.fit(pos, needs)
            # Contribution above replacement per dollar, with a star premium (quality^1.5): one star
            # is worth more than two role players, and a cheap ask helps but cannot make a bad player good.
            above = max(0.0, (self.valuation.value(bbr) or 0) - REPLACEMENT_VALUE)
            score = weight * above ** STAR_EXPONENT / max(0.25, ask["first_year"] / self.valuation.mid_level)
            wish = next((r for r in requests if r.get("subject") == "free_agent_target" and r.get("player") == p["player"]), None)
            if wish:
                score *= 1 + STANDING_WEIGHT[standing]
            rows.append({"bbr_id": bbr, "player": p["player"], "club": p["club"], "position": pos, "age": self.valuation.age(bbr),
                         "value": round(self.valuation.value(bbr) or 0, 1), "valuation": own, "ask": ask["first_year"],
                         "years_asked": ask["years"], "surplus": round(surplus, 3), "fit": weight, "score": round(score, 3),
                         "wade_request": bool(wish), "rfa": bool(p.get("rfa_eligible")), "bird_class": p.get("bird_class")})
        rows.sort(key=lambda r: -r["score"])
        return rows[:limit]

    def _positions(self):
        """bbr_id -> listed position from the end-of-season roster file, then the league registry."""
        out = {}
        for club in read("library/2003/league/nba_2003_end_of_season.json", self.root)["clubs"].values():
            for p in club["players"]:
                if p.get("bbr_id") and p.get("position"):
                    out[p["bbr_id"]] = p["position"].split("-")[0].split("/")[0]
        for p in read("career/Dwyane_Wade/Stats_and_Awards/League/player_registry.json", self.root)["players"]:
            if p.get("bbr_id") and p.get("position"):
                out.setdefault(p["bbr_id"], p["position"].split("-")[0].split("/")[0])
        return out

    def keep_holds(self):
        """Own free agents Miami would rather keep the rights to: hold at or under what Miami would pay."""
        rights = {p["player"]: p for p in self.rights["players"]}
        keep, drop = [], []
        for name, hold, status in self.holds()[1]:
            bbr = rights[name].get("bbr_id")
            own = self.valuation_of(bbr) if bbr else None
            (keep if own is not None and hold <= own * HOLD_KEEP_FACTOR else drop).append(
                {"player": name, "hold": hold, "valuation": own, "bird_status": status,
                 "reason": ("hold is within what Miami would pay; rights worth keeping" if own is not None and hold <= own * HOLD_KEEP_FACTOR
                            else "hold exceeds what Miami would pay" if own else "no 2002-03 evidence; hold exceeds any offer Miami would make")})
        return keep, drop

    def plan(self, requests=(), standing="unsigned_rookie"):
        """Miami's plan on the date: holds to renounce, room-first targets, then re-signings with Bird rights.

        Potential room counts every hold Miami would not keep as renounced; a renouncement is written only
        when a signing needs the room. Targets are taken greedily by score while their ask fits; one
        mid-level target is allowed once the room is used. Own free agents whose rights Miami keeps are
        re-signing candidates afterwards, over the cap with Bird rights where they apply.
        """
        keep, drop = self.keep_holds()
        room = self.cap_room(renounce=tuple(r["player"] for r in drop))
        budget_room = min(room["room"], self.payroll_ceiling() - room["committed"] - room["holds"])
        chosen, remaining = [], budget_room
        spare = sorted(keep, key=lambda k: k["valuation"])      # rights Miami would give up for room, cheapest first
        renounced_for_room = []
        probes = []
        for t in self.targets(requests, standing, limit=40):
            role_cap = self.role_ceiling(t["position"])
            if role_cap is not None and t["ask"] > role_cap * WALK_AWAY_OVER_VALUATION:
                continue                     # Miami will not pay a reserve's or rotation player's ask above the role's worth
            if t["ask"] <= remaining:
                chosen.append(dict(t, route="room"))
                remaining -= t["ask"]
            elif t["ask"] <= remaining + sum(k["hold"] for k in spare) and t["score"] >= ROOM_OVER_RIGHTS_SCORE:
                needed = t["ask"] - remaining
                while needed > 0 and spare:
                    k = spare.pop(0)
                    renounced_for_room.append(dict(k, renounced_for=t["player"]))
                    remaining += k["hold"]
                    needed -= k["hold"]
                chosen.append(dict(t, route="room"))
                remaining -= t["ask"]
            elif remaining < self.valuation.mid_level and t["ask"] <= self.valuation.mid_level and not any(c["route"] == "mid_level" for c in chosen):
                chosen.append(dict(t, route="mid_level"))
            elif (t["bird_class"] in SIGN_AND_TRADE_RIGHTS and not t["rfa"] and t["score"] >= SIGN_AND_TRADE_MIN_SCORE
                  and not any(c["route"] == "sign_and_trade" for c in chosen) and not any(pr["player"] == t["player"] for pr in probes)):
                # A target beyond the room and the exceptions whose incumbent holds his full Bird rights: Miami can only
                # reach him by sign-and-trade. The probe is two-sided and read-only (runtime/trades.py); one per plan.
                from .trades import TradeDesk
                ok, why = TradeDesk(self.on, self, self.root).sign_and_trade_feasible(t)
                probes.append({"player": t["player"], "bbr_id": t["bbr_id"], "club": t["club"], "ask": t["ask"], "score": t["score"],
                               "sign_and_trade_feasible": ok, "binding_constraint": why})
                if ok:
                    chosen.append(dict(t, route="sign_and_trade", sign_and_trade_feasible=ok, binding_constraint=why))
            if len(chosen) >= 4:
                break
        keep = [k for k in keep if k["player"] not in {r["player"] for r in renounced_for_room}]
        drop = drop + renounced_for_room
        chosen_names = {c["player"] for c in chosen}
        review = []
        for r in requests:
            if r.get("subject") != "free_agent_target":
                continue
            t = next((x for x in self.targets(requests, standing, limit=200) if x["player"] == r["player"]), None)
            if r["player"] in chosen_names:
                review.append({"player": r["player"], "outcome": "pursued", "reason": "in the plan's targets"})
            elif t is None:
                review.append({"player": r["player"], "outcome": "not pursued", "reason": "not on the market on this date or no 2002-03 evidence to price"})
            elif any(pr["player"] == r["player"] and not pr["sign_and_trade_feasible"] for pr in probes):
                why = next(pr["binding_constraint"] for pr in probes if pr["player"] == r["player"])
                review.append({"player": r["player"], "outcome": "not pursued", "reason": f"fits only through a sign-and-trade, and no package is legal: {why}"})
            else:
                review.append({"player": r["player"], "outcome": "not pursued", "reason": f"ask ${t['ask']:,} does not fit the room (${remaining:,} left) or the exceptions; score {t['score']}"})
        rights = {p["player"]: p for p in self.rights["players"]}
        re_sign = [{"player": k["player"], "bbr_id": rights[k["player"]].get("bbr_id"), "route": k["bird_status"],
                    "valuation": k["valuation"], "hold": k["hold"]} for k in keep]
        return {"date": self.on, "cap_room": room, "payroll_ceiling": self.payroll_ceiling(),
                "renounce_when_needed": drop, "keep_rights": keep, "needs": self.needs(),
                "targets": chosen, "room_after_targets": remaining, "re_sign_candidates": re_sign, "wade_requests": review,
                "sign_and_trade_probes": probes}

    # -- offers ----------------------------------------------------------------------------
    def role_for(self, position, needs=None):
        """The role Miami can honestly offer at a position: starter minutes where the spot is open."""
        n = (needs or self.needs()).get(position, {"minutes_short": 0, "quality_gap": 0})
        if n["minutes_short"] >= STARTER_MINUTES or n["quality_gap"] >= 0.3:
            return {"role": "starter", "minutes_per_game": STARTER_MINUTES}
        if n["minutes_short"] > 0:
            return {"role": "rotation", "minutes_per_game": 20}
        return {"role": "reserve", "minutes_per_game": 12}

    def role_ceiling(self, position, needs=None):
        """The most Miami pays for the role a position offers (judgement): a reserve is not paid like a starter."""
        share = ROLE_CEILING_SHARE[self.role_for(position, needs)["role"]]
        return None if share is None else int(round(share * self.valuation.mid_level))

    def route_ceiling(self, route, bbr_id):
        """The first-year salary a signing route allows (1999 rules, as `cba.terms_errors` checks them)."""
        p = self.market.players.get(bbr_id, {})
        prior, service = p.get("prior_salary_2002_03") or 0, p.get("nba_seasons_before_2003_04")
        minimum = self.valuation.minimum(service)
        if route == "non_bird":
            return max(round(prior * 1.2), round(minimum * 1.2))
        if route == "early_bird":
            return max(round(prior * 1.75), self.valuation.mid_level)
        if route == "mid_level":
            return self.valuation.mid_level
        if route == "million":
            return 1500000
        if route == "minimum":
            return minimum
        if route == "sign_and_trade":
            return self.valuation.maximum(service, prior or None)   # signed by the incumbent with full Bird rights
        return None

    def resign_and_trade(self, bbr_id, position):
        """Whether Miami would shop an agreed own free agent as a sign-and-trade instead of simply re-signing him:
        his position fit is below RESIGN_AND_TRADE_FIT (judgement; the free-agency driver's shop_own and run_trade --shop)."""
        return self.fit(position, self.needs()) < RESIGN_AND_TRADE_FIT

    def offer_terms(self, target, round_no, counter=None, route="room", restricted=False):
        """Miami's offer in a round, or None when Miami walks away (docs/front_office_design.md 5.5).

        Round 1 opens at OPEN_SHARE of the ask, never above Miami's valuation, one season short of the
        years asked. Later rounds concede toward the player's counter in CONCESSION_STEPS of the gap,
        never past WALK_AWAY_OVER_VALUATION times the valuation; a counter beyond that ends the talks.
        Raises follow the route (Bird 12.5%, otherwise 10%); the mid-level route starts at the exception.
        """
        ask, own = target["ask"], target["valuation"]
        ceiling = own * WALK_AWAY_OVER_VALUATION
        role_cap = self.role_ceiling(target["position"])
        if role_cap is not None:
            ceiling = min(ceiling, role_cap)
            own = min(own, role_cap)
        route_cap = self.route_ceiling(route, target.get("bbr_id"))
        if route_cap is not None:
            ceiling = min(ceiling, route_cap)
        if round_no > MAX_ROUNDS or (counter is not None and counter > ceiling):
            return None
        if round_no == 1:
            first = min(OPEN_SHARE * ask, own, ceiling)
        else:
            goal = min(counter if counter is not None else ask, ceiling)
            previous = target.get("last_offer", OPEN_SHARE * ask)
            first = previous + (goal - previous) * CONCESSION_STEPS[min(round_no - 2, len(CONCESSION_STEPS) - 1)]
            first = min(first, ceiling)
        first = int(round(first))
        years = max(1, target["years_asked"] - (1 if round_no == 1 else 0))
        if restricted:
            years = max(3, years)            # an offer sheet needs three seasons (1999 rules)
        if route in ("mid_level", "non_bird", "early_bird"):
            years = min(years, 6)
        if route == "million":
            years = min(years, 2)
        if route == "sign_and_trade":
            years = min(max(3, years), 7)    # at least three non-option seasons, at most the Bird length (1999 rules)
        raise_share = RAISE["bird" if route in ("bird", "early_bird", "sign_and_trade") else "other"]
        schedule = [int(round(first * (1 + raise_share * i))) for i in range(years)]
        last_guaranteed = not (years >= 4 and round_no == 1)
        guaranteed = sum(schedule) if last_guaranteed else sum(schedule[:-1])
        return {"first_year": first, "years": years, "schedule": schedule, "guaranteed": guaranteed,
                "raise_percent": raise_share * 100, "last_year_guaranteed": last_guaranteed, "round": round_no,
                "promise": self.role_for(target["position"]),
                "basis": (f"round {round_no}: ask ${ask:,}, Miami's valuation ${own:,}, ceiling ${int(ceiling):,}"
                          + (f", counter ${counter:,}" if counter else ""))}

    def context_for(self, target):
        """What the player weighs about Miami: role, strength and location (docs/front_office_design.md 4.3)."""
        role = self.role_for(target["position"])
        wins = self.config.get("projection", {}).get("wins", 30)
        return {"club": MIAMI, "role_minutes": role["minutes_per_game"], "strength": wins,
                "location": self.config.get("location_appeal", 0.6), "ask": target["ask"]}

    def match_packet(self, target, terms, window):
        """Decision packet for a real incumbent's answer to Miami's offer sheet (design 4.5).

        The incumbent matches by money: likely when the sheet is at or under what the production is
        worth (the comparables price) and its payroll after matching stays under the tax projection.
        """
        from .contracts import club_ledger
        payroll = club_ledger(target["club"], SEASON, self.root)["known_total"]
        tax_line = read("library/2003/league/nba_2003_04_cap_rules.json", self.root).get("luxury_tax_line_projection_july_2003", 57000000)
        surplus = (target["valuation"] - terms["first_year"]) / max(terms["first_year"], 1)
        p = 0.5 + MATCH_SURPLUS_SLOPE * surplus
        over_tax = payroll + terms["first_year"] > tax_line
        if over_tax:
            p *= MATCH_OVER_TAX_FACTOR
        p = round(min(0.95, max(0.05, p)), 3)
        return {"event_id": f"{window}-{target['bbr_id']}-match", "date": self.on,
                "question": f"Does {target['club']} match Miami's offer sheet for {target['player']} ({terms['years']} years, ${sum(terms['schedule']):,})?",
                "decider": f"{target['club']} (real club, drawn by rule)", "options": {"matched": p, "match_declined": round(1 - p, 3)},
                "basis": (f"Sheet first year ${terms['first_year']:,} against a comparables price of ${target['valuation']:,} "
                          f"(surplus {surplus:+.1%}); {target['club']} payroll ${payroll:,} {'over' if over_tax else 'under'} the "
                          f"${tax_line:,} tax projection after matching. 0.5 + {MATCH_SURPLUS_SLOPE} x surplus"
                          + (f", x {MATCH_OVER_TAX_FACTOR} over the tax line" if over_tax else "") + ", kept inside 5-95%.")}
