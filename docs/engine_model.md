# Engine model and calibration (kernel 2003.3)

What the possession engine does beyond the per-play rates, why, and how it was checked. Code: `runtime/kernel.py`, `runtime/rotations.py`. Check: `python scripts/engine_diagnostics.py 6`, plus `--defense-test` and `--home-test` (analysis only: made-up entropy, nothing written to the career; its output names clubs and players and is not to be committed).

All constants below are judgement constants unless a source is named. They describe how basketball is played, not any team's results, and none was fitted to a 2003-04 result. This page reports only league-wide measures; per-club and per-player results of the check stay out of the repository (AGENTS.md, option C).

## Defense (problem E1)

Each real-career profile carries a defensive value: that season's Defensive Box Plus/Minus (DBPM, points per 100 possessions against a league-average defender), shrunk toward 0 with the 300-minute prior and moved by the development swing (`docs/statistical_ratings.md`). On every play the five defenders' values are summed. One summed point is worth one point per 100 opponent possessions:

- two thirds through the opponent's make probability (`make_per_defense`): a make is worth its points and and-one free throws, less the offensive-rebound continuation a miss would have had;
- one third through the opponent's turnover probability (`tov_per_defense`): a defensive turnover takes the place of a shot and costs its full value.

Rebounding already has its own rates, so it is left out to avoid counting it twice. Check (`--defense-test 3`, the same games with half the clubs' players one point better): +5 on the floor allows 5.1 fewer points per 100.

Players without DBPM count as average defenders (0): veteran and rookie estimates, and Wade until his camp grade (roadmap item 9). Legacy 20-80 perimeter/interior grades keep their old small effect.

## Rotations and availability (problem E3, roadmap item 8)

A player input has minutes per game when he plays and an availability, the chance he is available for a game (default 1).

- Real clubs (`"rotation": "real"`): the real roster on the game's date. Minutes per game played, and games played over the club's games during his stint. A traded player is with each club only for his stint's part of the season, placed from the order of his stints and his games played (never transaction dates), so he is on one club at a time.
- Before the tip the engine draws each player's availability, then dresses up to 12 in rotation order (most minutes per game first). With fewer than 8 available, the missing players most likely to have been available come back (hardship), so a player barely with the club stays out.
- Targets fill 240 minutes in rotation order: each player gets his average until the game is full, so a deep bench sits when everyone is healthy. When short-handed, the shortfall is spread in proportion to the averages, up to 8 minutes above a player's average and no higher than 42 (or his own average if that is higher); only if that still leaves minutes do the caps give way, up to 48.

Conflict rules (`AGENTS.md`, world model):

1. Real Miami transactions are skipped at import. A stint one began is folded into the player's previous club, whose stint extends over it. A player real Miami brought in between seasons, free agents included (chosen by the user), is back on the club that had him at the end of the season before, for the whole season, with that season's minutes per game and games played. One with no previous NBA club stays a free agent.
2. Players on simulated Miami's register are taken out of every real club, matched by Basketball-Reference ID or name. So a returned player simulated Miami signs plays for Miami only.
3. Departing players' minutes go to arrivals and returned players up to their own previous share; the rest raises the staying players' minutes in proportion to their real minutes. When the arrivals need more than the departing minutes, the difference comes out of the staying players' minutes in the same proportion.

## Late game (problem E4)

In the 4th quarter and overtime:

- **Closing lineup:** the last 5:00 of a game within 10, and all of overtime, go to the five players with the largest targets.
- **Garbage time:** the bench takes over when the 4th-quarter lead reaches 15 plus 1 per minute left (27 at 12:00, 21 at 6:00).
- **Foul when trailing:** down 1-3 with 24 seconds or less (the game clock under the shot clock), down 4-6 with 45 or less, down 7-10 with 75 or less. The foul takes 1-4 seconds and gives two free throws to the ball handler; if that is more time than is left, the clock runs out instead. A team down more than 10 concedes. Fouls go to players who can afford them.
- **Run the clock:** a leading team inside the last 2:30 uses 14-24 seconds.
- **Trailing offense:** inside 2:30 it hurries (4-16 seconds); down 1-3 with the shot clock off it takes a good shot and leaves 2-8 seconds. Down 3 or more inside the last minute, at least 60% of its shots are threes (95% when down exactly 3 with the shot clock off).
- **Last shot:** in every period, a possession that starts with the shot clock off holds for the last shot. That final, set-defense shot converts at 0.7 times the normal rate. A possession with under 3 seconds gets a shot off only in proportion to its time.

League averages already contain late-game fouls and threes. Measured on 2003-04 rosters, this logic adds about 1.4 free-throw attempts, 0.7 fouls and 0.5 three-point attempts per team per game, so the regular rates leave those amounts out: the environment's trip, foul and three-point rates, and real players' free-throw and three-point rates (`regular_trip_share`, `regular_three_share`).

## Score effect

Independent possessions alone give a game-to-game spread of about 15 points. Real NBA results vary about 12 points around the betting line, because a team that gets ahead of the game relaxes and one that falls behind presses. Before the tip the engine estimates the margin the two rosters should produce, from the same per-play rates, minute targets, defense, rebounding and home edge it plays with (`_expected_points`). During the game the offense's make probability moves by 0.0022 for every point it is ahead of that par line at the time (gained when behind), up to 25 points.

Pulling toward the par line rather than toward a tie removes random swings but leaves real quality and the home edge intact. Check: with the score effect off, played margins follow the estimate with a slope of 0.99, so the estimate needs no scaling.

## Foul trouble (problem E5)

With six fouls to disqualify, a player sits once he reaches 2 fouls in the 1st quarter, 3 in the 2nd, 4 in the 3rd, and 5 in the 4th until the last 5:00 (the limits follow the foul-out limit). He leaves at that dead ball if the bench has someone without foul trouble, and returns when the period changes or the limit lifts. A player one foul from disqualification fouls at a quarter of his normal rate (he defends carefully).

## Calibration record

Six seasons of the real 2003-04 schedule without Miami's games (6,642 games, 79 per club per season), real rosters on each date, kernel 2003.3. Kernel 2003.2 was measured before this check existed, on 1,500 random pairings with top-12 season shares. Benchmarks are general figures for the era, not 2003-04 results.

| Measure | Kernel 2003.2 | Kernel 2003.3 | Benchmark |
| --- | ---: | ---: | --- |
| Points per team per game | 95.2 | 95.3 | 95.1 (2002-03 environment) |
| Final-margin SD | 15.8 | 13.1 | 13-14 |
| Overtime games | 2.8% | 5.0% | 5-7% |
| Home win rate | 59.5% | 59.9% | 57-63% |
| Home edge, home minus neutral on the same games | not measured | +3.1 ± 0.2 | 3.0 (environment assumption) |
| Foul-outs per game | 0.75 | 0.22 | 0.2-0.3 |
| Spread of club average margins within a season | about 3.3 | 4.6 | 4-5 |
| Players with 30+ input minutes: simulated vs input minutes per game | not measured | 35.9 vs 35.3 | their input |

Box totals per team: FGA 81.1 (80.8), FTA 24.9 (24.4), turnovers 15.2 (14.9), offensive rebounds 12.1 (12.0), assists 21.7 (21.5), fouls 22.2 (21.8); environment values in brackets. Three-point attempts run at 15.2 against 14.7: the 2003-04 players' own three-point rates, weighted by their attempts, are about 3% above the 2002-03 environment.

Known gaps: team pace is uniform (problem E6); there are no injuries or fatigue (problem E7, roadmap item 12); from 2004-05, players real Miami traded away between seasons still follow history, because the season tables cannot tell a trade from a free-agent move (roadmap item 8).
