# How this repository works

A handoff guide for any assistant or person picking up the project. Read this first, then `AGENTS.md`, which is the binding rulebook. Where this guide and `AGENTS.md` disagree, `AGENTS.md` wins.

## 1. What the project is

An alternate-history NBA career simulation of **Dwyane Wade**, starting at the June 26, 2003 draft (No. 5 pick, Miami Heat).

- **The user** controls only Wade's own decisions: contract replies, requests to the front office, training choices, role requests.
- **An AI general manager** controls Miami: signings, cap, roster, depth chart, rotation and trades. The user can react as Wade but can't author Miami's decisions.
- **The other 28 clubs** follow real history: real rosters, real minutes and real transactions. They have no simulated front office.
- **Miami is fully simulated.** Real moves involving Miami are skipped, under the conflict rules in `AGENTS.md`.
- **Wade's career is alternate history.** His ability starts from the college statistics in his profile, and his record comes only from simulated games. Real Wade statistics and awards are never imported.
- **Real players' ability** follows their real seasons, with an engine-drawn swing. This is option C in `AGENTS.md`.

## 2. Where things are

| Path | What it holds |
| --- | --- |
| `AGENTS.md` | The rules: authority, no hindsight, world model, engine, statistics, after-event checklist |
| `docs/ROADMAP.md` | What is built and what is still missing, in career-clock order |
| `docs/front_office_design.md` | Free agency, contracts, answer model, roster rules, trades, camp |
| `docs/engine_model.md` | The game engine's model and calibration |
| `career/Dwyane_Wade/` | The career: profile, season folders, statistics, milestones, contracts |
| `career/Dwyane_Wade/2003-04/current_state.json` | **The career clock.** It is the only authority on "today". |
| `career/Dwyane_Wade/2003-04/00_Team/` | Miami's records (simulation-owned): roster register, depth chart, rotation, finances, cards |
| `career/Dwyane_Wade/2003-04/01_Free_Agency/` | Negotiations, plans, Wade's requests (`wade_requests.json`), Wade's rookie contract |
| `career/Dwyane_Wade/2003-04/04_Training_Camp/` | Camp roster, decisions, the October 27 correction (`signing_corrections.json`) |
| `career/Dwyane_Wade/Stats_and_Awards/` | Generated statistics pages: Wade, Miami (`Team/`) and league (`League/`), plus 407 league player cards |
| `library/<year>/league/` | Real-world data: rosters, contracts, transactions, schedules, cap rules, colours, player stats |
| `library/careers/nba_player_careers.json` | Real players' season rates, used by the engine for their ability |
| `runtime/` | All logic (Python, standard library only) |
| `scripts/` | Command-line drivers (each has a docstring with its usage) |
| `tests/` | About 460 unit tests; `tests/checkpoint.py` freezes the June 26 checkpoint for tests |

## 3. The game engine and draws

- **Railway.** The engine runs on Railway (`Dockerfile.engine`, `railway.json`, `scripts/serve_engine.py`). Railway deploys the **`milestone-1`** branch after its checks pass.
- **Every chance event is drawn by the engine, never locally.** A game is a `Game_N.request.json`. A decision (a free agent's answer, an injury, a camp battle, a consent) is a `*.decision.json` with options and probabilities.
- **Never re-rolled.** The engine stores the first draw for every event id forever and refuses a changed packet under the same id. Never pass a seed, never edit a drawn request, never resolve a game or decision locally.
- **Games.** They need a push to `milestone-1` and a Railway redeploy, because the engine reads the repository's dated inputs at boot. Results are then fetched with `python scripts/collect_results.py`. The `collect-results` GitHub workflow also runs hourly and on every push to `milestone-1`.
- **Decisions.** They can be drawn at once through the authenticated `POST /decisions` route: `python scripts/draw_decisions.py`. It needs the environment variable `ENGINE_API_TOKEN`. **The token is a secret: it is never written into the repository or chat.** Without the token, decisions go the slow way: commit, push, deploy, collect.
- **Canonical results.** A result counts only after it is written into the career record. `scripts/write_back_results.py --write` writes game results into notes and statistics pages.

## 4. How the clock moves (the loop)

Each driver processes days in order and **stops** when a draw is missing or Wade must answer. The loop:

1. Run the driver for the phase up to a target date.
   - Free agency: `python scripts/run_free_agency.py --write <date>`.
   - Camp and preseason: `python scripts/run_camp.py --write <date>`. Its stages are 2003-09-30 (invites and injuries), 10-05 (preseason requests), 10-24 (evaluation and rotation) and 10-27 (the cut).
   - Regular season: `python scripts/build_season_games.py --write <date>` for Miami and `python scripts/build_league_slate.py --write <date>` for the other games.
2. If it stopped on pending draws, run `python scripts/draw_decisions.py`. For games, push and wait for Railway, then run `python scripts/collect_results.py`. Then run the driver again.
3. If it stopped on a question for Wade, ask the user and record the reply. See `docs/live_player_milestones.md` and `scripts/player_milestone.py`.
4. Write back results: `python scripts/write_back_results.py --write`.
5. Before every commit: `python scripts/validate_repository.py`, `python scripts/update_player_reports.py --check`, `python scripts/build_league_cards.py --check`, and `python -m unittest discover -s tests`.
6. Commit to the working branch, open a pull request into `milestone-1`, **wait for its checks to pass**, then merge. Railway deploys only green `milestone-1`. Merging red once stalled the engine for 40 minutes.

Commit in batches, about every couple of weeks of career time or at any stop that needs the user.

## 5. Main systems

- **Free-agent market** (`runtime/market.py`, `runtime/valuation.py`). The unsigned pool on a date, asking prices and real exits.
  - A player is available only if three things hold: he is a free agent in the data, he has no real move dated on or before the date, and he is not restricted. A restricted player needs an offer sheet his club may match.
- **Answer model** (`runtime/player_utility.py`, `runtime/club_strength.py`). A player scores Miami's offer against his real alternative on seven factors: money, security, tax tier, role, contention, loyalty and market.
  - Contention and role come from every club's roster **on the date, with him on it**.
  - Weights depend on age and on a drawn trait. The gap between the two scores sets the accept, counter and reject odds, and the engine draws the answer.
- **Miami's GM** (`runtime/gm.py`).
  - **Ceiling.** Plans under a $57M owner payroll ceiling with no tax.
  - **Holds and exceptions.** Handles cap holds, the mid-level exception and Bird rights.
  - **Later seasons.** Every later season of an offer must also fit under the ceiling.
  - **Valuation.** Walks away above its valuation.
- **Negotiations** (`runtime/negotiation.py`, the contract desk), **signing write-back** (`runtime/signing.py`), **trades and sign-and-trades** (`runtime/trades.py`, `scripts/run_trade.py`).
- **Wade's voice** (`docs/front_office.md`).
  - **Requests.** They are logged in `wade_requests.json`.
  - **Weighing.** A request is weighed by his **standing** (`runtime/standing.py`): unsigned_rookie, rookie (current), starter, all_star, franchise. The chance it overrides the GM's rule equals the standing weight times one minus the rule's margin.
  - **Franchise consultation.** At franchise standing, Miami must ask him before adding another star.
- **Roster rules** (`runtime/camp.py`, `runtime/refill.py`).
  - **Who dresses.** Only signed players, under one shared rule (`camp.playable`).
  - **The cut.** Releases invitees first and the rotation last.
  - **Unsigned draft rights** don't count toward the 15.
  - **Refill.** Open spots are filled from truly available free agents.
  - **Validation.** It checks these rules on every run.
- **Statistics and cards.**
  - **Generated pages.** `runtime/player_reports.py`, `runtime/write_back.py` and `runtime/league_cards.py`. Every page is generated: edit the source record, never the page.
  - **Refresh.** `scripts/refresh_career_views.py` rebuilds reports, league cards and statistics pages together.

## 6. Where the career stands (October 27, 2003)

- **Wade.** Signed July 21, 2003 to his rookie-scale deal. The user's counter: 80% protected, incentives to 120% of scale, team option for 2006-07. His standing is `rookie`. In the rotation he comes off the bench at 20 minutes, as the first guard.
- **Miami's 15.** Mike James, Eddie Jones, Caron Butler, Scott Padgett and Brian Grant start. The bench is Stephen Jackson, Shawn Kemp, LaPhonso Ellis, Cherokee Parks, Rasual Butler, Anthony Carter, Sean Lampley, Udonis Haslem and John Wallace. Jerome Beasley holds unsigned second-round rights.
- **Preseason.** Miami went 2-5. Wade played only Games 1 and 2, because of a dressing rule since fixed.
- **Free agency.** Kidd stayed in New Jersey. Miller and Odom were requested by Wade but not pursued for lack of cap room. Haslem was signed on October 27: Wade's request broke a tie at the last roster spot.
- **The October 27 correction.** Five camp signings were voided because the players weren't truly available. Real moves, with sources, were added to the transactions file.
- **Next.** Opening night is October 28, 2003, at Philadelphia.

## 7. Rotation reviews and remaining work (see `docs/ROADMAP.md`)

**In-season rotation reviews are built.** The staff reviews Miami every fourteen days after its October 24 camp assessment: November 7, November 21, and so on through the regular season. The October 27 roster correction does not reset that schedule. Run `python scripts/review_rotation.py --write <date>` when a review is due; the game builder waits for it before writing later game requests.

The staff ranks the signed roster by production per minute from closed regular-season games strictly before the review date. Each player's fixed preseason estimate carries the weight of 300 minutes; the score adds observed efficiency on the same per-30-minute scale. The prior loses weight as minutes accumulate, so a few hot or cold games have limited influence. Camp evaluation scores supply the estimates. Later camp arrivals use their dated recruitment value: Cherokee Parks 7.13, Udonis Haslem 5, and John Wallace 5 from the October 27 signing correction. Recruitment fit and Wade's requests do not add a starting-job bonus.

At each position, a clear leader gets the job. When the top two scores are within 10%, an unchanged engine decision packet decides the battle once, giving the leader a 50%–75% chance. Collect those draws and rerun the review command to complete the rotation. Seniority and draft slot provide no protection. Reviews save their evidence, decisions, depth chart and rotation under `00_Team/Team/Depth_Chart/Reviews/<date>/`; already-written game requests keep their lineups. An injury replacement's actual start is recorded in the game result and counts in reports and standing under the existing standing rules.

Remaining work:

1. **Standings, tiebreakers and the playoff bracket** (roadmap item 14), before April 2004.
2. **Season awards vote** (item 15), before April 2004.
3. **The 2004 draft** (item 17) and **season rollover** (item 18), before summer 2004.

## 8. Hard rules that are easy to break

- **No hindsight.** The front office knows only what was public on the career date. Never use a future result, signing or statistic.
- **Never fix a canonical result.** Never edit a played game's request or a drawn decision to change an outcome.
- **The real Wade is off limits.** Never import his statistics, awards or biography into the simulation. The profile at `career/Dwyane_Wade/Dwyane_Wade_Player_Profile.md` is the canon.
- **Don't invent sources.** No invented facts, photos or sources for real people. Unknown stays "Not recorded", and inferences are labelled.
- **Ask about Wade, not about Miami.** Ask the user only about Wade's decisions, never to approve a Miami move.
- **Commits.** Don't put model names in commits or pull requests. The engine token never goes in the repository.
- **Tests follow the clock.** Tests read the live career date. Tests that describe the June 26 checkpoint use `tests/checkpoint.py`. Keep both kinds working when the clock moves.
