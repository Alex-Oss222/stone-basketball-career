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

| Input | Effect in kernel 2003.3 |
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
| DBPM (real careers only) | Defensive value: the five defenders' sum lowers the opponent's make probability and raises its turnovers (`docs/engine_model.md`) |

The engine uses estimated rates, not the 20–80 ranks. For a player with a statistical profile, overlapping legacy skill ratings are rejected to prevent ignored inputs or double counting. Explicit, evidence-based perimeter/interior defense grades remain possible; they are not inferred from steals and blocks. Players without an eligible record retain the existing neutral/explicit-grade fallback, with an empty statistical profile in the frozen packet. A fallback is not evidence that the player is average.

Per-player play weights are `1` for a field-goal attempt, `TOV/FGA` for a turnover, and `FTr * (1 - and_one_share) / 2 * regular_trip_share` for a two-shot trip, normalized by their sum. `regular_trip_share` (0.93 for 2003-04) leaves out the late-game free throws the engine's late-game fouls add back; a player's three-point share is likewise `3PAr * regular_three_share` (0.97), leaving out late-game threes (`docs/engine_model.md`, Late game). The and-one share retains the existing provisional 0.12 assumption. Every individual free-throw rate therefore controls volume independently of FT accuracy. This is an approximation: three-shot trips, technical free throws and missed-free-throw rebounds are not explicitly modeled.

Assists, rebounds, steals and blocks use rates relative to the league baselines. They are opportunity estimates, not literal per-play probabilities: [Basketball-Reference's glossary](https://www.basketball-reference.com/about/glossary.html) defines their different denominators. In this kernel, steals are selected after a turnover, and blocks after a miss. Those production rates do not independently create stops or establish matchup defense; team defense comes from the defensive value (DBPM) of real-career profiles, and veteran or rookie estimates without one count as average defenders. Rebounding is calibrated in aggregate, including a chance of a miss ending without an individual defensive rebound. Fouls affect allocation; total non-shooting foul frequency still comes from the era environment. Pace, lineups and coaching roles can also make simulated averages differ from historical ones.

The published 14.9 team turnovers per game exceeds summed individual turnovers, 14.2696 per team game. The 0.6304 gap is treated as **inferred unassigned team turnovers**, including source rounding. It is not charged to individual players. Team totals and box scores identify that difference explicitly.

## Reproducibility and scope

The source SHA-256 and model version travel with every game profile. The complete league environment and all selected rates are frozen in the journaled game packet before resolution. An edited profile, mismatched baseline, unavailable date or stale source hash is refused. Existing results remain immutable. No game requests or career results are created by this import.

Checks cover the import's arithmetic and joins, generated-file consistency, independent shot frequency and accuracy, FT range, rebounding allocation, sample shrinkage, date gates, and packet immutability. Isolated kernel calibration tests check aggregate behavior against the 2002-03 environment. They are not a historical replay or a fitted prediction of every player's next season. The priors and structural assumptions remain provisional.

The data collector reported an ESPN cross-check for 423 players and live Basketball-Reference spot checks. The repository retains that provenance in the original records; this implementation does not claim to have independently repeated those external checks. Games started remain the supplied Basketball-Reference values.

## Rookie estimates

Draftees have no NBA record, so they get an estimate from pre-draft statistics instead (`runtime/prospects.py`). Model `rookie-2003.2` adds dated qualitative scouting. On this lineage it takes effect on **November 12, 2003**, after the last closed game at adoption. This is a prospective engine-model correction, not an in-season talent gain or new scouting evidence. Games through November 11 keep the byte-preserved [rookie-2003.1 archive](../library/2003/league/nba_2003_rookie_estimates_2003_1.json).

- [Pre-draft statistics](../library/2003/league/nba_2003_prospect_stats.json): one record per draftee, with only evidence available on draft night. Wade's record is copied from his [career profile](../career/Dwyane_Wade/Dwyane_Wade_Player_Profile.md), section 13. That profile is alternate history (UConn, born 1984), so it is the canonical source and the historical Wade's college numbers are not used.
- [Original statistical inputs](../library/2003/league/nba_2003_prospect_stats_2003_1.json): byte-preserved source for the archived `rookie-2003.1` estimates. Replays before November 12 read this copy. The archived estimate keeps its original logical `source_file` and source hash; the loader resolves that hash against this archive, so earlier frozen packets remain identical.
- [Generated estimates](../library/2003/league/nba_2003_rookie_estimates.json): rebuilt with `python scripts/import_prospect_stats.py`; `--update-card` refreshes the estimate block on Wade's card. Validation fails if the file is stale.
- [Dated scouting](../library/2003/league/nba_2003_prospect_scouting.json) and [schema](../foundation/nba_prospect_scouting.schema.json): each trait has a qualitative classification, evidence date and exact profile sections. The profile is still canonical. Runtime checks reject unknown traits, unsupported classifications, evidence after June 26, unknown prospect IDs, changed profile hashes and missing sections. Review the traits before updating a source hash.

Method, per rate:

1. Combine pre-draft seasons with recency weights 3, 2, 1 (most recent first).
2. Translate. Shooting percentages and attempt tendencies are the observed rate times a level factor. Production rates (usage, assists, rebounds, steals, blocks) are the NBA baseline times the player's per-minute production relative to the NBA per-minute average, times a level factor. Fouls are not recorded, so the NBA baseline is used. A scouted position supplies an ORB/DRB split prior; without scouting, total rebounds retain the original shared relative rate.
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

### Scouting assumptions and their scope

`runtime/prospect_scouting.py` supplies the same mapping for any prospect with the same evidence. No player-name check selects these modifiers. A player without a scouting record retains exactly the generic statistical rates and has no style modifiers.

| Evidence | Model effect | Limitation |
| --- | --- | --- |
| Plus paint pressure | Multiply translated FTA/FGA by 1.15 before the existing sample shrinkage | A bounded judgment, not a fitted foul-drawing coefficient |
| Concern about pressure decisions | Multiply only the positive team-defense turnover increment by 1.5 | Team defensive value is a coarse pressure proxy; there are no explicit trap or coverage events yet. Base TOV/FGA and the adjustment against ordinary or weak defense are unchanged |
| Plus transition push | After that player's own defensive rebound, multiply the existing .22 break opportunity by 1.25, giving .275 | No change after teammates' rebounds or steals; ordinary pace, dead-ball and late-game gates still apply |
| Plus paint pressure | Spatial multipliers 1.30 at 0-3 feet and 1.10 at 3-10 feet | Modeled style, not measured individual shot-location data |
| Plus midrange pull-up | Spatial multipliers 1.10 at 10-16 feet and 1.05 at 16 feet to the arc | The six existing bands cannot isolate exactly 12-18 feet |
| Scouted primary position | Redistribute total translated rebound production with a dated position split | No fabricated college ORB/DRB counts and no extra bonus for a plus rebounding trait |

Spatial weights multiply the prior-season league shares and are normalized separately within two- and three-point attempts. The water-filling efficiency calculation uses those same new shares, preserving the player's exact aggregate make probability even near zero or one. These weights do not change three-point attempt rate, aggregate shooting accuracy or unrelated skills.

The rebound prior pools actual 2002-03 ORB/DRB totals for players with at least 500 minutes and an unambiguous primary position in the end-of-season roster. IDs count once; ambiguous or unmatched positions are omitted. The SG cohort contains 57 players, 3,122 offensive rebounds and 10,331 defensive rebounds, giving an offensive share of .2321. The translated implied total rebounds per minute is conserved, as is the estimate after equal-sample shrinkage. This is a position split prior, not an empirically fitted NCAA-to-NBA translation.

Contact finishing, secondary creation, set shooting, limited off-dribble threes, guard rebounding, screen navigation, help discipline and weak-side event defense remain explicitly sourced evidence. They do not add another numerical bonus to box-score rates. Catch versus pull-up three accuracy and possession-level defensive assignments require new engine events before they can be estimated separately. Camp defense now stays at the profile baseline of 45 until assignment-level evidence exists; preseason steals plus blocks no longer move it. The already recorded October 24 grade and camp decisions remain unchanged.

With Wade's revised college totals below, scouting moves FTA/FGA from the generic .308 to .352 and ORB%/DRB% from .052/.130 to .044/.138. The statistical translation supplies 2P% .539, 3P% .392, FT% .926, usage .208, AST% .237, 3PA/FGA .239 and base TOV/FGA .105; scouting adds no further change to those rates. These are expected rates before the same previously journaled season development swing, not targets for his simulated box scores.

Generated estimates carry the statistical source hash plus the scouting JSON, canonical profile, prior-season statistics and roster hashes. The frozen game profile carries its dated traits, derived style and source hashes. Loading a new-game profile recomputes the expected artifact and rejects stale inputs. Earlier dates load and validate only the archived generic model, preserving closed packet hashes and the existing `development:2003-04:wadedw01` draw. No requests, results, rotations, career dates or awards are rewritten. A day-one replay would require a separate pre-season lineage, not changes to these completed games.

The missing calibration study remains separate work: a verified 1997-2002 draft cohort, using pre-draft college evidence and first NBA seasons only, with the full 2003 class held out. No such cohort was imported or fitted by this correction. The NCAA factors and scouting mappings remain provisional.

Coverage at June 26, 2003: Wade only. The other 57 players in the [draft-class file](../library/2003/league/nba_2003_draft_class.json) have identity data but no pre-draft statistics or pick numbers, so they play on the neutral fallback until their records are added. A level without a factor table (high school, international) is refused rather than guessed; LeBron James (high school) and Darko Milicic (international) need their own approach.

New draft classes follow the same path: a `library/<year>/league/nba_<year>_prospect_stats.json` with draft-night evidence, gated by the draft date.

### Authorized college totals revision

The user set Wade's college career targets to 54.7 FG%, 44.2 3P%, 93.3 FT% and 21.2 PPG. The profile and statistical source use integer makes, attempts and points that round to all four targets across his existing 98 games:

| Season | G | FGM/FGA | FG% | 3PM/3PA | 3P% | FTM/FTA | FT% | PTS | PPG |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2000-01 | 34 | 194/369 | 52.6 | 42/98 | 42.9 | 98/110 | 89.1 | 528 | 15.5 |
| 2001-02 | 30 | 210/389 | 54.0 | 48/115 | 41.7 | 117/128 | 91.4 | 585 | 19.5 |
| 2002-03 | 34 | 327/578 | 56.6 | 92/199 | 46.2 | 219/227 | 96.5 | 965 | 28.4 |
| Career | 98 | 731/1336 | 54.7 | 182/412 | 44.2 | 434/465 | 93.3 | 2078 | 21.2 |

The season allocation is a modeling choice: attempt volume rises by about 8% with approximately the same shot mix and season shares, while retaining the freshman-to-junior improvement and sophomore three-point dip. Every season obeys `PTS = 2 × FGM + 3PM + FTM`. Career points are `2 × 731 + 182 + 434 = 2078`; `2078 / 98 = 21.2041`, displayed as 21.2. Percentages divide summed makes by summed attempts. Two-point totals are 549/924. The junior efficiency narrative, scouting shooting summary, statistical source, source hashes, current rookie estimates and personnel card all follow the revised counts.

Games, starts, minutes, non-scoring totals, team results, NCAA Tournament subset and recorded honors retain their existing evidence. The original source and `rookie-2003.1` artifact remain archived for every closed game. No `rookie-2003.2` game has been played at this checkpoint, so the revised estimate retains the November 12 adoption gate and the existing development draw. Translation constants and scouting trait classifications are unchanged.

### Shot-making traits and the revised scoring canon (rookie-2003.3)

Model `rookie-2003.3` (scouting `prospect-scouting-2003.2`) applies from **December 3, 2003**, Miami's first game after the last closed one. Games from November 12 to December 2 keep the [archived rookie-2003.2 estimates](../library/2003/league/nba_2003_rookie_estimates_2003_2.json), whose bytes are pinned (`prospects.ARCHIVED_ROOKIE_SHA256`), with their [scouting](../library/2003/league/nba_2003_prospect_scouting_2003_2.json) and [profile source](../library/2003/league/sources/Dwyane_Wade_Player_Profile_rookie_2003_2.md) archived beside them.

Two changes, both authorized by the user on December 1, 2003 (career clock):

1. Documented shot-making traits now move shot locations for every scouted prospect (`prospect_scouting.SHOT_TRAIT_WEIGHTS`, judgement multipliers within one shot value): catch-and-shoot spots (`set_perimeter_shooting`: corner three 1.15), a limited off-dribble three (arc 0.95), curl (10-16 ft 1.10, 3-10 ft 1.05), mid-post turnaround (same), floater (3-10 ft 1.15), face-up (10-16 ft and 16 ft to the line 1.05) and step-back (16 ft to the line 1.10), alongside the existing paint and pull-up weights. They change where attempts come from, never how many or the mean make probability.
2. Wade's scoring canon (profile section 4) was revised to a full midrange package: face-up, step-back, floater and mid-post turnaround as regular weapons, off-ball curls and flashes, and a consistent catch-and-shoot three (more than half made at UConn). The trait `catch_and_shoot_accuracy: elite` adds a relative accuracy tilt of +0.13 at the corner three (`CATCH_SHOOT_CORNER_TILT`, limit 0.15) before the shift that keeps his three-point mean: about 50% from the corner and 35% above the break for a 39% three-point shooter against average defense. The kernel reads it as `style.zone_accuracy` (kernel 2003.11).

His rates, development draw and translation constants are unchanged; the revision moves location and relative zone accuracy only. Expected two-point mix: rim 34.7%, 3-10 ft 19.5%, 10-16 ft 19.0%, 16 ft to the line 26.7% (league 35.0, 18.3, 17.8, 28.9).

## Talent trajectories (option C)

The user chose the hybrid model: real players' ability follows their real careers, with simulated development around it. Model `trajectory-hybrid.1`, `runtime/trajectories.py`. The scope rules are in `AGENTS.md` under "Talent-trajectory exception".

- **Expected path.** For each player and season in `library/careers/nba_player_careers.json`, his real rates for that season, shrunk toward the league baseline with the same 300-minute prior as veterans. A low-minute real season therefore says little. His defensive value is that season's real DBPM shrunk toward 0 (league average) with the same 300-minute prior.
- **Development swing.** Each rate is multiplied by `exp(spread × z)`. `z` follows a stationary AR(1) per player: full spread in the first season, then half of last season's swing carries over (`PERSISTENCE = 0.5`). Spreads are judgement constants: 2-5% for shooting accuracy, 6-12% for volume and production rates. Defense moves additively, `0.5 × z` points per 100 possessions, drawn last from the same event so the rate draws are unchanged.
- **Feedback from simulated seasons (capped 20%).** From the second season on, a real player's expected rates are multiplied by `exp(adjust)`, where for each rate `adjust = 0.2 × ln(observed / expected)` from his last simulated season, the observed rate first shrunk toward the expected one with the veteran sample priors, then capped at ± that rate's swing spread. `expected` is what the engine expected for that season before its swing, so a hot or cold simulated season, or a different role, carries a little into the next year. Each season's adjustment replaces the previous one; a player who keeps beating his path settles at about a sixth of the gap, and no adjustment can exceed one season's spread. Every rate is compared relative to the simulated league, so a league-wide level the engine itself adds (late-game threes, say) is nobody's surprise. Because the expectation is taken before the swing, about a sixth of last season's swing also carries through the feedback, on top of the swing's own half. The rollover (roadmap item 18) writes `career/Dwyane_Wade/<season>/trajectory_feedback.json` with `runtime/trajectories.season_feedback` from closed game results; profiles that use it carry its SHA-256 as `feedback_sha256`. There is no feedback for 2003-04, the first simulated season, and none for Wade, whose own update is below. Defense has no feedback because the simulation does not compute DBPM.
- **Who decides the draw.** The engine journals one `development:<season>:<bbr_id>` event per player and season, exactly like a game, so a swing cannot be chosen or re-rolled. Replays are identical; the developed rates and the draws travel in the frozen game packet and are re-checked.
- **Priority.** A trajectory replaces the veteran or rookie estimate for that player and season. Players without a trajectory keep their existing estimate. Wade never has one; validation rejects a careers file that includes him.
- **What it does not cover.** Trajectories carry ability only. Minutes and availability of the 28 real clubs come from their real roster on the game's date (world model D, `runtime/rotations.py`): minutes per game played, and games played over the club's games during the player's stint; a traded player is with each club for his stint's part of the season, placed from the order of his stints and his games played, never from transaction dates or results. Miami's minutes and availability are always simulated decisions. Real careers cut short by injury still describe ability, not availability.

### Careers file

`library/careers/nba_player_careers.json` is imported from Basketball-Reference season tables for 2003-04 through 2013-14 (`scripts/import_careers.py`): 1,185 players, one row per player-season, using a traded player's combined row. The historical Dwyane Wade and the Awards column are removed on import. Trajectories are active. Format:

```json
{
  "schema_version": 1,
  "kind": "player_career_rates",
  "source": "where the numbers came from",
  "players": {
    "jamesle01": {
      "player_name": "LeBron James",
      "seasons": {
        "2003-04": {"minutes": 3122, "rates": {"two_point_pct": 0.0, "...": "all 13 engine rate keys"}, "dbpm": -0.9}
      }
    }
  }
}
```

The 13 rate keys are those in `RATE_KEYS` (`runtime/player_stats.py`): two-, three- and free-throw accuracy, three-point and free-throw attempt rates, turnovers per FGA, usage, assist, offensive and defensive rebound, steal and block percentages, and fouls per minute. A rate may be `null` when the source lacks it. Basketball-Reference season tables supply all of them. `dbpm` is the advanced table's Defensive Box Plus/Minus (points per 100 possessions against a league-average defender; `null` when missing, which counts as average).

## Wade's development

Wade is alternate history, so he has no real trajectory. He develops on the same terms as everyone else, from simulated evidence only.

- **Every season he gets an engine swing.** The engine journals `development:<season>:wadedw01` and applies the same spreads as for real players. Unlike real players, his swing is drawn fresh each season instead of chaining. His simulated season already carries last year's swing into the next expectation, so chaining it would count it twice.
- **Rookie season:** college estimate (above) plus that season's swing.
- **Each later season** (`runtime/protagonist.py`, `next_season_rates`):
  1. Prior: last season's expected rates.
  2. Evidence: his simulated season, summed from closed game results' box-score lines. Rates are updated with the same sample priors as veterans (100 two-point attempts, 50 threes, 25 free throws, 300 minutes for production rates), so a short or injured season moves him less. Shooting tendencies come straight from the box score; production rates are per-minute output relative to the league, times the league baseline.
  3. Age step for his age on February 1 of the new season:

| Age | Production (usage, assists, rebounds, steals, blocks) | Accuracy (2P, 3P, FT) | Turnovers and fouls |
| --- | ---: | ---: | --- |
| up to 21 | ×1.05 | ×1.015 | ÷1.05 |
| 22-24 | ×1.03 | ×1.010 | ÷1.03 |
| 25-27 | ×1.01 | ×1.005 | ÷1.01 |
| 28-30 | ×1.00 | ×1.000 | unchanged |
| 31-33 | ×0.97 | ×0.995 | ÷0.97 |
| 34+ | ×0.94 | ×0.990 | ÷0.94 |

The age steps are provisional judgement constants for a typical curve, not fitted values. Fitting them on pre-2003 player seasons would be the upgrade. They must never be tuned toward the historical Wade. Run the update at each season's end, after every regular-season and playoff game is closed. Wiring it to the season rollover is part of building the 2004-05 season.
