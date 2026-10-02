# Game engine

Kernel `2003.1`, schema `1`.

## How a game gets played

1. A game request file, `Game_N.request.json`, is committed next to its `Game_N.md` note (format in `runtime/game_requests.py`). Repository validation checks every request, so a bad one fails the build and never deploys.
2. Pushing to the branch Railway tracks rebuilds the engine. On startup it plays every request it has not played before and keeps the result on the volume.
3. The result is public at `https://<railway-domain>/games/<event_id>/box` (box score) and `/games/<event_id>` (full JSON). `/games` lists every request and its status.
4. The result becomes canonical only when it is written into the game note and committed.

Before a game is drawn, its event id and the SHA-256 of its inputs are journaled with the secret career seed on the Railway volume. Re-deploying replays a played game identically. Editing a played game's request is refused (`altered packet refused`, shown in `/games`) and the original result stays, so a result cannot be re-rolled. `run_game` has no seed parameter, and `architecture_errors()` checks that the journal entry always precedes the draw.

## Era

`runtime/era.py` holds two kinds of era knowledge:

- **Rules by season** (`SEASON_RULES`): 12 game-day actives, injured list, zone defense legal with defensive three seconds, no hand-check emphasis yet (that begins 2004-05), no play-in (begins 2020-21), best-of-seven first round. A season without a row fails closed; add the next season's row before the career clock enters it.
- **League environment**: a season is calibrated on the last *completed* season, read from `library/<year>/league/nba_<season>_league_environment.json`, and only once that file's `published_after` date has passed for the game date. 2003-04 games run on the 2002-03 environment. A season's own final averages are never used to play it.

The 2002-03 environment is marked `provisional`: its values were entered from recollection of Basketball-Reference league averages and need a line-by-line check against the source named in the file.

## Kernel

Per-play probabilities (turnover, free-throw trip, field-goal attempt, three-point share, make rates, and-one, offensive rebound, assist, steal, block, non-shooting fouls) are derived from the environment's per-game averages. Two neutral clubs reproduce the era's scoring, shot volume, threes, free throws, turnovers and offensive rebounds within a few percent (`tests/test_engine.py`). Defensive rebounds run high because team rebounds are credited to players.

Players carry optional ratings on a 20-80 scale (`three_point_shooting`, `mid_range_shooting`, `rim_finishing`, `free_throws`, `ball_handling`, `passing`, `rebounding`, `perimeter_defense`, `interior_defense`, `usage`). A missing rating is league average (50). Player cards are `Unassessed`, so every player currently plays as league average until the simulation grades them. The position profiles and the home edge are provisional structural assumptions, not sourced league data.

Rotation follows each player's minute target (sum 240). Six fouls disqualify. Overtime is five minutes.

`runtime/league.py` builds a baseline rotation for background clubs from the library depth order. It is a default, not a coaching decision; Miami's rotation belongs to the AI/GM records.

## Railway deployment

`railway.json` points Railway at `Dockerfile.engine`, whose first stage runs repository validation and the full test suite, so a failing check blocks the deploy. The service uses only the Python standard library.

One-time setup (already done for this repository):

1. Railway project deploying this repository's tracked branch, with the Railway GitHub App installed on the repository.
2. A volume mounted at `/data`. It holds the career seed and every result; losing it means played games can no longer be reproduced. Turn on volume backups if the plan offers them.
3. Variable `ENGINE_API_TOKEN`, at least 32 random characters. It protects `/ready` and `/corrections` only; results are public.
4. Optional: variable `RAILWAY_DOCKERFILE_PATH=Dockerfile.engine`, so Railway never falls back to automatic detection.
5. A generated public domain.

After that there is nothing to run locally. The deploy log lists each request as `played`, `already_played` or `error`.

A kernel version change is journaled in `kernel_transitions` and does not alter the seed or any played game.
