"""Skill fit: what a player adds to Miami beyond minutes at his position (docs/front_office.md, Skill fit).

The front office reads only evidence dated on or before the career date: the completed 2002-03 season's
estimated rates (`nba_2003_veteran_ratings.json`), the 2002-03 defensive box plus/minus
(`nba_2002_03_defense.json`) and, for draftees, the dated rookie estimates. Never the engine's 2003-04
talent trajectories.

Each player gets six standardized skills against the 2002-03 league (players with 500+ minutes):
- spacing: three-pointers made per field-goal attempt (attempt rate x accuracy);
- rim_protection: block percentage;
- rebounding: offensive plus defensive rebound percentage;
- defense: 2002-03 DBPM (0 when unrecorded, as for a draftee);
- playmaking: assist percentage;
- creation: usage percentage (how much of the offense he needs).

Miami's need for each skill is how far its held players, weighted by production, fall below the league
on it (0 when Miami is at or above average). A candidate's skill fit is
    1 + NEED_WEIGHT x sum(need[s] x z[s]) - DUPLICATION_WEIGHT x crowding,
where crowding is his creation above average times Miami's own creation above average (a second
high-usage scorer next to Wade crowds him). Bounded to FIT_LIMITS. The same rule for every player.
"""
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEASON = "2003-04"
VETERANS = Path("library/2003/league/nba_2003_veteran_ratings.json")
DEFENSE = Path("library/2003/league/nba_2002_03_defense.json")
ROOKIES = Path("library/2003/league/nba_2003_rookie_estimates.json")
SKILLS = ("spacing", "rim_protection", "rebounding", "defense", "playmaking", "creation")
NEEDED = ("spacing", "rim_protection", "rebounding", "defense", "playmaking")   # creation is crowding, not a need
COHORT_MINUTES = 500
NEED_WEIGHT = 0.12            # judgement: a full standard deviation on a full-need skill moves fit by 12%
DUPLICATION_WEIGHT = 0.10     # judgement: a high-usage scorer next to a high-usage club
FIT_LIMITS = (0.6, 1.4)
NEED_CAP = 1.5                # standard deviations


def _read(rel, root):
    path = Path(root) / rel
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def raw_skills(rates, dbpm):
    return {"spacing": rates["three_point_attempt_rate"] * rates["three_point_pct"],
            "rim_protection": rates["block_pct"],
            "rebounding": rates["offensive_rebound_pct"] + rates["defensive_rebound_pct"],
            "defense": dbpm if dbpm is not None else None,
            "playmaking": rates["assist_pct"], "creation": rates["usage_pct"]}


class SkillFit:
    def __init__(self, root=ROOT):
        root = Path(root)
        veterans = _read(VETERANS, root)
        defense = (_read(DEFENSE, root) or {}).get("players", {})
        rookies = (_read(ROOKIES, root) or {}).get("players", {})
        self.raw = {}
        cohort = []
        for bbr, p in veterans["players"].items():
            d = defense.get(bbr, {}).get("dbpm")
            self.raw[bbr] = raw_skills(p["estimated"], d)
            if p["sample"]["minutes"] >= COHORT_MINUTES:
                cohort.append(self.raw[bbr])
        for bbr, p in rookies.items():
            self.raw.setdefault(bbr, raw_skills(p["estimated"], None))
        self.mean, self.sd = {}, {}
        for s in SKILLS:
            values = [r[s] for r in cohort if r[s] is not None]
            m = sum(values) / len(values)
            self.mean[s] = m
            self.sd[s] = math.sqrt(sum((v - m) ** 2 for v in values) / len(values)) or 1.0

    def z(self, bbr_id):
        """Standardized skills of a player, or None without dated evidence."""
        raw = self.raw.get(bbr_id)
        if raw is None:
            return None
        return {s: 0.0 if raw[s] is None else max(-3.0, min(3.0, (raw[s] - self.mean[s]) / self.sd[s])) for s in SKILLS}

    def club_profile(self, held):
        """Production-weighted mean skills of the players a club holds: [(bbr_id, weight)]."""
        rows = [(self.z(b), w) for b, w in held if self.z(b) is not None and w > 0]
        total = sum(w for _, w in rows)
        if not total:
            return {s: 0.0 for s in SKILLS}
        return {s: sum(z[s] * w for z, w in rows) / total for s in SKILLS}

    def needs(self, held):
        profile = self.club_profile(held)
        need = {s: round(min(NEED_CAP, max(0.0, -profile[s])), 3) for s in NEEDED}
        return {"profile": {s: round(v, 3) for s, v in profile.items()}, "need": need,
                "creation_load": round(max(0.0, profile["creation"]), 3)}

    def fit(self, bbr_id, club_needs):
        """Skill-fit multiplier of a candidate for a club with these needs (1.0 without evidence)."""
        z = self.z(bbr_id)
        if z is None:
            return 1.0
        gain = sum(club_needs["need"][s] * z[s] for s in NEEDED)
        crowding = max(0.0, z["creation"]) * club_needs["creation_load"]
        return round(max(FIT_LIMITS[0], min(FIT_LIMITS[1], 1 + NEED_WEIGHT * gain - DUPLICATION_WEIGHT * crowding)), 3)
