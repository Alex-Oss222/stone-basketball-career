# All-Star weekend games (roadmap 15b)

The engine plays the Rookie Challenge and the All-Star Game of every season with the same kernel as an NBA game, as it plays the FIBA games: the exhibition has its own rules row, an environment built from the real editions played before it, and a translation of each player's NBA profile into exhibition terms. The rosters are the season's recorded All-Star selections (`all_star.json`, `runtime/all_star.py`); nothing here re-decides them. The Saturday contests are not played (below).

## The parts

| Part | File | What it does |
| --- | --- | --- |
| Research | `library/all_star/games/<year>-<game_type>.json`, `library/all_star/anchor_seasons.json` | The real All-Star Games (1998, 2000-2005) and Rookies-versus-Sophomores games (2000-2005; 2000 excluded) from their Basketball-Reference box pages: date, final, overtimes, MVP, team totals as published and every player's line. The real Wade's lines are flagged `protagonist_real_history`. The anchors' regular-season totals and rates come from the pinned sumitrodatta copy of the Basketball-Reference bulk tables (commit `7f9b337`), the source already used for 2002-03. |
| Rules | `runtime/era.py` (`EXHIBITION_RULE_PERIODS`, `exhibition_rules`) | Date-gated rows; a date outside them fails closed. The researched statuses are in each season's calendar (`library/<year>/league/nba_<season>_all_star.json`, `research.engine_rules`). |
| Engine files | `scripts/build_all_star_engine.py` (`--check`), `library/all_star/engine/<season>-<game_type>.json` | Environment, translation and minutes template of each game. A locked game's file is never rewritten (below). |
| Engine | `runtime/kernel.py`, `runtime/game_runner.py`, `runtime/all_star_engine.py`, `runtime/game_requests.py` | The exhibition packet, the translated profiles and their check. NBA and FIBA games take exactly the path they took before. |
| Games | `runtime/all_star_games.py`, `scripts/all_star_day.py` | The lock, the requests, Wade's notes, the MVP, Wade's award, the page and the validation. |
| Records | `Stats_and_Awards/League/<season>/all_star_games.json` and `All_Star_Games.md` | The locks and MVPs, and the page with results, box scores, locks, environment and MVP tallies. |

## Rules

- **All-Star Game.** Standard NBA rules: four 12-minute quarters, 5-minute overtimes, a 24-second clock, six fouls, twelve dressed. Every box from 1997 totals 240 team minutes (2003's two overtimes 290), and no source before the 2004-2006 games states a deviation.
- **Rookie Challenge.** Two 20-minute halves (the kernel's `quarters` are its periods, so 2) and 2-minute overtimes, nine a side, fouls counted but nobody fouls out (`foul_out_limit` None). Halves and overtime are sourced in the 2004 and 2006 releases; no foul-outs only for 2004 (the 2005 box fits it: Al Jefferson, 6 fouls in 21 minutes). Not modelled: the team-foul penalty after ten, the 20-second timeouts and the clock stopping after made baskets.
- **Kernel.** Each addition acts only when its key is present, so NBA and FIBA games are unchanged (pinned digests in `tests/test_all_star_engine.py`):
  - `team_errors` accepts an `exhibition_model` profile key, only under the exhibition competition;
  - `calibrate` scales `make_per_defense` and `tov_per_defense` by `engine_assumptions.defense_intensity` when present (no NBA or FIBA environment carries it);
  - `calibrate` multiplies the half-court possession seconds by `engine_assumptions.possession_seconds_factor` when present (0.97 here; no NBA or FIBA environment carries it either);
  - in `resolve_game` a `foul_out_limit` of None means no disqualification and no foul-trouble sitting; the intentional-foul and careful-defender weights keep the nominal six; no random draw is added;
  - the result checks (`shot_events.spatial_result_errors`, run by the kernel and the collector) read an exhibition's period layout from `era.exhibition_layout` (the Rookie Challenge's two 20-minute halves and 2-minute overtimes); every other result is checked against four periods of at most 12 minutes as before.
- **Kernel version** stays `2003.11`: the FIBA rules came in without a version change, and a new version would fail closed on any journaled event without a saved result.

## Environment, translation and defense

- **Environment.** The real editions of the same game published before it: the five most recent All-Star Games (1999 had none), the Rookies-versus-Sophomores games from 2001, up to five. The 2000 Rookie Challenge is excluded (incomplete minutes, overtime length not recorded). Team totals as published (the real Wade's included, as in the NBA and FIBA environments), each team-game scaled to regulation by its overtimes, averaged per 48 or per 40 minutes. Team turnovers 0. Published the day after the last baseline game. The builder refuses a game whose previous year's real edition is not researched (`NO_GAME` names a year without one), and a baseline line whose season is missing from the anchor file, so a later game can never be built on an older baseline or a thinner fit without an error.
- **Translation.** Each anchor's line in a baseline game against his own regular season (at least 300 minutes; never the real Wade):
  - two-point, three-point and free-throw percentages move by a logit shift from pooled makes against expected makes on the same attempts;
  - three-point attempts, free-throw attempts and turnovers per field goal attempt change by a ratio pooled by attempts; fouls per minute pooled by minutes; usage, assist, rebound, steal and block rates by the FIBA minute-weighted ratio, with baselines equal to the anchors' own rates in the games.
  - **Shrinkage (a stated deviation from the design's "about 100 attempts or minutes").** Only the three-point and free-throw shifts are shrunk toward no change (100 attempts; their samples are 73 to 230 attempts). The two-point shift and the ratios stay unshrunk: their samples are large, every edition differs from the NBA in the same direction, so a pull toward no change is a known bias (in the probe it cost 2 to 4% of scoring and added 10 to 20% free throws), and only the raw ratio keeps the anchors' translated mean on the baselines.
- **Defense.** Individual defensive values are off (`defense_intensity` 0): the translation is fitted on real exhibition games and already contains the defense played in them.
- **Pace.** From the environment through `calibrate`: about 116-118 possessions per 48 minutes (All-Star Game), 104 per 40 (Rookie Challenge), with the half-court possession seconds multiplied by 0.97 (`possession_seconds_factor`): holding for a period's last shot, the four-second floor and the late-game clock were balanced at NBA possession lengths and otherwise cost about 2% of an exhibition's possessions (the calibration record in `docs/engine_model.md`). Both teams play at pace 1.0 on a neutral court, rest 2, no injury or absence draws.

Fitted values (`translation` in the engine files):

| Game | Anchors | 2P shift | 3P shift | FT shift | 3PA rate | FTA rate | TOV/FGA | PF/min |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| All-Star Game 2004 | 119 | +0.088 | -0.071 | +0.014 | x1.328 | x0.432 | x1.104 | x0.791 |
| All-Star Game 2005 | 119 | +0.170 | -0.060 | -0.188 | x1.366 | x0.423 | x1.151 | x0.814 |
| All-Star Game 2006 | 118 | +0.130 | -0.035 | -0.303 | x1.335 | x0.402 | x1.187 | x0.843 |
| Rookie Challenge 2004 | 54 | +0.391 | +0.072 | -0.221 | x1.196 | x0.410 | x1.252 | x0.620 |
| Rookie Challenge 2005 | 71 | +0.510 | +0.036 | -0.283 | x1.263 | x0.394 | x1.112 | x0.587 |
| Rookie Challenge 2006 | 88 | +0.490 | +0.060 | -0.242 | x1.221 | x0.438 | x1.041 | x0.605 |

The calibration record is in `docs/engine_model.md` (All-Star weekend).

## The lock

On the game's date, from results closed through the day before (`all_star_games.lock_game`):

- **All-Star Game:** the twelve a side after the Commissioner's replacements (`all_star.json` `game_rosters`) and their recorded five starters.
- **Rookie Challenge:** the panel's nine a side as recorded (a corrected roster as corrected, the dated correction of 2006-01-15). The Commissioner's test of the All-Star Game applies: a player who played in none of his club's last two games is out, and the panel's next available player of his side and position group takes his place. The panel's order is recomputed by `all_star.rookie_challenge_order` on the step's own date, under its correction's context for a corrected roster (`award_corrections.replaying`); the lock refuses when the recomputed nine differ from the recorded nine. The test flags six recorded players: Ginóbili, Stoudemire, Dunleavy and Daniels in 2003-04, Harrison and Hinrich in 2004-05. All six were rotation players who sat out their club's last two games: absences, not coach's decisions.
- **Ranking** within the starters and within the reserves (all nine in the Rookie Challenge, whose top five start), the same rule for everyone, Wade included: closed regular-season Game Score per game, then points per game, then the recorded selection order.
- **Minutes:** the baseline editions' minutes averaged by rank (starters and reserves apart where the box records them), each team-game scaled to regulation, normalized to 240 or 200 and rounded to whole minutes; a roster that is not twelve (or nine) uses the first slots, rescaled. The template counts every player's minutes, the real Wade's too: it is the coaches' rotation shape, not an ability fit.

| Game | Starters | Reserves |
| --- | --- | --- |
| All-Star Game 2004 | 30, 28, 26, 23, 19 | 23, 20, 18, 17, 14, 13, 9 |
| All-Star Game 2005 | 31, 28, 26, 23, 19 | 24, 21, 17, 16, 14, 12, 9 |
| All-Star Game 2006 | 30, 28, 25, 22, 18 | 24, 21, 18, 17, 14, 13, 10 |
| Rookie Challenge 2004 | 28, 26, 25, 23, 23 | 22, 19, 17, 17 |
| Rookie Challenge 2005 and 2006 | 29, 27, 25, 24, 23 | 21, 19, 17, 15 |

- **Position:** the one the engine used for the player in the last frozen game input of the season before the date (never a registry placeholder).
- **Selections as known on the lock date.** Every step the lock reads (the Rookie Challenge step; the starters, reserves and replacements behind the All-Star Game rosters, `all_star.rosters`) is read through `award_corrections.as_of(step, locked_on)`. Validation recomputes each lock from the records, except a lock one of whose steps was corrected after it: the current code then decides the corrected selection, while the lock read the one the career knew, so that lock stands as recorded.
- **Engine file.** The lock records the sha256 of its engine file (`engine_sha256`): the request is frozen against that file and the engine replays the game from it (its environment is journaled verbatim), so validation refuses any change and `scripts/build_all_star_engine.py` never rewrites a locked game's file (`--check` lists one whose fresh build differs as kept). A research correction or a builder change reaches only the games locked after it.
- **Profile:** `load_rating_index(game_date, season).engine_profile(...)`, exactly what an NBA game on that date reads (Wade's rookie estimate in 2003-04 and his protagonist profile after it, real players' trajectories with feedback, Bosh's alternate-history profile from 2004-05), translated. `_developed` reuses the season's journaled development event (`development_refs` returns the same reference for the same player and season), so no new swing is drawn. `_exhibition_packet` checks every profile against the translated dated profile with its development draws and fails closed without one.

## Requests, results and MVP

- **Event ids** are `<date>-rookie-challenge` and `<date>-all-star-game`; validation refuses any other id for an exhibition request, so a game cannot be drawn again under a new id.
- **Paths.** Wade's games sit beside his notes, `<season>/11_All_Star/{Rookie_Challenge,All_Star_Game}/Game_1.md` (`player_team`, `venue: neutral`, `competition: rookie_challenge` or `all_star`). Every other game is in `Stats_and_Awards/League/<season>/All_Star/Games/<event_id>.request.json` (only the 2005-06 Rookie Challenge so far). Both carry frozen inputs. The home side is the alphabetical first (East, Rookies) on a neutral court.
- **MVP** (`all_star_games.decide_mvp`), from the closed box: a media panel of 9 (the Finals MVP panel's size; the award's own is unverified), lens 0.30 to 0.60 spread evenly, one vote each, counted by `season_awards.tally_single`. Production is the mean z-score of Game Score and points among everyone who played; the second criterion is the z-score of being on the winning side. Equal ballots name co-MVPs in the All-Star Game (the 2000 precedent, Duncan and O'Neal) and go to one engine draw in the Rookie Challenge (`Award_Draws/<season>-rookie-challenge-mvp.decision.json`; never shared 2000-2005). On the real games the rule names the real MVP in 10 of the 13 researched editions; the misses were within about one point (2003 Rookie Challenge: Richardson 31 points against Arenas 30; 2005 All-Star Game: Jermaine O'Neal against Iverson, 15 points each; 2005 Rookie Challenge: Bosh's Game Score 33 against Anthony's 31 points). The 2004 fan share of the vote is not modelled (its weight is unverified).
- **Records.** The MVP is kept in the game's `mvp` block in `all_star_games.json` (with `recorded_on` when later than the game). `all_star.json` is not touched: a step with `recorded_on` there would flip the 2003-04 legacy date inference in `all_star.decision_dates`. Wade's MVP goes to `awards.json` as `All-Star Game MVP` or `Rookie Challenge / Rising Stars MVP`, competition `all_star` or `rookie_challenge` (the catalogue's names and competitions).

## A separate record

- No closed-results reader (standings, weekly, monthly and season awards, rotation reviews, the protagonist and trajectory updates, standing, valuation) reads `11_All_Star` or `All_Star/Games`; those readers take the regular-season and playoff folders only. `is_league_slate` leaves `All_Star` out, as it does `Playoffs`.
- The MVP names are not in `standing.HONOR_NAMES` and their competitions are not `regular` or `playoff`, so standing ignores them; valuation reads `all_star.json` selections and season awards only; `incentives.earned_honors` leaves out exhibition competitions (its substring match on "All-Star" would count the MVP); the national-team committee reads neither.
- The MVPs appear under Other honors on the season's award hub, on league cards and on followed-player pages, from the later of the game date and `recorded_on`. Wade's statistics are his own pages per season (`<season>/11_All_Star/`) and career rows, never added to NBA totals; their engine shots stay out of the NBA shot record.

## Dates and the retroactive weekends

- **Dates** from the season calendars: 2004-02-13 and 2004-02-15, 2005-02-18 and 2005-02-20, 2006-02-17 and 2006-02-19. The schedules have no NBA game from Friday to Monday of each weekend.
- **Why playing them after the fact is allowed.** They are separate exhibition records that nothing recorded since reads; every input is dated before the game (rosters decided from results through each step's date, profiles as of the game date, environments from real games published earlier); each game is a new journal event, drawn once from the engine seed, with a request the records fully determine and validation recomputes. The 2003-04 selections themselves closed late (recorded on 2004-06-24), and `recorded_on` exists for this. The three weekends were locked and requested on 2006-04-19 (`--retroactive`, allowed on that date only) and carry `recorded_on: 2006-04-19`.
- **Validation's due date** is the later of the game date and 2006-04-19. A game must be locked and requested on its due date and have its result and MVP once the clock is past it, so a deploy never deadlocks while results are pending.
- **From 2006-07** the driver plays them on their dates (`scripts/advance.py`): `all_star_day` after the day's awards locks and requests the games dated on the day, `play` plays them, `all_star_after` in `close_day` writes Wade's notes, decides each MVP (a Rookie Challenge tie drawn by the engine) and rebuilds the pages. A game that passed without a lock is refused. The rules rows (`era.EXHIBITION_RULE_PERIODS`) and the 2006-07 engine files (`scripts/build_all_star_engine.py` `CONFIG`) must be added before February 2007, after researching the real 2006 All-Star Game and Rookie Challenge (`library/all_star/games`) and their players' 2005-06 seasons (`library/all_star/anchor_seasons.json`); the builder refuses the 2007 games without them, and without the files the lock fails closed and the driver stops.

## Playing the retroactive games

1. The implementation commit carries the code, the research and the built engine files, the docs and tests, and the six locks and requests written by `python scripts/all_star_day.py --write 2006-04-19 --retroactive`.
2. Merge and push. The build passes with the requests pending; the boot scan journals and plays all six.
3. `python scripts/play_games.py 2006-04-19` fetches the results (already played) through `POST /games`, checks them with `result_errors` and writes the result files. If the requests were not in the pushed commit, it plays them instead; that works only once the code and library are deployed, because the fingerprint must match.
4. `python scripts/all_star_day.py --after 2006-04-19`; if a Rookie Challenge MVP tie wrote a draw packet, `python scripts/draw_decisions.py` and `--after` again. Then `python scripts/reconcile.py` (or `update_player_reports.py` and `build_league_cards.py --write`), validation and the targeted tests; commit and push. The next boot replays them as already played. Do not use `advance.py`: the clock does not move.

## Saturday contests (not played)

They are not basketball games, so the possession kernel cannot play them; their fields and announcement dates are unresearched (the calendars list participant selection as "not found"); an invitation to Wade would be a player decision that stops the clock, and no standing rule covers it; the dunk contest is judged and has no statistical basis. A later contest module could draw each event once: the Three-Point Shootout's 25 balls in 5 racks with the money ball from the translated catch-and-shoot rate, fitted on real shootouts published before; the field by a dated invitation rule; Wade's answer by a standing rule the user sets; a title honor only, never statistics. The Skills Challenge and Shooting Stars would rest on judgement and come later.

## Sources (retrieved 2026-10-10)

- Box scores, finals, overtimes, dates and MVPs: `https://www.basketball-reference.com/allstar/NBA_<year>.html` and `NBA_<year>_rookie.html` (page digests in each research file).
- Anchor seasons: `https://raw.githubusercontent.com/sumitrodatta/nba-alt-awards/7f9b3375439b79cb4e62f66ae7d12160275c2863/2026/Data/Player%20Totals.csv` and `Advanced.csv`.
- Rules and dates: the three `library/<year>/league/nba_<season>_all_star.json` files, with the 2004 Rookie Challenge release (oursportscentral, realgm) and the 2006 release (insidehoops).
