#!/usr/bin/env python3
"""Reproduce the league's 2002-03 spatial prior from pinned, prior-season CSVs.

  python scripts/import_shot_environment.py --check
  python scripts/import_shot_environment.py --write
  python scripts/import_shot_environment.py --fetch --write

The default check and write are offline. --fetch verifies the pinned upstream
files before retaining only NBA season 2003 rows; later-season rows never enter
the repository. No player-specific ability or career record is generated.
"""
import argparse
from collections import defaultdict
import csv
from decimal import Decimal
import hashlib
import io
import json
from pathlib import Path
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = Path("library/2003/league/nba_2002_03_shot_environment.json")
SOURCE_DIR = Path("library/2003/league/sources")
REVISION = "7f9b3375439b79cb4e62f66ae7d12160275c2863"
SOURCE_BASE = f"https://raw.githubusercontent.com/sumitrodatta/nba-alt-awards/{REVISION}/2025/Data/"
SOURCES = {
    "shooting": {
        "url": SOURCE_BASE + "Player%20Shooting.csv",
        "upstream_sha256": "e7d16e3a1bc2fcb9bb07ee89310b438f27e12b25afa53f4e22c67c739ec08c5f",
        "snapshot_file": str(SOURCE_DIR / "nba_2002_03_player_shooting.csv"),
        "snapshot_sha256": "fae8dcc21e67302e0b112d993efdceabfe6cb576ef7620b36d41a345b69d579b",
    },
    "totals": {
        "url": SOURCE_BASE + "Player%20Totals.csv",
        "upstream_sha256": "3406548a8be421dfd248edceb7efa8a7eba02aaf5eae26d1121e7f2484068cea",
        "snapshot_file": str(SOURCE_DIR / "nba_2002_03_player_totals.csv"),
        "snapshot_sha256": "2971a07163924f75133d9c2daa16ffa040f12a07cad1329bbe35c3d7cfe88ae5",
    },
}
DISTANCE_BANDS = (
    ("distance_0_3", "x0_3", 0, 3),
    ("distance_3_10", "x3_10", 3, 10),
    ("distance_10_16", "x10_16", 10, 16),
    ("distance_16_three", "x16_3p", 16, None),
)


def verify(raw, expected, label):
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError(f"{label}: SHA-256 mismatch")
    return raw


def season_snapshot(raw):
    """Keep the source's columns and row order, with deterministic LF CSV output."""
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
    rows = [row for row in reader if row["season"] == "2003" and row["lg"] == "NBA"]
    if not rows:
        raise ValueError("source contains no NBA 2002-03 rows")
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=reader.fieldnames, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


def fetch_sources(root=ROOT):
    """Validate both downloads completely before writing either snapshot."""
    snapshots = []
    for name, spec in SOURCES.items():
        with urlopen(spec["url"], timeout=60) as response:
            raw = response.read()
        verify(raw, spec["upstream_sha256"], name + " upstream")
        snapshot = season_snapshot(raw)
        verify(snapshot, spec["snapshot_sha256"], name + " snapshot")
        snapshots.append((Path(root) / spec["snapshot_file"], snapshot))
    for path, raw in snapshots:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)


def read_sources(root=ROOT):
    out = {}
    for name, spec in SOURCES.items():
        raw = (Path(root) / spec["snapshot_file"]).read_bytes()
        verify(raw, spec["snapshot_sha256"], name + " snapshot")
        rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8"))))
        if any(row["season"] != "2003" or row["lg"] != "NBA" for row in rows):
            raise ValueError("spatial calibration must contain only NBA 2002-03 rows")
        out[name] = rows
    return out


def full_season_rows(rows):
    """A traded player's TOT row replaces his individual team stints exactly once."""
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["player_id"]].append(row)
    selected = {}
    for player, group in grouped.items():
        aggregate = [row for row in group if row["tm"] == "TOT"]
        if len(aggregate) == 1:
            selected[player] = aggregate[0]
        elif len(group) == 1 and not aggregate:
            selected[player] = group[0]
        else:
            raise ValueError(f"ambiguous full-season rows for player {player}")
    return selected


def fraction(row, field, *, required=False):
    value = row[field]
    if value in ("", "NA"):
        if required:
            raise ValueError(f"{row['player']}: missing {field} for positive attempts")
        return Decimal(0)
    result = Decimal(value)
    if not Decimal(0) <= result <= Decimal(1):
        raise ValueError(f"{row['player']}: {field} is outside [0, 1]")
    return result


def build_environment(root=ROOT):
    sources = read_sources(root)
    shooting = full_season_rows(sources["shooting"])
    totals = full_season_rows(sources["totals"])
    if shooting.keys() != totals.keys():
        raise ValueError("shooting and totals do not cover the same players")
    attempts = defaultdict(Decimal)
    makes = defaultdict(Decimal)
    league_totals = {key: 0 for key in ("fga", "fg", "x2pa", "x2p", "x3pa", "x3p")}
    for player, total in totals.items():
        row = shooting[player]
        if any(total[key] != row[key] for key in ("seas_id", "season", "player", "tm", "lg")):
            raise ValueError(f"shooting and totals identity mismatch for {player}")
        for key in league_totals:
            league_totals[key] += int(total[key])
        fga = Decimal(total["fga"])
        for zone, field, _, _ in DISTANCE_BANDS:
            count = fga * fraction(row, f"percent_fga_from_{field}_range", required=bool(fga))
            attempts[zone] += count
            makes[zone] += count * fraction(row, f"fg_percent_from_{field}_range", required=bool(count))
        threes = Decimal(total["x3pa"])
        corners = threes * fraction(row, "percent_corner_3s_of_3pa", required=bool(threes))
        corner_makes = corners * fraction(row, "corner_3_point_percent", required=bool(corners))
        attempts["corner_three"] += corners
        makes["corner_three"] += corner_makes
        attempts["arc_three"] += threes - corners
        makes["arc_three"] += Decimal(total["x3p"]) - corner_makes
    two_ids = [row[0] for row in DISTANCE_BANDS]
    two_attempts = sum(attempts[key] for key in two_ids)
    two_makes = sum(makes[key] for key in two_ids)
    three_attempts = attempts["corner_three"] + attempts["arc_three"]
    zones = []
    for key in [*two_ids, "corner_three", "arc_three"]:
        is_two = key in two_ids
        zones.append({"id": key, "shot_value": 2 if is_two else 3,
                      "attempt_share_within_value": float(attempts[key] / (two_attempts if is_two else three_attempts)),
                      "fg_pct": float(makes[key] / attempts[key]),
                      "estimated_attempts": float(attempts[key]), "estimated_makes": float(makes[key])})
    return {
        "schema_version": 1,
        "model_version": "spatial-2003.1",
        "league": "NBA", "season": "2002-03", "kind": "league_shot_environment",
        "purpose": "Prior-season league spatial shape for 2003-04, conditioned on each simulated player's own two- and three-point rates. No historical Wade NBA statistics or individual spatial ability are imported.",
        "published_after": "2003-04-16",
        "publication_gate_basis": "Same completed-prior-regular-season cutoff as nba_2002_03_league_environment.json. This is an engine availability gate after the 2002-03 regular season, not a claimed archival publication timestamp for the later retrieved CSV.",
        "player_profile_policy": "league_prior_conditioned_on_player_two_three_rates",
        "count_kind": "estimates reconstructed from rounded source shares and percentages; not observed integer shot counts",
        "zones": zones,
        "two_point_fg_pct": float(two_makes / two_attempts),
        "three_point_fg_pct": league_totals["x3p"] / league_totals["x3pa"],
        "league_totals": league_totals,
        "coverage": {"source_rows_per_table": len(sources["shooting"]), "unique_full_season_players": len(totals),
                     "aggregated_trade_rows_used": sum(row["tm"] == "TOT" for row in totals.values()),
                     "reconstructed_two_point_attempts": float(two_attempts),
                     "reconstructed_two_point_makes": float(two_makes),
                     "two_point_attempt_rounding_residual": float(Decimal(league_totals["x2pa"]) - two_attempts),
                     "two_point_make_rounding_residual": float(Decimal(league_totals["x2p"]) - two_makes)},
        "provenance": {
            "provider": "Basketball-Reference player shooting and totals, via the pinned sumitrodatta/nba-alt-awards mirror",
            "reference_url": "https://www.basketball-reference.com/leagues/NBA_2003_shooting.html",
            "retrieved_on": "2026-10-03", "revision": REVISION,
            "sources": [{"table": key, **spec} for key, spec in SOURCES.items()],
            "snapshot_rule": "All source columns, season=2003 and lg=NBA rows only; original order; UTF-8 CSV with LF line endings.",
            "method": [
                "Select TOT once for traded players and the sole team row for everyone else; join shooting to totals by player_id with matching season, seas_id, player, team and league.",
                "Distance-band attempts = total FGA times source percent_fga_from_band_range; band makes = estimated attempts times source fg_percent_from_band_range.",
                "Corner-three attempts = exact total 3PA times percent_corner_3s_of_3pa; makes = estimated attempts times corner_3_point_percent.",
                "Arc-three estimates are exact total 3PA and 3PM minus corner estimates, including the source's non-corner heaves.",
                "Normalize the four reconstructed two-point attempt weights within two-pointers and the two three-point weights within three-pointers; do not replace the player's existing 3P attempt rate or aggregate two-/three-point ability.",
                "Use the reconstructed weighted two-point FG percentage as the spatial two-point baseline so relative zone effects cancel in expectation despite rounded source percentages."
            ],
        },
        "geometry_assumptions": [
            "Distance bands 0-3, 3-10, 10-16 and 16 feet to the three-point line are the measured source categories. They are not measured restricted-area or paint categories.",
            "No lateral, within-band radial, handedness, shot-type or exact-coordinate observations are available in these sources.",
            "Two-point coordinates may be sampled with area-uniform radius inside the native distance band and uniform front-half angle, rejecting positions outside the court or two-point region. These are provisional structural choices, not measured tendencies.",
            "Corner-three coordinates may be sampled uniformly inside the legal corner strips; arc-three coordinates may use area-uniform radius from 23.75 to 28 feet with court and corner rejection. The 28-foot cutoff and within-region distributions are provisional assumptions; deep heaves are not individually reconstructed.",
            "Corner-three source labels are mapped to the court's straight three-point-line regions. The source does not supply exact coordinates to independently verify this boundary for each attempt.",
            "Physical reporting zones are derived from simulated coordinates. Simulated coordinates never become historical tracking observations or evidence about an individual player's real shot-location distribution."
        ],
    }


def rendered(root=ROOT):
    return json.dumps(build_environment(root), indent=2, ensure_ascii=False) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write", action="store_true")
    parser.add_argument("--fetch", action="store_true", help="verify pinned upstream CSVs and retain prior-season snapshots")
    args = parser.parse_args()
    if args.fetch and not args.write:
        parser.error("--fetch requires --write; --check is always read-only and offline")
    if args.fetch:
        fetch_sources()
    expected = rendered()
    target = ROOT / OUTPUT
    if args.write:
        target.write_text(expected, encoding="utf-8")
        print(f"Wrote {OUTPUT}; six league zones from NBA 2002-03 only.")
        return 0
    if not target.is_file() or target.read_text(encoding="utf-8") != expected:
        print(f"Stale or missing {OUTPUT}; run this script with --write.")
        return 1
    print("Spatial prior and pinned prior-season source checksums match.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
