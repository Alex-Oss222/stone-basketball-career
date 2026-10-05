# Engine model and calibration (kernel 2003.10)

What the possession engine does beyond the per-play rates, why, and how it was checked. Code: `runtime/kernel.py`, `runtime/rotations.py`. Check: `python scripts/engine_diagnostics.py 4 --check --summary-json /tmp/engine-summary.json`, plus `--defense-test` and `--home-test` (analysis only: made-up entropy, nothing written to the career). Reports and optional JSON contain league aggregates, never player results for the career or front office.

All constants below are judgement constants unless a source is named. They describe how basketball is played, not any team's results, and none was fitted to a 2003-04 result. This page reports only league-wide measures; per-club and per-player results of the check stay out of the repository (AGENTS.md, option C).

## Defense (problem E1)

Each real-career profile carries a defensive value: that season's Defensive Box Plus/Minus (DBPM, points per 100 possessions against a league-average defender), shrunk toward 0 with the 300-minute prior and moved by the development swing (`docs/statistical_ratings.md`). On every play the five defenders' values are summed. One summed point is worth one point per 100 opponent possessions:

- two thirds through the opponent's make probability (`make_per_defense`): a make is worth its points and and-one free throws, less the offensive-rebound continuation a miss would have had;
- one third through the opponent's turnover probability (`tov_per_defense`): a defensive turnover takes the place of a shot and costs its full value.

Rebounding already has its own rates, so it is left out to avoid counting it twice. Check (`--defense-test 3`, the same games with half the clubs' players one point better): +5 on the floor allows 4.7 to 5.1 fewer points per 100 across the runs made.

Players without DBPM count as average defenders (0): veteran and rookie estimates, and Wade until his camp grade (roadmap item 9). Legacy 20-80 perimeter/interior grades keep their old small effect.

Kernel 2003.6 divides the shooting part of each player's existing defensive value into interior and perimeter channels. Block rate and steal rate are each measured relative to their league baseline. The specialization tilt is `(blocks - steals) / (blocks + steals + 2)`; the two added baseline events shrink extreme small-sample specialization. Interior and perimeter weights are `1 + tilt` and `1 - tilt`, normalized by the league's two-point and three-point shot values, including and-ones and offensive-rebound continuations. Thus specialization redistributes the shooting budget rather than adding more defense. The turnover budget and rebound probabilities retain their own rates.

Interior means **all two-point shots** in the defensive calculation. Kernel 2003.7 records distinct shooting locations, but this defensive approximation still applies the interior channel to every two-point zone. Blocks and steals cannot give a player with zero defensive value new defensive ability. There are still no individual matchups, size mismatches, or lineup chemistry.

## Spatial shooting and live charts (kernel 2003.7)

Every field-goal attempt selects a location before resolving its outcome. The six native source categories are 0–3 feet, 3–10 feet, 10–16 feet, 16 feet to the three-point line, corner three and arc three. The [2002–03 spatial source](shot_environment_sources.md) supplies league attempt shares and efficiencies; it is separate from the existing league environment and player profiles. Missing individual spatial profiles use the same league shape, conditioned on each player's own two-/three-point attempt share and ability. No historical Wade NBA statistics enter this model.

The model shifts the zone make probabilities together until their attempt-weighted mean equals the existing possession's make probability. When a probability reaches zero or one, the remaining zones absorb the difference. Usage, passing, transition, defense and late-clock effects therefore retain their previous expected shooting value. Locations are sampled within legal court regions using explicit geometric assumptions: these are simulated coordinates, not historical tracking observations. The source distance bands are not interchangeable with the chart's geometric paint and distance regions.

The immutable result contains complete `shot_tracking` provenance and a `shots` array: stable ID, player, side, period, remaining clock, coordinates, native zone, shot value, make/miss and transition flag. A missed shooting-foul trip is not an FGA; a blocked FGA is a recorded miss. Every made/missed two-/three-point bucket reconciles with the player and team boxes. The collector and chart adapters reject malformed or incomplete feeds. The chart reads only closed results and labels the locations as simulated engine events.

Old games remain without spatial data. A separate **Tracked games only** selection aggregates only complete tracked games, with its own dates, appearances, attempts and rates. Full-period totals retain untracked games and their visible coverage gaps. Both Wade's card and league player cards use this rule. The [spatial calibration report](spatial_calibration.md) records the aggregate checks; diagnostics never write career results.

## Usage, passing and transition (kernel 2003.6)

**Usage versus efficiency.** The shooter's expected usage is normalized against the five players on the floor. Load above his own profile estimate costs 0.30 make probability per unit of additional possession share (three percentage points for ten additional usage points); lower load provides the corresponding benefit, bounded at six percentage points either way. It applies to two- and three-point shooting, never free-throw accuracy. More minutes at the same possession share do not themselves incur this cost. The rule is the same for Wade and every other player.

**Passer effects.** The four other players' assist rates, relative to the league baseline, change a shooter's make probability by `0.018 × (mean teammate passing quality - 1)`, bounded at 3.5 percentage points. The shooter cannot improve his own shot with his own assist rate. Assists are still credited only after a made basket, so this does not create assists on misses or double-count the passer's box score. Legacy passing grades use a position-normalized fallback.

**Transition.** A credited steal offers a break with probability 70%; a credited defensive rebound offers one with probability 22%. A break uses about seven seconds, with an eight-percentage-point two-point bonus and a two-point three-point bonus relative to half-court play. Dead balls, substitutions, quarter changes, and offensive rebounds reset the opportunity; a late leading team can choose to use the clock. These are event-driven opportunities, not extra possessions added independently of the clock. No player is given a Wade-specific transition boost.

Season shooting rates and pace already include fast breaks. The calibration removes their expected contribution from half-court timing and all make rates before adding the effects to observed breaks. The expected-margin calculation also estimates each club's transition opportunities from its defense, steals and rebounds, so the score effect does not erase that advantage. The result's `transition_stats` records aggregate opportunities by origin, elapsed seconds, attempts, makes and points; it contains no fabricated shot coordinates.

The explicit end-of-period and forced late-three logic also depresses shooting already represented in the source rates. A global regular three-point correction of +0.014 restores the league target; it affects the analytic estimate and played probabilities equally. It is an aggregate calibration constant, never a player-specific correction or a change to historical source data.

## Rotations and availability (problem E3, roadmap item 8)

A player input has minutes per game when he plays and an availability, the chance he is available for a game (default 1).

- Real clubs (`"rotation": "real"`): the real roster on the game's date. Minutes per game played, and games played over the club's games during his stint. A traded player is with each club only for his stint's part of the season, placed from the order of his stints and his games played (never transaction dates), so he is on one club at a time.
- Before the tip the engine draws each player's availability, then dresses up to 12 in rotation order (most minutes per game first). With fewer than 8 available, the missing players most likely to have been available come back (hardship), so a player barely with the club stays out.
- Targets fill 240 minutes in rotation order: each player gets his average until the game is full, so a deep bench sits when everyone is healthy. When short-handed, the shortfall is spread in proportion to the averages, up to 8 minutes above a player's average and no higher than 42 (or his own average if that is higher); only if that still leaves minutes do the caps give way, up to 48.

Conflict rules (`AGENTS.md`, world model):

1. Real Miami transactions are skipped at import. A stint one began is folded into the player's previous club, whose stint extends over it. A player real Miami brought in between seasons, free agents included (chosen by the user), is back on the club he last played for (its successor if the franchise moved or was renamed), for the whole season, with his minutes per game and games played in that last season. One with no previous NBA club stays a free agent.
2. Players simulated Miami holds on the game's date are taken out of every real club. They come from Miami's dated holdings record (`00_Team/Team/Roster/holdings.json`, next to the register), matched by Basketball-Reference ID (by name only for an entry without one), so a later roster move never changes a game already played. A returned player simulated Miami signs plays for Miami only, and frees no minutes at the club he never really played for.
3. Departing players' minutes go to arrivals and returned players up to their own previous share; the rest raises the staying players' minutes in proportion to their real minutes. When the arrivals need more than the departing minutes, the difference comes out of the staying players' minutes in the same proportion.

Miami's staff reviews its rotation every fourteen days after the dated camp decision (`runtime/rotation_reviews.py`; [workflow](front_office.md#fortnightly-staff-rotation-reviews)). Each player's closed regular-season production per minute blends with a fixed preseason prior worth 300 minutes. Close starting battles use engine decision packets; clear leaders start without a draw. New dated rotation files apply prospectively, and existing game requests are never rewritten.

Explicit requests may mark five staff starters. The engine records `started` from the actual opening five after availability changes. Injury replacement starts receive the same GS credit as other starts, including in the existing season-close standing calculation. Legacy results without this field retain unknown starts; current lineups cannot fill the gap.

## Engine upgrades and closed games

Kernel 2003.8 freezes optional dated scouting, its source hashes and derived style alongside each eligible rookie's rates. On the existing career lineage, `rookie-2003.2` begins November 12, 2003; earlier dates load the archived `rookie-2003.1` data with exactly the old profile shape. The season development packet is unchanged. [Scouting assumptions](statistical_ratings.md#scouting-assumptions-and-their-scope) specify the paint-pressure prior, conserved-total rebound split, pressure-turnover sensitivity, rebounder-specific transition probability and efficiency-preserving spatial weights. Team defensive value is only a coarse proxy for pressure, not evidence that a particular possession was trapped. Historical requests, closed results, camp decisions and rotations are not regenerated.

Kernel 2003.7 retains schema 1 and freezes the full spatial environment in new game packets. The result identifies that configuration by its canonical SHA-256. For a stored game, the service selects the original kernel's input schema before loading additional sources, checks its original packet and serves the stored result verbatim. Pre-spatial packets contain no spatial environment; later data cannot change their hashes. Optional starter inputs remain absent from historical packets unless explicitly supplied. Editing an already played request or its frozen spatial inputs still fails the journal hash check. An old journal entry without a saved result fails closed across a kernel change; it must not be silently redrawn under new rules.

## Late game (problem E4)

In the 4th quarter and overtime:

- **Closing lineup:** the last 5:00 of a game within 10, and all of overtime, go to the five players with the largest targets.
- **Garbage time:** the bench takes over when the 4th-quarter lead reaches 15 plus 1 per minute left (27 at 12:00, 21 at 6:00).
- **Foul when trailing:** down 1-3 with 24 seconds or less (the game clock under the shot clock), down 4-6 with 45 or less, down 7-10 with 75 or less. The foul takes 1-4 seconds and gives two free throws to the ball handler; if that is more time than is left, the clock runs out instead. A team down more than 10 concedes. Fouls go to players who can afford them.
- **Run the clock:** a leading team inside the last 2:30 uses 14-24 seconds.
- **Trailing offense:** inside 2:30 it hurries (4-16 seconds); down 1-3 with the shot clock off it takes a good shot and leaves 2-8 seconds. Down 3 or more inside the last minute, at least 60% of its shots are threes (95% when down exactly 3 with the shot clock off).
- **Last shot:** in every period, a possession that starts with the shot clock off holds for the last shot. That final, set-defense shot converts at 0.7 times the normal rate. A possession with under 3 seconds gets a shot off only in proportion to its time.

League averages already contain late-game fouls and threes. Measured on 2003-04 rosters, this logic adds about 1.4 free-throw attempts, 0.7 fouls and 0.5 three-point attempts per team per game, so the regular rates leave those amounts out: the environment's trip, foul and three-point rates, and real players' free-throw and three-point rates (`regular_trip_share`, `regular_three_share`).

## Team pace (problem E6)

Each real club plays at its pace from the season before, relative to that season's league mean (`library/<year>/league/nba_<season>_team_pace.json`, built by `scripts/import_team_pace.py` from the Basketball-Reference team tables; only pace is kept, never results). A game runs at the average of the two clubs' paces, which scales the length of a regular possession and the expected margin. In 2003-04 the clubs range from 0.95 to 1.05 of the league pace. A club with no season before (Charlotte in 2004-05) and Miami, until its coaches set a pace, play at the league pace.

## Fatigue and injuries (problem E7, roadmap item 12)

- **Back-to-backs:** every club's rest comes from the schedule (days off since its previous regular-season game, at most 3). On the second night of a back-to-back a club plays 1.5 points worse, through its own make probability, and the expected margin accounts for it.
- **Injuries for the simulated club (Miami, Wade included):** after each Miami game, every Miami player who played may be hurt. The chance is 1.6% per 36 minutes, times 0.85 up to age 25, 1.0 to 29, 1.2 to 32 and 1.45 after, and times 1.2 on the second night of a back-to-back. Lengths: 55% day-to-day (1-2 games), 25% short (3-7), 13% medium (8-20), 6% long (21-50), 1% season-ending (51-82). A 34-minute starter averages about 1.3 injuries and 9 to 14 missed games a season. The draw uses the game's journaled entropy and is reported in the result's `injuries`; `runtime/injuries.py` counts down the games still to miss. Real injury histories are never used.
- **Real clubs** keep missing games at their real season rates through availability (rotations above); they get no extra draws.

## Score effect

Independent possessions alone give a game-to-game spread of about 15 points. Real NBA results vary about 12 points around the betting line, because a team that gets ahead of the game relaxes and one that falls behind presses. Before the tip the engine estimates the margin the two rosters should produce, from the same per-play rates, minute targets, defense, rebounding and home edge it plays with (`_expected_points`). During the game the offense's make probability moves by 0.0022 for every point it is ahead of that par line at the time (gained when behind), up to 25 points.

Pulling toward the par line rather than toward a tie removes random swings but leaves real quality and the home edge intact. Check: with the score effect off, played margins follow the estimate with a slope of 0.99, so the estimate needs no scaling.

## Foul trouble (problem E5)

With six fouls to disqualify, a player sits once he reaches 2 fouls in the 1st quarter, 3 in the 2nd, 4 in the 3rd, and 5 in the 4th until the last 5:00 (the limits follow the foul-out limit). He leaves at that dead ball if the bench has someone without foul trouble, and returns when the period changes or the limit lifts. A player one foul from disqualification fouls at a quarter of his normal rate (he defends carefully).

## Calibration record

Four seasons of the real 2003-04 schedule without Miami's games (4,428 games, 79 per club per season), real rosters on each date, kernel 2003.3. Kernel 2003.2 was measured before this check existed, on 1,500 random pairings with top-12 season shares. Benchmarks are general figures for the era, not 2003-04 results.

| Measure | Kernel 2003.2 | Kernel 2003.3 | Benchmark |
| --- | ---: | ---: | --- |
| Points per team per game | 95.2 | 94.8 | 95.1 (2002-03 environment) |
| Final-margin SD | 15.8 | 13.4 | 13-14 |
| Overtime games | 2.8% | 5.4% | 5-7% |
| Home win rate | 59.5% | 60.6% | 57-63% |
| Home edge, home minus neutral on the same games | not measured | +3.1 ± 0.2 | 3.0 (environment assumption) |
| Foul-outs per game | 0.75 | 0.22 | 0.2-0.3 |
| Spread of club average margins within a season | about 3.3 | 4.6 | 4-5 |
| Players with 30+ input minutes: simulated vs input minutes per game | not measured | 35.3 vs 35.3 | their input |

Box totals per team: FGA 81.1 (80.8), FTA 24.8 (24.4), turnovers 15.2 (14.9), offensive rebounds 12.1 (12.0), assists 21.7 (21.5), fouls 22.1 (21.8); environment values in brackets. Three-point attempts run at 15.1 against 14.7: the 2003-04 players' own three-point rates, weighted by their attempts, are about 3% above the 2002-03 environment.

Later kernels (the record above was measured on 2003.3): with team pace and back-to-backs (2003.5), three seasons give margin SD 13.1, overtime 5.0%, home win 61.2%, foul-outs 0.22 and club spread 4.6.

### Kernel 2003.10: injuries during the game, the return window and absence spells

- **When an injury happens.** The simulated club's injuries are drawn at the end of each period on the minutes played in it (same risk per minute as before), and a player hurt in a period sits out the rest of the game. Before, the draw came after the final whistle and the player finished the game.
- **Coming back.** After an injury of eight or more games, the next ten games carry 1.5 times the injury risk (`REINJURY_FACTOR`, judgement: re-injury risk is higher after a return, the size is not sourced). The staff restricts his minutes to 70%, 80% and 90% of his rotation minutes in his first three games back and gives the rest to the others (`season_games.return_restrictions`). The request carries `returning` (games back, 1-10), stored only when set so earlier packets keep their shape.
- **Real clubs' absences.** A real player misses his real share of games as spells laid out by one journaled event per player, club and season (`runtime/absence_spells.py`), lengths from the injury-length bands; his availability input for a game is 1 or 0. Before, each game was drawn on its own, so absences came as scattered single games.

### Kernel 2003.9 and rotation model 2 (games from November 12, 2003)

Three problems from the November 2003 audit, fixed together and checked on the same diagnostic schedule. Games before November 12 keep the inputs and kernel they were played with.

- **Rule 3 raises (rotation model 2, `runtime/rotations.py`).** Minutes a departed player leaves are spread over the staying rotation in proportion to real minutes, but no one gains more than `RULE3_RAISE_CAP` = 4 a game; the rest goes to the others. Before, Atlanta's uniform factor of 1.16 put Jason Terry at 43.2 input minutes against a real 37.3.
- **Reserves dress (model 2).** Beyond a club's nine largest minutes, a missed game was mostly a coach's decision, so the reserve dresses every night at his real minutes per club game (season total kept), and a club carries at most fifteen. Clubs now dress 11.8 a game on average, against 10.1 before, and only 1.4% of team-games dress nine or fewer, against 32.5%.
- **Stint gaps (model 2).** A real trade is placed by stint order and games played, so for a few games the departing players can be gone before the arriving ones start (Toronto, late November 2003). When the club's minutes then fall short of 240, every player's minutes are raised in proportion, up to the 44-minute cap, so the game can be played. Only an input the engine would otherwise refuse is changed; no played game's packet moves.
- **Garbage time (kernel 2003.9).** Real minutes already include real blowouts, so the bench now takes over at a 20-point lead plus one per minute left (was 15). Per game played against real minutes, rotation ranks 1 and 2 moved from 0.97-0.98 to 0.996 and 1.002; ranks 3 to 7 sit 2-5% above (short-handed raises). Season totals in the diagnostics run about 3.7% low for everyone because the schedule leaves out Miami's games.
- **One-game absences for the simulated club (kernel 2003.9).** Miami's injuries already lose about what 2002-03 regulars at 30+ minutes missed (7.7 games of 82, median 4); 25-30 minute regulars missed about 1.3 more than the injury model loses. `ABSENCE_PER_GAME` = 1.5% a game (illness or personal, one game), drawn before the game and reported in the result's `absences`. Larger gaps below 25 minutes are mostly coach's decisions, which Miami's own rotation makes.

Four seasons (4,428 games) on kernel 2003.9 with model 2 pass `--check`: points 94.9 (95.1), margin SD 13.4, overtime 5.2%, home win 60.0%, foul-outs 0.22 a game, club spread 4.7; FGA 80.9 (80.8), FTA 24.8 (24.4), turnovers 15.1 (14.9), assists 21.6 (21.5); FG 43.9% (44.2%); players with 30+ input minutes 35.6 against 35.3.

### Kernel 2003.6 recalibration

The reproducible four-season check covers 4,428 non-Miami games (8,856 team boxes). The same schedule and diagnostic entropy were run before the change on 2003.5. All result invariants passed. `--check` passed with its declared limits: scoring and FGA within 3% of the prior-season environment, other box counts within 6%, and aggregate shooting percentages within one percentage point. These are Monte Carlo acceptance bands, not claims of exact equality.

| Measure | 2003.5 before change | 2003.6 | Prior-season target / era benchmark |
| --- | ---: | ---: | ---: |
| Points per team | 94.82 | 95.01 | 95.1 |
| FGA per team | 81.2 | 80.88 | 80.8 |
| Three-point attempts per team | 15.2 | 15.11 | 14.7 |
| Free-throw attempts per team | 25.0 | 24.78 | 24.4 |
| Turnovers per team | 15.1 | 15.16 | 14.9 |
| Offensive rebounds per team | 12.2 | 12.11 | 12.0 |
| Assists per team | 21.6 | 21.70 | 21.5 |
| Margin SD | 13.11 | 13.24 | 13–14 |
| Overtime games | 5.4% | 5.2% | 5–7% |
| Home win rate | 60.6% | 60.8% | 57–63% |
| Foul-outs per game | 0.229 | 0.225 | 0.2–0.3 |
| Spread of club average margins | 4.59 | 4.55 | 4–5 |

New aggregate shooting: FG 43.89% (target 44.2%), three-point 35.21% (34.9%), FT 75.46% (75.8%). Defensive rebounds 30.45 (30.3), steals 8.24 (7.9), blocks 5.15 (5.0), fouls 22.09 (21.8). There are 9.83 recorded transition possessions per team, averaging 7.02 seconds. Box-counted possessions remain 95.10 against the published pace estimator's 91.0; as before, the clock is calibrated to box totals and these definitions differ.

Paired checks used three seasons each (3,321 pairs): +5 defensive value on the floor reduced opponent scoring by **4.61 points per 100 possessions**; home versus neutral court added **3.18 ± 0.21 points** (standard error). Synthetic usage tests kept the focal player's estimate fixed while reducing teammates' usage: across 400 games per scenario, his attempts rose 67.6% and shooting fell from 43.70% to 40.50%. That test concerns the model's response to load, not a prediction for Wade.

Commands: `python scripts/engine_diagnostics.py 4 --check`; `python scripts/engine_diagnostics.py 3 --defense-test`; `python scripts/engine_diagnostics.py 3 --home-test`; `python -m unittest tests.test_shot_creation -q`. Diagnostic files stay outside the career, and no real 2003-04 results were used as calibration targets.

Known gaps: from 2004-05, players real Miami traded away between seasons still follow history, because the season tables cannot tell a trade from a free-agent move (roadmap item 8).

## 2004-05 changes (roadmap 18a; from the 2004-05 season only)

The 2003-04 season keeps its procedure exactly; these apply to games whose season is 2004-05 or later (`kernel._new_era`).

- **Star usage.** The handler is chosen in proportion to his usage weight raised to `USAGE_EXPONENT = 1.15`. Plain proportional shares are normalised over each five-man lineup, so lineups with several high-usage players pulled them down. Synthetic check (`scratchpad` probe, 24 frozen March 2004 matchups x 15 games each, local entropy, never committed), realized usage over input usage: exponent 1.0 gave top-25 median 0.942, league median 0.997, bottom-25 1.028; exponent 1.15 gave 0.994, 0.992 and 0.984. Checked against the engine's own inputs only, never this season's results.
- **Separate random streams.** Availability, injuries and possessions each draw from their own stream derived from the game entropy (shot locations already had theirs), so a new draw in one model does not shift the others.
- **Credited playing time.** A player credited with any box-score event shows at least one second, taken from the teammate with the most time so the floor total holds; `validate_result` refuses a 2004-05 result where a credited player shows under one second.
- **Hand-checking (2004-05 rules).** Recorded as an era rule flag only (the user's decision): no engine effect is added, because sizing it from 2004-05 results would be hindsight.
