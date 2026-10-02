# Engine model and calibration (kernel 2003.3)

What the possession engine does beyond the per-play rates, why, and how it was checked. Code: `runtime/kernel.py`, `runtime/rotations.py`. Check: `python scripts/engine_diagnostics.py 6000` (analysis only: made-up entropy, nothing written to the career).

All constants below are judgement constants unless a source is named. They describe how basketball is played, not any team's results, and none was fitted to a 2003-04 result.

## Defense (problem E1)

Each real-career profile carries a defensive value: that season's Defensive Box Plus/Minus (DBPM, points per 100 possessions against a league-average defender), shrunk toward 0 with the 300-minute prior and moved by the development swing (`docs/statistical_ratings.md`). On every play the five defenders' values are summed. One summed point is worth one point per 100 opponent possessions:

- two thirds through the opponent's make probability (`make_per_defense`, derived from the environment: a make is worth its points less the offensive-rebound value of a miss);
- one third through the opponent's turnover probability (`tov_per_defense`).

Rebounding already has its own rates, so it is left out to avoid counting it twice. Check: every player +1 on defense (+5 on the floor) lowered points allowed by 5.3 per 100 over 1,500 games.

Players without DBPM count as average defenders (0): veteran and rookie estimates, and Wade until his camp grade (roadmap item 9). Legacy 20-80 perimeter/interior grades keep their old small effect.

## Rotations and availability (problem E3, roadmap item 8)

A player input has minutes per game when he plays and an availability, the chance he is available for a game (default 1).

- Real clubs (`"rotation": "real"`): minutes per game played and games played over the club's games, from the real season roster (world model D). This uses season totals only, never dates.
- Before the tip the engine draws each player's availability, then dresses up to 12 in rotation order (most minutes per game first). With fewer than 8 available, the next players are added back (hardship).
- Targets fill 240 minutes in rotation order: each player gets his average until the game is full, so a deep bench sits when everyone is healthy. When short-handed, the shortfall is spread in proportion to the averages, up to 8 minutes above a player's average and no higher than 42 (or his own average if that is higher); only if that still leaves minutes do the caps give way, up to 48.
- Conflict rule 3 (`AGENTS.md`): departing players' minutes go first to arrivals up to their own previous share; the rest raises the staying players' minutes in proportion to their real minutes.

Season shares divided over a top-12 list gave LeBron James 42.9 minutes every night; he now plays his real 39.5 on the nights he plays.

## Late game (problem E4)

In the 4th quarter and overtime:

- **Closing lineup:** the last 5:00 of a game within 10, and all of overtime, go to the five players with the largest targets.
- **Garbage time:** the bench takes over when the 4th-quarter lead reaches 15 plus 1 per minute left (27 at 12:00, 21 at 6:00).
- **Foul when trailing:** down 1-3 with 24 seconds or less (the game clock under the shot clock), down 4-6 with 45 or less, down 7-10 with 75 or less. The foul takes 1-4 seconds and gives two free throws to the ball handler. A team down more than 10 concedes. Fouls go to players who can afford them.
- **Run the clock:** a leading team inside the last 2:30 uses 14-24 seconds.
- **Trailing offense:** inside 2:30 it hurries (4-16 seconds); down 1-3 with the shot clock off it takes a good shot and leaves 2-8 seconds. Down 3 or more inside the last minute, at least 60% of its shots are threes (95% when down exactly 3 with the shot clock off).
- **Last shot:** in every period, a possession that starts with the shot clock off holds for the last shot. That final, set-defense shot converts at 0.7 times the normal rate. A possession with under 3 seconds gets a shot off only in proportion to its time.

League averages already contain late-game fouls: this logic adds about 1.5 free-throw attempts and 0.8 fouls per team per game on 2003-04 rosters, so the regular trip and foul rates (and real players' free-throw rates) leave that amount out.

## Score effect

Independent possessions alone give a game-to-game spread of about 15 points. Real NBA results vary about 12 points around the betting line, because a leading team relaxes and a trailing team presses. The kernel moves the offense's make probability by 0.0015 per point of its lead (gained when trailing), up to 25 points. That also pulls back steady edges, so the home edge input is scaled up to keep the environment's home advantage (`attenuation` in `calibrate`). Team quality is not scaled; its spread was checked instead (below).

## Foul trouble (problem E5)

A player sits once he reaches 2 fouls in the 1st quarter, 3 in the 2nd, 4 in the 3rd, and 5 in the 4th until the last 5:00. He leaves at that dead ball if the bench has someone without foul trouble, and returns when the period changes or the limit lifts. A player one foul from disqualification fouls at a quarter of his normal rate (he defends carefully).

## Calibration record

Real 2003-04 rosters with real minutes and availability, 6,000 games, kernel 2003.3. Benchmarks are general figures for the era, not 2003-04 results.

| Measure | Kernel 2003.2 | Kernel 2003.3 | Benchmark |
| --- | ---: | ---: | --- |
| Points per team per game | 95.2 | 95.0 | 95.1 (2002-03 environment) |
| Final-margin SD | 15.8 | 13.7 | 13-14 |
| Overtime games | 2.8% | 5.4% | 5-7% |
| Home win rate | 59.5% | 57.9% | 57-63% |
| Foul-outs per game | 0.75 | 0.23 | 0.2-0.3 |
| Spread of team average margins, 82-game season | about 3.3* | 4.0 | 4-5 |
| LeBron James minutes per game (real 39.5) | 42.9 | 39.7 | his real average |

\* Measured before this metric existed, as the raw spread over 1,500 games with top-12 season shares.

Box totals per team: FGA 81.2 (80.8), FTA 24.7 (24.4), turnovers 15.1 (14.9), offensive rebounds 12.2 (12.0), assists 21.7 (21.5); environment values in brackets. Three-point attempts run at 15.7 against 14.7 because the 2003-04 real players shoot more threes than the 2002-03 environment. The best clubs come out San Antonio, Indiana, Minnesota, Sacramento and Houston; the worst Orlando, Atlanta, Washington, the Clippers and Chicago.

Known gaps: the realized home margin is about 2.5 points against the 3.0 assumption; team pace is uniform (problem E6); there are no injuries or fatigue (problem E7, roadmap item 12).
