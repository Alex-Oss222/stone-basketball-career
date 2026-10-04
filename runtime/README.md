# Game engine

Kernel `2003.8`, schema `1`.

## Detailed live career screens

The same deployment serves the actual player interface. `/` and `/career` open the detailed milestone desk; `/cards` and `/player` open Shooting and Awards. `/career/status` reports the career cutoff, season, screen version and deployed revision. `/games` remains the engine's JSON result listing.

`runtime/live_site.py` builds the screens from the normal canonical report builder at startup. The Docker image includes the runtime UI assets and the report configuration. Current career READMEs link the same generated screens and their complete Markdown fallbacks. The nine milestone views contain dated facts, full evidence, player responses and next checkpoints. The player's UFA/RFA/control state comes from the career, never a demo selector.

These are read-only views. The player answers through the established career workflow; owning event records and validated commands persist those decisions. Viewing a screen never runs a game, signs a contract or advances time. Generated source pages keep every table column. The real Shooting page uses only closed player boxes and explicitly recorded location feeds; an absent feed is visibly unavailable, and earned annual Awards exclude weekly/monthly recognition and unannounced results.

The event CLIs refresh reports after writes; direct record edits require `python scripts/update_player_reports.py`. Deploying `milestone-1` refreshes the public snapshot. `/ready` and `/corrections` retain their existing authentication, and the public routes cannot read the engine database or arbitrary filesystem paths.

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

Kernels 2003.3 to 2003.5 add team defense, availability-based rotations, late-game logic, foul trouble, a score effect, team pace, back-to-back fatigue and injuries for Miami. The model, its constants and the calibration record are in [docs/engine_model.md](../docs/engine_model.md); `python scripts/engine_diagnostics.py 4` re-runs the check: four seasons of the real 2003-04 schedule between real rosters on their dates (analysis only, nothing is written; add `--defense-test` or `--home-test` for the paired checks).

Kernel 2003.6 added usage-dependent shooting efficiency, teammate passing effects, interior/perimeter defensive specialization, and transition after steals and defensive rebounds. Kernel 2003.7 chooses a sourced distance band and modeled court location before each FGA, then records its outcome in the immutable result. The full prior-season spatial environment is journaled only in new packets. Zone efficiencies preserve the possession's existing mean make probability. Interior defense still uses all two-point shots as its proxy; individual matchups, size and chemistry are not modeled.

Kernel 2003.8 adds optional prospect scouting style: extra turnover sensitivity to positive team defense, rebounder-specific transition opportunities and normalized spatial weights. `rookie-2003.2` also supplies a paint-pressure FTr prior and a dated position rebound split. These generic assumptions apply prospectively from November 12, 2003; earlier game inputs retain the archived rookie model. Wade's development event is unchanged. See [scouting assumptions](../docs/statistical_ratings.md#scouting-assumptions-and-their-scope).

`python scripts/engine_diagnostics.py 4 --check --summary-json /tmp/engine-summary.json` checks aggregate boxes, shooting, spatial coverage and conditional zone shares against the real prior-season sources. New results contain actual `started` flags, `transition_stats`, complete `shot_tracking` provenance and `shots`. Closed events feed Wade's and league-player charts, with a separate **Tracked games only** cohort for periods containing older locationless games. Existing stored results stay unchanged across upgrades and edited packets are refused. See [spatial sources](../docs/shot_environment_sources.md) and [calibration](../docs/spatial_calibration.md).

Rotations: a club is an explicit `players` list (Miami's AI/GM states its rotation this way; minutes sum to 240), `"rotation": "real"` for a real club's real roster on the game's date, with minutes per game and availability, less any player simulated Miami holds (`runtime/rotations.py`, roadmap item 8, world model D), or a `baseline` library file. With availabilities the engine draws who is available, dresses up to 12 in rotation order and fills 240 minutes. Six fouls disqualify. Overtime is five minutes.

`runtime/league.py` builds the older baseline rotation for background clubs from the end-of-2002-03 depth order. It is a default, not a coaching decision; Miami's rotation belongs to the AI/GM records.

## Game builders (roadmap items 10 and 11)

Nothing is written by hand. Both builders read the season schedule (`library/2003/league/nba_2003_04_schedule.json`), write a game only on or before its date in a run, never write a blank placeholder, never rewrite a request that exists, and are idempotent; `--check <date>` reports what is due and unwritten and checks what is written, without writing. Logic: `runtime/season_games.py`.

- `python scripts/build_season_games.py --write <date>` (Miami, item 10): for every Miami regular-season game on or before the date with no note yet, the note `06_Regular_Season/<month>/Week_N/Game_N.md` (the `scripts/create_game_note.py` record: scheduled, competition regular, `event_id`, `result_file: Game_N.result.json`; games numbered in date order within their week) and `Game_N.request.json` next to it. Miami's side is the camp decision, `00_Team/Team/Depth_Chart/rotation.json` (240 minutes in rotation order, written October 24 by `scripts/run_camp.py`): players the engine's injury draws keep out (`runtime.injuries.injured_out` over Miami's closed preseason and regular-season results in date order, less the Miami games already on the calendar since the last closed result) are left out, the next man on the staff's depth chart who is not in the rotation takes the last rotation slot's minutes (the staff's standing rule, a judgement), and the minutes are re-scaled to 240; Wade's `perimeter_defense` rating is carried from `00_Team/Team/defensive_grades.json` while a grade is in force on the game date, and no other ratings are sent. The opponent is `"rotation": "real"`. Every request passes `runtime.game_requests.load_request` before it is kept, and the generated player report pages are rebuilt afterwards (`scripts/update_player_reports.py`). The builder refuses to run without the camp rotation.
- `python scripts/build_league_slate.py --write <date>` (the league, item 11): a request for every non-Miami regular-season game on or before the date, `career/Dwyane_Wade/Stats_and_Awards/League/2003-04/Games/<game_id>.request.json` (both clubs `"rotation": "real"`, game_type regular, venue home) with a README. Railway finds them like any request and `scripts/collect_results.py` writes `<game_id>.result.json` beside each; a result there is a league record for standings and league statistics, never a player's game record (there is no game note). Every written request is checked structurally (exact fields, both clubs in the season's roster file, agreement with the schedule's game, not Miami); the engine's `load_request` runs on a deterministic sample (first, last and every 25th written) because it costs about 0.2 s a request and the full 1,189-game slate would take minutes; `--validate-all` runs it on every request. Repository validation applies the same rule: the full engine check for every Miami request, structure for the whole slate plus the sample, and unique event ids across both (`runtime.game_requests.request_errors`). The script first confirms that the schedule's club names are the roster file's.

- `python scripts/write_back_results.py --write` (the write-back, item 13; `runtime/write_back.py`, `docs/player_statistics.md`): after `scripts/collect_results.py` has saved the engine's answers, every result beside a scheduled Miami note dated on or before the career clock is written into the note (played, score, box score, Miami injuries), the phase/week note and the injured player's Miami card; then the player reports, the Miami team pages, the league pages and the league cards are rebuilt from the closed results. `--check` verifies; repository validation refuses an unwritten result.

## Fortnightly staff reviews

During the regular season, run `python scripts/review_rotation.py --write <date>` for the staff's fortnightly reviews before building games past their due dates. Close all earlier games first, collect any engine-drawn starting battles, then rerun the review command. The builder uses the newest dated `Depth_Chart/Reviews/<date>/rotation.json`, falling back to the immutable camp rotation before the first review. `--check <date>` validates reviews without writes. Existing requests retain their original lineups, and injury replacement starts count normally. Full rules: [fortnightly staff reviews](../docs/front_office.md#fortnightly-staff-rotation-reviews).

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

## Decisions drawn on demand

`POST /decisions` (bearer token) takes one decision packet, the exact content of a committed or about-to-be-committed `*.decision.json`, and returns the engine's draw: `201` and `status: decided` the first time, `200` and `status: already_decided` with the same outcome afterwards, `409` for a changed packet under an event id already drawn or a packet that breaks the decision schema, `401` without the token, `400` or `413` for a malformed body. Boot scans and the route share `runtime.private_service.play_decision`. `python scripts/draw_decisions.py` sends every pending request, checks each answer against its request (`scripts/collect_results.result_errors`) and writes the result file the collector would write. The token is read from `ENGINE_API_TOKEN` and never written or printed. Games are not drawn this way.
