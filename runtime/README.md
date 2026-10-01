# Game engine

Kernel `2003.1`, schema `1`.

## How a game is resolved

1. `runtime.game_runner.run_game(home, away, event_id=..., game_date=...)` validates both clubs against the season's era rules and freezes a canonical packet. Bad inputs fail here, before anything is journaled.
2. The packet's SHA-256 and event id go to the private engine-state service on Railway (`/events/close`). The service journals that identity, then returns an opaque reference derived from a secret career seed it never discloses.
3. The local kernel turns that reference into entropy and plays the game possession by possession.

The same event with the same packet always returns the same game. The same event with any changed input is refused (`altered packet refused`), so a result cannot be re-rolled by editing a rotation or a rating after the fact. `run_game` has no seed parameter, and `architecture_errors()` checks that closure always precedes the draw.

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

The service (`runtime/private_service.py`, entry point `scripts/serve_engine.py`) uses only the Python standard library. `railway.json` points Railway at `Dockerfile.engine`, whose first stage runs repository validation and the full test suite, so a failing check blocks the deploy.

One-time setup in Railway:

1. New project, deploy from the GitHub repository. The Railway GitHub App must be installed on the repository (not only authorized for login), or auto-deploy from `main` is unavailable.
2. Add a volume to the service mounted at `/data`. The career seed and journal live there; losing the volume loses the ability to reproduce closed games.
3. Set the variable `ENGINE_API_TOKEN` to a random string of at least 32 characters, for example `python -c "import secrets; print(secrets.token_urlsafe(48))"`. Optional: `ENGINE_DATABASE_PATH` (default `/data/engine.sqlite3`).
4. Generate a public domain under the service's networking settings.

Locally, export `ENGINE_RUNTIME_URL` (the Railway domain, with `https://`) and `ENGINE_API_TOKEN`, then run `python scripts/check_engine_readiness.py`. No secret belongs in Git.

## Snapshot binding

The service binds to the SHA-256 of the live `current_state.json`. The image computes it at build time. When a merged change to the current state reaches Railway, the new image starts **locked**: `/ready` reports `snapshot_advance_pending` and game closure is refused until `python scripts/advance_engine_snapshot.py "<checkpoint>"` is run from a merged `main` checkout. That compare-and-swap is journaled; the stored snapshot is never overwritten at startup. A kernel version change is journaled the same way (`kernel_transitions`) and does not alter the seed or any closed event.
