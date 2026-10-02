# Game engine

Kernel `2003.3`, schema `1`.

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

The 2002-03 environment now uses the supplied Basketball-Reference averages and retains their provenance. Statistical estimates and structural modeling assumptions remain provisional; see [the veteran rating method](../docs/statistical_ratings.md).

## Kernel

Per-play probabilities (turnover, free-throw trip, field-goal attempt, three-point share, make rates, and-one, offensive rebound, assist, steal, block, non-shooting fouls) start from the environment's per-game averages. Isolated neutral-club tests check era totals. Unassigned team turnovers are separated from individual turnovers; not every missed field goal is credited as an individual rebound.

Requests automatically attach 2002-03 statistical profiles to matched veterans. Use a verified `bbr_id` on explicit player entries; recognized names/IDs also work. Shooting frequency and accuracy, free-throw drawing and accuracy, and offensive/defensive rebounding are separate inputs. The complete environment, source hash, model version and selected rates are frozen in the game packet.

Unmatched players retain optional legacy ratings on a 20–80 scale (`three_point_shooting`, `mid_range_shooting`, `rim_finishing`, `free_throws`, `ball_handling`, `passing`, `rebounding`, `perimeter_defense`, `interior_defense`, `usage`), defaulting to neutral 50. That fallback is not a scouting assessment. For matched veterans, statistical inputs replace overlapping legacy ratings; only independently assessed perimeter/interior defense grades may be supplied alongside them. Display grades on cards are not engine inputs. Position fallbacks, home edge and other structural assumptions remain provisional.

Kernel 2003.3 adds team defense, availability-based rotations, late-game logic, foul trouble and a score effect. The model, its constants and the calibration record are in [docs/engine_model.md](../docs/engine_model.md); `python scripts/engine_diagnostics.py 4` re-runs the check: four seasons of the real 2003-04 schedule between real rosters on their dates (analysis only, nothing is written; add `--defense-test` or `--home-test` for the paired checks).

Rotations: a club is an explicit `players` list (Miami's AI/GM states its rotation this way; minutes sum to 240), `"rotation": "real"` for a real club's real roster on the game's date, with minutes per game and availability, less any player simulated Miami holds (`runtime/rotations.py`, roadmap item 8, world model D), or a `baseline` library file. With availabilities the engine draws who is available, dresses up to 12 in rotation order and fills 240 minutes. Six fouls disqualify. Overtime is five minutes.

`runtime/league.py` builds the older baseline rotation for background clubs from the end-of-2002-03 depth order. It is a default, not a coaching decision; Miami's rotation belongs to the AI/GM records.

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
