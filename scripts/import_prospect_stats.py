#!/usr/bin/env python3
"""Rebuild rookie estimates from pre-draft statistics. No requests are created and no games run."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from bisect import bisect_left, bisect_right
from runtime.player_stats import GRADE_LABELS, MIN_COHORT_MINUTES, read_json
from runtime.prospects import (ROOKIE_MODEL_VERSION, ROOKIE_PATH, SCOUTING_EFFECTIVE_FROM,
                               VETERAN_PATH, expected_rookie_estimates, rookie_errors)

CARD = ROOT / "career/Dwyane_Wade/2003-04/00_Team/Team/Player_Cards/dwyane_wade.md"
START, END = "<!-- rookie-estimate:start -->", "<!-- rookie-estimate:end -->"


def card_block(player, veterans):
    """Percentile grades against the veteran cohort, using the same 20-80 scale as veteran cards."""
    rows = []
    for key, label in GRADE_LABELS.items():
        if key not in player["estimated"] or player["translated"].get(key) is None:
            continue
        cohort = sorted(p["estimated"][key] for p in veterans["players"].values()
                        if p["sample"]["minutes"] >= MIN_COHORT_MINUTES and p["observed"][key] is not None)
        value = player["estimated"][key]
        rank = (bisect_left(cohort, value) + bisect_right(cohort, value)) / (2 * len(cohort))
        base = veterans["rate_baselines"][key]
        rows.append(f"| {label} | {round(20 + 60 * rank)} | {value:.3f} | {base:.3f} |")
    return "\n".join([
        START,
        f"### Statistical estimate from college record ({ROOKIE_MODEL_VERSION})",
        "",
        f"**Estimate, not NBA evidence.** Translated from {player['sample']['seasons']} UConn seasons "
        f"({player['sample']['games']} games, {player['sample']['minutes']} minutes) with provisional college-to-NBA "
        "factors and shrinkage toward the 2002-03 NBA average. Grades rank the estimate against 2002-03 NBA players "
        "with 500+ minutes (20-80, 50 = median). Dated scouting adds paint-pressure and position-rebound priors. "
        f"This model correction applies from {SCOUTING_EFFECTIVE_FROM}; earlier games retain rookie-2003.1. "
        "Method: [statistical ratings](../../../../../../docs/statistical_ratings.md#rookie-estimates).",
        "",
        "| Rate | Grade (20-80) | Estimate | NBA average |",
        "| --- | ---: | ---: | ---: |",
        *rows,
        "",
        f"Free-throw attempts/FGA: {player['estimated']['free_throw_attempt_rate']:.3f}; "
        f"turnovers/FGA: {player['estimated']['turnovers_per_fga']:.3f}. "
        "Pressure concerns affect turnovers against positive team defense, not the base rate. "
        "Paint and pull-up location weights preserve aggregate shooting accuracy. Rebound-led transition "
        "applies only after his own defensive rebound. These are provisional model assumptions, not tracking data.",
        END,
    ])

data = expected_rookie_estimates(ROOT)
check = "--check" in sys.argv
text = json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
path = ROOT / ROOKIE_PATH
if check:
    current = path.read_text(encoding="utf-8") if path.exists() else ""
    errors = rookie_errors(ROOT)
    print("Generated and archived rookie estimates are current." if current == text and not errors else "\n".join(errors or ["Stale: " + str(ROOKIE_PATH)]))
    raise SystemExit(0 if current == text and not errors else 1)
path.write_text(text, encoding="utf-8")
if "--update-card" in sys.argv:
    card = CARD.read_text(encoding="utf-8")
    block = card_block(data["players"]["wadedw01"], read_json(ROOT / VETERAN_PATH))
    if START in card:
        card = card[:card.index(START)] + block + card[card.index(END) + len(END):]
    else:
        anchor = "## Changes and coaching notes"
        card = card.replace(anchor, block + "\n\n" + anchor, 1)
    CARD.write_text(card, encoding="utf-8")
for p in data["players"].values():
    print(p["player_name"], {k: round(v, 3) for k, v in p["estimated"].items()})
