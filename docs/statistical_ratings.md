# Veteran ratings from 2002-03 statistics

The opening 2003-04 baseline now contains all 428 players in the supplied 2002-03 regular-season file. It is dated June 26, 2003. No later season or incoming draft-class statistics enter these estimates.

## Files and updates

- [Original supplied statistics](../library/2003/league/nba_2002_03_player_stats.json): moved unchanged from `docs/nba_veteran_stats.json`. Totals, advanced rates, nulls, notes and pinned source links remain intact.
- [Input JSON Schema](../foundation/nba_veteran_stats.schema.json): the collection contract. The importer additionally checks count relationships, duplicate IDs, season/cutoff, units and recomputable rates.
- [Generated veteran profiles](../library/2003/league/nba_2003_veteran_ratings.json): one profile per `bbr_id`, with recorded rates, estimated rates, sample sizes and display grades.
- [Import report](../library/2003/league/nba_2003_veteran_import_report.json): validation results and roster coverage.
- [League environment](../library/2003/league/nba_2002_03_league_environment.json): supplied league averages replace the previous recollected values.

Rebuild with `python scripts/import_veteran_stats.py`. Use `--check` for a read-only comparison. Add `--update-cards` to update the opening Miami veteran cards; this option is restricted to the June 26 checkpoint. It retains the original coaching notes, current-season rows, playoff history and awards. Later staff assessments belong in dated notes, outside the generated grade block.

There are 14 matching Miami veteran cards. Alonzo Mourning has no record in the supplied season and remains ungraded. Wade and Beasley are excluded. The raw end-of-season roster contains 349 verified player IDs and one duplicate Ken Johnson row without an ID; baseline rotations already deduplicate names. All 428 profiles are available if a player absent from that roster is later selected in a dated, valid game request. Importing statistics does not assign a player to a team or make an unavailable player active.

## Recorded values and model estimates

Percentages in JSON are fractions: `0.351` means 35.1%. FTr is **FTA/FGA**, not a percentage of possessions. A missing value stays `null` in the recorded layer. A measured zero remains zero. Traded players have one combined record with several team codes; it is never summed with separate team-stint rows.

For each rate, the estimate is:

`(observed_rate * sample + league_baseline * prior_sample) / (sample + prior_sample)`

A missing observation uses the league baseline for the engine and receives **no display grade**. This prevents zero attempts from becoming a zero-percent shooting skill. Small samples are pulled toward the baseline. The prior sizes below are explicit, provisional modeling choices, not empirically fitted reliability estimates or a claim about talent.

| Rate | Sample | Prior sample |
| --- | --- | ---: |
| Two-point accuracy | 2PA | 100 |
| Three-point accuracy | 3PA | 50 |
| Free-throw accuracy | FTA | 25 |
| Three-point attempt share | FGA | 20 |
| Free-throw attempt rate | FGA | 50 |
| Turnovers per FGA | FGA | 100 |
| True shooting | FGA + 0.44 × FTA | 100 |
| USG%, AST%, ORB%, DRB%, STL%, BLK%, TOV%, fouls/minute | Minutes | 300 |

Accuracy and attempt-rate baselines come from summed totals. The other advanced-rate baselines are weighted by minutes, excluding missing observations. Source TS%, 3PAr, FTr and TOV% are checked against totals with a 0.000501 tolerance for rounding to three decimal places. The source's four null advanced fields for Guy Rucker stay null in the recorded layer.

## Card grades

Cards use a **20–80 statistical scale**. Each estimated rate is ranked against players with at least 500 minutes and an observed value for that statistic. The formula is `round(20 + 60 * percentile)`, using the midpoint for ties. Turnover percent is reversed so lower turnover rates get higher grades. A grade of 50 is the median of this cohort. Comparisons are across all positions, so rebounding and assist grades describe production rather than position-adjusted skill.

These grades are descriptive. They do not drive the engine and are not added together into an overall rating. The cards show the observed evidence next to each grade, including shot attempts, games and minutes. There are 46 samples under 100 minutes. Low-minute estimates can reflect mostly the prior; they should not be read as established scouting judgments.

Usage, 3PAr and FTr are tendencies shown separately. True shooting is an efficiency summary and is not applied again as an extra shooting boost. Physical tools, creation, decision quality, rim versus midrange finishing and overall defense remain unassessed. The file has no shot-distance data, film grades, playoff history or award records from which to establish them.

## Engine mapping

Game requests join on `bbr_id` when supplied. Existing canonical names, normalized snake-case IDs and BRef IDs are also recognized. A known name paired with another player's ID is rejected. Team abbreviations are not used for identity. Explicit player lists may include an optional `bbr_id`; requests cannot supply their own statistical profile.

| Input | Effect in kernel 2003.2 |
| --- | --- |
| USG% | Relative weight for selecting the player who uses a play |
| 3PAr | Chance that his field-goal attempt is a three, independent of accuracy |
| 2P%, 3P% | Make probability for that shot type |
| FTr | Free-throw trips and and-one frequency relative to field-goal attempts |
| FT% | Free-throw make probability, including poor shooters below the old effective range |
| TOV/FGA | Individual turnovers relative to shooting opportunities |
| AST% | Assist allocation and the team's chance of an assisted basket |
| ORB%, DRB% | Separate offensive and defensive rebound weights; relative lineup strength changes recovery chances |
| STL%, BLK% | Relative frequency and allocation of credited steals and blocks |
| Fouls/minute | Allocation of defensive fouls |

The engine uses estimated rates, not the 20–80 ranks. For a player with a statistical profile, overlapping legacy skill ratings are rejected to prevent ignored inputs or double counting. Explicit, evidence-based perimeter/interior defense grades remain possible; they are not inferred from steals and blocks. Players without an eligible record retain the existing neutral/explicit-grade fallback, with an empty statistical profile in the frozen packet. A fallback is not evidence that the player is average.

Per-player play weights are `1` for a field-goal attempt, `TOV/FGA` for a turnover, and `FTr * (1 - and_one_share) / 2` for a two-shot trip, normalized by their sum. The and-one share retains the existing provisional 0.12 assumption. Every individual free-throw rate therefore controls volume independently of FT accuracy. This is an approximation: three-shot trips, technical free throws and missed-free-throw rebounds are not explicitly modeled.

Assists, rebounds, steals and blocks use rates relative to the league baselines. They are opportunity estimates, not literal per-play probabilities: [Basketball-Reference's glossary](https://www.basketball-reference.com/about/glossary.html) defines their different denominators. In this kernel, steals are selected after a turnover, and blocks after a miss. Those production rates do not independently create stops or establish matchup defense. Rebounding is calibrated in aggregate, including a chance of a miss ending without an individual defensive rebound. Fouls affect allocation; total non-shooting foul frequency still comes from the era environment. Pace, lineups and coaching roles can also make simulated averages differ from historical ones.

The published 14.9 team turnovers per game exceeds summed individual turnovers, 14.2696 per team game. The 0.6304 gap is treated as **inferred unassigned team turnovers**, including source rounding. It is not charged to individual players. Team totals and box scores identify that difference explicitly.

## Reproducibility and scope

The source SHA-256 and model version travel with every game profile. The complete league environment and all selected rates are frozen in the journaled game packet before resolution. An edited profile, mismatched baseline, unavailable date or stale source hash is refused. Existing results remain immutable. No game requests or career results are created by this import.

Checks cover the import's arithmetic and joins, generated-file consistency, independent shot frequency and accuracy, FT range, rebounding allocation, sample shrinkage, date gates, and packet immutability. Isolated kernel calibration tests check aggregate behavior against the 2002-03 environment. They are not a historical replay or a fitted prediction of every player's next season. The priors and structural assumptions remain provisional.

The data collector reported an ESPN cross-check for 423 players and live Basketball-Reference spot checks. The repository retains that provenance in the original records; this implementation does not claim to have independently repeated those external checks. Games started remain the supplied Basketball-Reference values.

## Rookie estimates

Draftees have no NBA record, so they get an estimate from pre-draft statistics instead (model `rookie-2003.1`, `runtime/prospects.py`).

- [Pre-draft statistics](../library/2003/league/nba_2003_prospect_stats.json): one record per draftee, with only evidence available on draft night. Wade's record is copied from his [career profile](../career/Dwyane_Wade/Dwyane_Wade_Player_Profile.md), section 13. That profile is alternate history (UConn, born 1984), so it is the canonical source and the historical Wade's college numbers are not used.
- [Generated estimates](../library/2003/league/nba_2003_rookie_estimates.json): rebuilt with `python scripts/import_prospect_stats.py`; `--update-card` refreshes the estimate block on Wade's card. Validation fails if the file is stale.

Method, per rate:

1. Combine pre-draft seasons with recency weights 3, 2, 1 (most recent first).
2. Translate. Shooting percentages and attempt tendencies are the observed rate times a level factor. Production rates (usage, assists, rebounds, steals, blocks) are the NBA baseline times the player's per-minute production relative to the NBA per-minute average, times a level factor. Pre-draft records give total rebounds only, so offensive and defensive rebounding share one relative rate. Fouls are not recorded, so the NBA baseline is used.
3. Shrink toward the NBA baseline with the veteran priors above, counting each college attempt or minute as half of an NBA one.

| NCAA level factor | Value | Reason |
| --- | ---: | --- |
| Two-point accuracy | 0.92 | Longer, faster interior defense |
| Three-point accuracy | 0.90 | 19'9" college line; NBA 22' to 23'9" |
| Free-throw accuracy | 1.00 | Same distance |
| Three-point attempt share | 0.75 | Fewer threes at the longer line |
| Free-throw attempt rate | 0.85 | |
| Turnovers per FGA | 1.15 | More pressure and length |
| Usage, assists, rebounds | 0.85 | Stronger teammates and opponents |
| Steals, blocks | 0.80 | |

All of these are provisional judgement constants, not fitted values. Replacing them with factors fitted on pre-2003 drafts (college season against rookie season) is the obvious upgrade once that data is in the library. They must never be tuned to make a 2003 draftee match his real NBA career.

Coverage at June 26, 2003: Wade only. The other 57 players in the [draft-class file](../library/2003/league/nba_2003_draft_class.json) have identity data but no pre-draft statistics or pick numbers, so they play on the neutral fallback until their records are added. A level without a factor table (high school, international) is refused rather than guessed; LeBron James (high school) and Darko Milicic (international) need their own approach.

New draft classes follow the same path: a `library/<year>/league/nba_<year>_prospect_stats.json` with draft-night evidence, gated by the draft date.
