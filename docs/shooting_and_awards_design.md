# Shooting and yearly awards cards

[Interactive sample](examples/player_cards_preview.html) · [Sample reports](examples/player_stats_preview.md) · [Shooting fallback](examples/sample_shooting.md) · [Awards fallback](examples/sample_awards.md)

The sample report strip contains two destinations: **Shooting** and **Awards**. The source box-score table keeps its full statistical columns. The interactive version supports pointer hover, keyboard focus and touch; the Markdown version uses ordinary image links so the navigation also works on GitHub.

The supplied images guide the visual design: a compact red-and-black navigation strip and a dark half-court chart with a small player identity. The reference player's photo, totals, shot locations and awards are not this example player's data. The sample identity uses an initials fallback when a verified photo is unavailable.

## Read the chart

| Encoding | Meaning | Interpretation |
| --- | --- | --- |
| Blue through neutral to red | Field-goal percentage, using a fixed scale | Blue is a lower make rate; red is a higher make rate |
| Dot area | Attempts per game in that spatial bin | More attempts make a larger dot; radius grows with the square root of frequency |
| Court region / zone control | Which area is being inspected | The details show that region's figures, not the player's whole-game PPG |
| Period control | Season, month, week or game sample | All counts, appearances and displayed rates refer to the selected period |
| Empty / incomplete state | No attempts, no appearance or insufficient location coverage | Missing locations are never silently treated as zero attempts |

Color means absolute FG%, not percentile, league-relative performance, player ability or expected points. A three-pointer scores more than a two-pointer; the field-goal percentage color alone does not measure total scoring value. A future league-relative mode would require separately sourced zone baselines from the same season and cutoff.

Small bins can have extreme percentages after only one or two shots. Always show makes and attempts alongside the color. Keep color and frequency scales fixed across period changes rather than making every period's busiest or most efficient bin look identical.

## Regions that add up correctly

Paint is a rectangular court area, while distance from the rim is radial. They overlap. These custom display regions avoid double-counting by using the following precedence:

1. Three-point area, respecting the corner line as well as the arc.
2. Paint, including the lane boundaries.
3. Two-pointers outside the paint, under 12 feet.
4. Two-pointers outside the paint, from 12 feet to under 18 feet.
5. Two-pointers outside the paint, 18 feet and farther inside the three-point line.

The 12- and 18-foot breaks are requested custom groupings, not names of official NBA basic zones. Labels retain “outside paint” where needed. A long corner two can be closer to the rim than an above-the-break three. A simple 23.75-foot radius is therefore insufficient to distinguish all twos from threes.

Coordinates use feet with the basket center at `(0, 0)`, lateral distance on `x` and distance toward midcourt on `y`. The baseline lies at `y = -5.25`; the lane spans `x = -8` to `8` and reaches `y = 13.75`. The three-point arc has a 23.75-foot radius and joins the straight corner boundaries at `x = -22` and `22`. A shot recorded on the three-point line is a two-pointer. Coordinate and recorded-value disagreements must be exposed instead of silently changing the score.

The diagram's boundaries describe its supported NBA geometry. Other rule eras, shorter NBA lines, FIBA courts and other competitions need their own explicit geometry adapter. A visual template does not establish support for those eras.

## Region details and denominators

For a complete selected period:

```text
zone FG% = zone made field goals / zone field-goal attempts
zone FG points = 2 × zone made twos + 3 × zone made threes
zone FG points/game = zone FG points / player appearances
zone FGA/game = zone field-goal attempts / player appearances
zone attempt share = zone field-goal attempts / all field-goal attempts
```

Every region uses the same appearance denominator, including games in which the player played but attempted no shot from that region. An explicit DNP does not add an appearance. Zero attempts yields unavailable FG%, rather than a misleading 0% shooting rate.

The chart's points come from made field goals. Free throws have their own totals and are not assigned to the paint or any other location. This lets the overall scoring line reconcile to field-goal points plus free-throw points without labelling the whole PPG total as paint production.

Incomplete tracking remains visible. Preserve located raw counts and coverage information, retain an unmapped bucket, and withhold complete-period regional per-game claims when their inputs are incomplete. Do not reconstruct actual location evidence from box scores, a player's position or a reference image. A box-score feed can support the overall shooting line without supporting a spatial chart.

“Outside view” means outside this supported half-court. It can include a valid backcourt heave, so it is distinct from an invalid record or a missing coordinate.

## What is real in the preview?

The statistical preview already has six fictional appearances and one fictional DNP. The shot fixture deliberately assigns synthetic locations to those invented shots and reconciles makes, attempts and shot values to the existing sample boxes. Those locations are layout data, not recovered NBA tracking or a result from the simulation engine.

The fixture contains enough information to reproduce each period and to verify the arithmetic. The generator, not a manually edited displayed percentage, determines the totals. The chart includes an unavailable-tracking state so the real career can remain honest until a supported location feed exists.

Build the examples from the repository root:

```bash
python scripts/build_player_preview.py
```

The HTML is generated from `docs/templates/player_cards_preview.html` and its embedded data. Edit the template or generator, then rebuild. The generated page is self-contained and can be opened locally without a server. GitHub renders the Markdown fallbacks; it displays HTML source rather than running the interactive document.

## Awards, by season

The destination is named **Awards**. Its primary surface is a collection of season award banners. Each banner names the award, season, team or competition context when applicable, and confirmation date. A season with no earned annual award shows a quiet empty state, not a row of unearned trophies.

Only earned annual awards known by that example's cutoff enter the yearly display. Weekly and monthly awards remain in their existing source records; they are not silently relabelled annual awards. Nominees, ballots, predictions and historical Wade achievements cannot become earned banners. A separately labelled fictional annual-award design case demonstrates the filled layout without adding a future result to the current example.

The photo slot is optional. A missing image or loading error returns to the initials fallback without a broken-image icon. An eventual real-player image needs a supplied or otherwise verified source and the matching identity; the template does not borrow the reference athlete's portrait.

## Research and design choices

Reviewed October 3, 2026. These sources ground terminology and geometry; they do not supply simulated player outcomes.

| Source | What is supported | Design decision |
| --- | --- | --- |
| [NBA Official, Rule 1: Court Dimensions](https://official.nba.com/rule-no-1-court-dimensions-equipment/) | Lane boundaries, three-point corner lines and arc, basket and restricted-area geometry | Draw a geometrically consistent court; avoid a radius-only three-point classifier |
| [NBA Official, Rule 5: Scoring](https://official.nba.com/rule-no-5-scoring-and-timing/) | Two points on/inside the line, three outside, one for a free throw | Use recorded shot values and keep free throws out of spatial field-goal points |
| [Jr. NBA, How to Read a Shot Chart, October 6, 2015](https://jr.nba.com/how-to-read-a-shot-chart/) | Shot charts connect attempts and results to locations; standard zone distinctions and league comparisons | Make the location and comparison basis explicit; our red-high/blue-low FG% palette is a deliberate custom choice |
| [NBA Stats glossary](https://www.nba.com/stats/help/glossary) | Field-goal percentage and effective field-goal percentage are distinct measures | Label the chart FG%, not an unspecified efficiency score |

The simplified navigation, per-region detail panel, touch/keyboard controls, initials fallback and annual banner layout are original interface choices for this repository.
