"""Historical evidence, reproducible statistical estimates, and game-input lookup.

Only completed NBA seasons are accepted. Display grades are descriptive ranks;
the engine uses estimated rates, never the ranks. Model choices are documented
in docs/statistical_ratings.md and are not claimed to be measured abilities.
"""
from bisect import bisect_left, bisect_right
from datetime import date
import hashlib
import json
import math
from pathlib import Path
import re
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
MODEL_VERSION = "veteran-2003.1"
STATS_PATH = Path("library/2003/league/nba_2002_03_player_stats.json")
RATINGS_PATH = Path("library/2003/league/nba_2003_veteran_ratings.json")
CUTOFF = "2003-06-26"
MIN_COHORT_MINUTES = 500
PRIOR_MINUTES = 300
PRIOR_ATTEMPTS = {"two_point_pct": 100, "three_point_pct": 50, "free_throw_pct": 25,
                  "three_point_attempt_rate": 20, "free_throw_attempt_rate": 50,
                  "turnovers_per_fga": 100, "true_shooting_pct": 100}
TOTAL_KEYS = ("games", "games_started", "minutes", "points", "field_goals_made",
              "field_goals_attempted", "three_pointers_made", "three_pointers_attempted",
              "free_throws_made", "free_throws_attempted", "offensive_rebounds",
              "defensive_rebounds", "assists", "steals", "blocks", "turnovers", "personal_fouls")
ADVANCED_KEYS = ("true_shooting_pct", "usage_pct", "assist_pct", "offensive_rebound_pct",
                 "defensive_rebound_pct", "steal_pct", "block_pct", "turnover_pct",
                 "three_point_attempt_rate", "free_throw_attempt_rate")
RATE_KEYS = ("two_point_pct", "three_point_pct", "free_throw_pct", "usage_pct", "assist_pct",
             "offensive_rebound_pct", "defensive_rebound_pct", "steal_pct", "block_pct",
             "three_point_attempt_rate", "free_throw_attempt_rate", "turnovers_per_fga",
             "fouls_per_minute")
GRADE_LABELS = {
    "two_point_pct": "Two-point scoring", "three_point_pct": "Three-point shooting",
    "free_throw_pct": "Free throws", "true_shooting_pct": "Scoring efficiency",
    "assist_pct": "Assist production", "turnover_pct": "Turnover control",
    "offensive_rebound_pct": "Offensive rebounding", "defensive_rebound_pct": "Defensive rebounding",
    "steal_pct": "Steal production", "block_pct": "Block production",
}


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def alias(name):
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", ascii_name.lower()).strip("_")


def ratio(numerator, denominator):
    return numerator / denominator if denominator else None


def data_errors(data):
    """Domain checks in addition to the published JSON Schema. No data is repaired."""
    if not isinstance(data, dict):
        return ["statistics must be a JSON object"]
    errors, seen = [], set()
    for key, value in {"schema_version": "1.0", "dataset_kind": "collected_stats",
                       "league": "NBA", "season_type": "regular", "as_of_date": CUTOFF}.items():
        if data.get(key) != value:
            errors.append(f"{key} must be {value!r}")
    records = data.get("records")
    if not isinstance(records, list) or not records:
        return errors + ["records must be a nonempty list"]
    for index, r in enumerate(records):
        if not isinstance(r, dict):
            errors.append(f"record {index}: not an object")
            continue
        name, pid, year = r.get("player_name"), r.get("bbr_id"), r.get("season_end_year")
        label = f"record {index} ({name})"
        if not isinstance(name, str) or not name.strip():
            errors.append(f"{label}: missing name")
        if not isinstance(pid, str) or not re.fullmatch(r"[a-z]+[0-9]{2}", pid):
            errors.append(f"{label}: verified Basketball-Reference ID required for import")
        if type(year) is not int or year != 2003:
            errors.append(f"{label}: this model accepts only the completed 2002-03 season")
        key = (str(pid), str(year))
        if key in seen:
            errors.append(f"{label}: duplicate player/season")
        seen.add(key)
        teams = r.get("team_codes")
        if not isinstance(teams, list) or not teams or any(
                not isinstance(t, str) or not re.fullmatch(r"(?!TOT$)[A-Z]{2,3}", t) for t in teams) or len(teams) != len(set(teams)):
            errors.append(f"{label}: invalid team codes")
        sources = r.get("sources", [])
        if not isinstance(sources, list) or not sources or any(
                not isinstance(s, dict) or not isinstance(s.get("url"), str)
                or not s["url"].startswith(("https://", "http://")) for s in sources):
            errors.append(f"{label}: source URLs required")
        t, a = r.get("totals"), r.get("advanced")
        valid = True
        for section, values, keys in (("totals", t, TOTAL_KEYS), ("advanced", a, ADVANCED_KEYS)):
            if not isinstance(values, dict) or set(values) != set(keys):
                errors.append(f"{label}: {section} fields do not match schema")
                valid = False
                continue
            for field, value in values.items():
                if value is None:
                    if section == "totals":
                        errors.append(f"{label}: {field} is missing; complete totals needed for this import")
                        valid = False
                    continue
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                    errors.append(f"{label}: invalid {field}")
                    valid = False
                elif section == "totals" and field != "minutes" and value != int(value):
                    errors.append(f"{label}: {field} must be a season count, not an average")
                    valid = False
                elif section == "advanced" and field not in ("true_shooting_pct", "free_throw_attempt_rate") and value > 1:
                    errors.append(f"{label}: {field} must be a fraction, not a whole-number percentage")
                    valid = False
        if not valid:
            continue
        for made, attempted in (("field_goals_made", "field_goals_attempted"),
                                 ("three_pointers_made", "three_pointers_attempted"),
                                 ("free_throws_made", "free_throws_attempted"),
                                 ("games_started", "games"),
                                 ("three_pointers_made", "field_goals_made"),
                                 ("three_pointers_attempted", "field_goals_attempted")):
            if t[made] > t[attempted]:
                errors.append(f"{label}: {made} exceeds {attempted}")
        if t["field_goals_made"] - t["three_pointers_made"] > t["field_goals_attempted"] - t["three_pointers_attempted"]:
            errors.append(f"{label}: two-point makes exceed attempts")
        if t["points"] != 2*t["field_goals_made"] + t["three_pointers_made"] + t["free_throws_made"]:
            errors.append(f"{label}: points do not reconcile")
        if not t["games"] and any(t[k] for k in TOTAL_KEYS):
            errors.append(f"{label}: production without an appearance")
        fga, fta, tov = t["field_goals_attempted"], t["free_throws_attempted"], t["turnovers"]
        expected = {"true_shooting_pct": ratio(t["points"], 2*(fga + .44*fta)),
                    "three_point_attempt_rate": ratio(t["three_pointers_attempted"], fga),
                    "free_throw_attempt_rate": ratio(fta, fga),
                    "turnover_pct": ratio(tov, fga + .44*fta + tov)}
        for field, value in expected.items():
            if (value is None) != (a[field] is None) or value is not None and abs(value - a[field]) > .000501:
                errors.append(f"{label}: {field} disagrees with totals or has wrong units")
    league = data.get("league_averages", [])
    if not isinstance(league, list) or len(league) != 1 or not isinstance(league[0], dict) or league[0].get("season_end_year") != 2003:
        errors.append("one 2002-03 league-average record required")
    else:
        averages = league[0].get("averages", {})
        required = {"pace", "points", "fga", "fg_pct", "three_pa", "three_pct", "fta",
                    "ft_pct", "orb", "drb", "ast", "stl", "blk", "tov", "pf"}
        if not isinstance(averages, dict) or set(averages) != required or any(isinstance(v, bool) or not isinstance(v, (int, float))
                                          or not math.isfinite(v) or v <= 0 for v in averages.values()):
            errors.append("invalid league averages")
    return errors


def observed_rates(record):
    t, a = record["totals"], record["advanced"]
    return {**a,
            "two_point_pct": ratio(t["field_goals_made"]-t["three_pointers_made"], t["field_goals_attempted"]-t["three_pointers_attempted"]),
            "three_point_pct": ratio(t["three_pointers_made"], t["three_pointers_attempted"]),
            "free_throw_pct": ratio(t["free_throws_made"], t["free_throws_attempted"]),
            "turnovers_per_fga": ratio(t["turnovers"], t["field_goals_attempted"]),
            "fouls_per_minute": ratio(t["personal_fouls"], t["minutes"])}


def baselines(records):
    sums = {key: sum(r["totals"][key] for r in records) for key in TOTAL_KEYS}
    mean = observed_rates({"totals": sums, "advanced": {k: None for k in ADVANCED_KEYS}})
    fga, fta, tov = sums["field_goals_attempted"], sums["free_throws_attempted"], sums["turnovers"]
    mean.update(true_shooting_pct=sums["points"]/(2*(fga+.44*fta)),
                three_point_attempt_rate=sums["three_pointers_attempted"]/fga,
                free_throw_attempt_rate=fta/fga, turnover_pct=tov/(fga+.44*fta+tov))
    for key in ("usage_pct", "assist_pct", "offensive_rebound_pct", "defensive_rebound_pct", "steal_pct", "block_pct"):
        eligible = [r for r in records if r["advanced"][key] is not None and r["totals"]["minutes"] > 0]
        # math.fsum is exactly rounded on every Python version (3.12 changed sum() for floats).
        mean[key] = math.fsum(r["advanced"][key]*r["totals"]["minutes"] for r in eligible)/math.fsum(r["totals"]["minutes"] for r in eligible)
    return mean, sums


def estimates(record, mean):
    t, observed = record["totals"], observed_rates(record)
    denominators = {"two_point_pct": t["field_goals_attempted"]-t["three_pointers_attempted"],
                    "three_point_pct": t["three_pointers_attempted"], "free_throw_pct": t["free_throws_attempted"],
                    "three_point_attempt_rate": t["field_goals_attempted"], "free_throw_attempt_rate": t["field_goals_attempted"],
                    "turnovers_per_fga": t["field_goals_attempted"],
                    "true_shooting_pct": t["field_goals_attempted"]+.44*t["free_throws_attempted"]}
    out = {}
    for key, value in observed.items():
        sample = denominators.get(key, t["minutes"])
        prior = PRIOR_ATTEMPTS.get(key, PRIOR_MINUTES)
        out[key] = (value*sample + mean[key]*prior)/(sample+prior) if value is not None else mean[key]
    return out


def build_ratings(data, data_hash):
    errors = data_errors(data)
    if errors:
        raise ValueError("\n".join(errors))
    mean, sums = baselines(data["records"])
    prepared = [(r, observed_rates(r), estimates(r, mean)) for r in data["records"]]
    cohorts = {key: sorted(e[key] for r, o, e in prepared if r["totals"]["minutes"] >= MIN_COHORT_MINUTES and o[key] is not None)
               for key in GRADE_LABELS}
    if any(not cohort for cohort in cohorts.values()):
        raise ValueError("complete veteran reference cohorts are required for percentile grades")
    players = {}
    for r, observed, estimated in prepared:
        grades = {}
        for key in GRADE_LABELS:
            cohort, value = cohorts[key], estimated[key]
            if observed[key] is None:
                grades[key] = None
                continue
            rank = (bisect_left(cohort, value)+bisect_right(cohort, value))/(2*len(cohort))
            if key == "turnover_pct":
                rank = 1-rank
            grades[key] = round(20+60*rank)
        players[r["bbr_id"]] = {
            "player_name": r["player_name"], "bbr_id": r["bbr_id"],
            "season_end_year": r["season_end_year"], "sample": {k:r["totals"][k] for k in ("games", "minutes")},
            "observed": observed, "estimated": estimated, "grades": grades,
        }
    return {"schema_version": 1, "model_version": MODEL_VERSION, "as_of": CUTOFF,
            "baseline_season": "2002-03", "source_file": str(STATS_PATH), "source_sha256": data_hash,
            "method": {"grade_scale": [20, 80], "grade_50": "median statistical estimate in the reference cohort",
                       "cohort_min_minutes": MIN_COHORT_MINUTES, "prior_minutes": PRIOR_MINUTES,
                       "prior_attempts": PRIOR_ATTEMPTS, "status": "provisional model estimates; source statistics are observations"},
            "rate_baselines": mean, "source_totals": sums, "players": players}


class RatingIndex:
    """Veteran profiles, plus rookie estimates when supplied (same rate keys and baselines)."""

    def __init__(self, data, rookies=None, trajectories=None, season=None):
        self.data = data
        self.trajectories, self.season = trajectories, season
        self.players = {pid: dict(p, model_version=data["model_version"], as_of=data["as_of"],
                                  source_sha256=data["source_sha256"]) for pid, p in data["players"].items()}
        for pid, p in ((rookies or {}).get("players") or {}).items():
            if pid in self.players:
                raise ValueError(f"{p['player_name']} has both a veteran and a rookie profile")
            self.players[pid] = dict(p, model_version=rookies["model_version"], as_of=rookies["as_of"],
                                     source_sha256=rookies["source_sha256"])
        if trajectories is not None:
            # Players known only from real careers (later draftees) still need a name lookup.
            for pid, p in trajectories.data["players"].items():
                self.players.setdefault(pid, {"player_name": p["player_name"], "bbr_id": pid, "trajectory_only": True})
        self.aliases = {}
        for pid, p in self.players.items():
            self.aliases.setdefault(alias(p["player_name"]), set()).add(pid)

    def lookup(self, player_id, bbr_id=None):
        candidates = self.aliases.get(alias(player_id), set())
        if bbr_id is not None:
            if candidates and bbr_id not in candidates:
                raise ValueError(f"{player_id}: Basketball-Reference ID conflicts with verified name")
            return self.players.get(bbr_id)
        if player_id in self.players:
            return self.players[player_id]
        if len(candidates) > 1:
            raise ValueError(f"{player_id}: ambiguous name; supply bbr_id")
        return self.players[next(iter(candidates))] if candidates else None

    def engine_profile(self, player_id, bbr_id=None):
        p = self.lookup(player_id, bbr_id)
        if p is None:
            return {}
        if self.trajectories is not None and self.trajectories.has(p["bbr_id"], self.season):
            return self.trajectories.expected_profile(p["bbr_id"], self.season, self.data["rate_baselines"])
        if p.get("trajectory_only"):
            return {}
        return {"bbr_id": p["bbr_id"], "model_version": p["model_version"],
                "as_of": p["as_of"], "season_end_year": p["season_end_year"],
                "source_sha256": p["source_sha256"],
                "rates": {k:p["estimated"][k] for k in RATE_KEYS}}


def load_rating_index(game_date, season, root=ROOT):
    date.fromisoformat(game_date)
    if season != "2003-04":
        return None  # Never silently reuse the 2002-03 player baseline in a later season.
    path = Path(root)/RATINGS_PATH
    if not path.exists():
        raise ValueError(f"missing statistical ratings: {RATINGS_PATH}")
    data = read_json(path)
    if data["as_of"] > game_date or data["baseline_season"] != "2002-03":
        raise ValueError("player statistics are not available at this game date")
    if data["model_version"] != MODEL_VERSION or data["source_sha256"] != sha256(Path(root)/STATS_PATH):
        raise ValueError("statistical ratings are stale; rebuild from the current source")
    from .prospects import PROSPECTS_PATH, ROOKIE_MODEL_VERSION, ROOKIE_PATH
    rookies = None
    if (Path(root)/ROOKIE_PATH).exists():
        rookies = read_json(Path(root)/ROOKIE_PATH)
        if (rookies["model_version"] != ROOKIE_MODEL_VERSION or rookies["as_of"] > game_date
                or rookies["veteran_model_version"] != MODEL_VERSION
                or rookies["source_sha256"] != sha256(Path(root)/PROSPECTS_PATH)):
            raise ValueError("rookie estimates are stale or not yet available; rebuild from the current source")
    from .trajectories import load_trajectories
    return RatingIndex(data, rookies, load_trajectories(root, season), season)


def repository_rating_errors(root=ROOT):
    try:
        data = read_json(Path(root)/STATS_PATH)
        errors = data_errors(data)
        if errors:
            return errors
        expected = build_ratings(data, sha256(Path(root)/STATS_PATH))
        if read_json(Path(root)/RATINGS_PATH) != expected:
            errors.append("generated veteran ratings are stale; run scripts/import_veteran_stats.py")
        return errors
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return [f"cannot validate veteran statistics: {exc}"]
