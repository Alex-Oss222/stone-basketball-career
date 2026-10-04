# Player statistics and professional identity

[Live Shooting, Contract and Awards](https://stone-basketball-career-production.up.railway.app/cards) · [Player contracts](https://stone-basketball-career-production.up.railway.app/contracts) · [Current career](../career/Dwyane_Wade/README.md) · [Filled preview](examples/player_stats_preview.md) · [Structure](season_structure.md)

Reports contain professional identity and statistical performance. Decisions remain in their owning notes. Existing team, league and award records retain their paths and links.

## Active detailed cards

The ordinary `scripts/update_player_reports.py` build generates `Stats_and_Awards/player_cards.html`, `player_cards_data.json`, `Shooting.md`, `Contract.md` and `Awards.md` from actual career evidence. The same build creates the detailed milestone desk and every tracked player's contract page under `Contracts/players/`. Every canonical player report links Shooting, Contract and Awards in that order; the shooting view uses the corresponding period where available. Contract has Current Contract and Contract History views, both tied to the dated agreement records described in [the contract guide](player_contract_pages.md). Complete details and source tables are open by default.

The live cards use `identity_at`, closed records from `collect_games`, and sourced earned awards. There is no fictional location generator on this path. Weekly and monthly awards stay in the complete award register; yearly banners use the recorded annual scope or recognized season-award/selection names. Unknown classifications remain in the complete register instead of becoming an invented annual trophy.

### Recorded shot-location source

A closed game note may declare `shot_file: Game_N.shots.json` in its metadata. This must be an existing adjacent JSON file within the same player career. Its envelope requires:

| Field | Required value or meaning |
| --- | --- |
| `schema_version` | `1` |
| `record_type` | `recorded_player_shots` |
| `player_id`, `event_id`, `date`, `season`, `competition` | Exact match to the canonical player and closed game |
| `recorded_on` | A date on or after the game and no later than the career cutoff |
| `coordinate_system` | `nba_feet_from_basket` |
| `source_type` | `recorded_event_feed` or `recorded_manual_tracking` |
| `source_label` | Nonempty description of the recorded evidence |
| `shots` | Attempts with unique `shot_id`, coordinates `x`/`y`, boolean `made`, and recorded `value` of 2 or 3 |

Coordinates use the [documented court convention](shooting_and_awards_design.md). The adapter validates identity, dates, shot values, location geometry and made/missed buckets against the closed box. Synthetic/example records fail validation. Missing coordinates and partial feeds preserve observed coverage while withholding complete-period regional rates. An unclosed engine sidecar, a scheduled note, a player's position or a source-library shooting estimate cannot supply live locations.

### Simulated engine shot events

Kernel 2003.7 records each FGA's modeled location before its outcome, using [prior-season spatial inputs](shot_environment_sources.md). A closed, declared game result can directly supply `shot_tracking` and `shots`; no duplicated `.shots.json` is created. The metadata requires schema 1, model `spatial-2003.1`, coordinate system `nba_feet_from_basket`, `source_type: engine_generated`, complete coverage and the journaled prior's SHA-256. Events retain stable shot IDs, player/side identity, period/clock, coordinates, native zone, two-/three-point value, make/miss and transition status.

The adapter verifies the closed note, declared result path, dates and player identity; validates all player/team shooting buckets and event geometry; and binds displayed events to a digest of the complete original result. Engine feeds are labeled **Simulated engine shot locations**. An engine feed and an external shot file cannot both supply the same game. No locations are appended to legacy results.

**All games** keeps the selected period's full boxes and coverage gaps. **Tracked games only** uses a separate aggregate of complete tracked games, with its own dates, appearances, source links, attempts, percentages and per-game denominators. A played zero-attempt game stays in that cohort's appearance count when its feed is explicitly present; DNPs do not count as appearances. With mixed old and tracked games the chart defaults to the tracked cohort, while the full period remains selectable. Periods with no tracking show an empty court and explanation. Other court geometries require a verified adapter before spatial plotting.

League season/month/week pages also use the complete per-game column order, with recorded age, club/rights, league and position. Their shared red-and-black section header needs no player awards banner. `scripts/format_league_reports.py` preserves existing period values when migrating the layout; the write-back (below) aggregates the closed results into those pages. Missing attempts and other new columns remain N/A until supported by branch games.

## Each level has a purpose

| Level | README | Statistical detail |
| --- | --- | --- |
| Career | Dated identity; regular season and playoffs by season, separate career totals | Follow a season or national competition |
| NBA season | Separate competition rows; regular season by month | Each competition owns its detail |
| Summer League / preseason | Production, shooting, participation and games | Totals, per-game, per-36, efficiency, splits and highs |
| Regular season | Season production and monthly rollup | Full season detail with source links |
| Month | Monthly production, each week, previous month and season through month end | Full month detail |
| Week | Weekly production, previous week, month-to-date, season-to-date, game log | Weekly totals and individual-game shooting |
| Playoffs | Separate postseason and series rows | Series/round and game detail |
| National competition | Qualifiers and final tournament, then edition/cycle | Stage/window/round and game detail |
| Game | Dated identity, participation or DNP, result | Actual box totals and source-supported rates |

The established player report path is `Stats_and_Awards/<season>/<month>/Week_N/README.md`. Matching READMEs beside regular-season notes expose the same summary. Deeper tables live in `Stat_Detail.md`. One canonical game feeds all applicable views.

The career folder README opens with a visual overview in the supplied red/dark card style. `assets/career_overview.svg` is generated from the same dated identity and career totals, with separate regular-season and playoff cards. The professional-status card contains entry and roster fields. A collapsible text version retains accessible tables and source navigation. Rebuilding player reports refreshes both versions; the reference screenshot's historical biography and career results are not imported.

All player report levels now share the red-and-black personal-information header, with position, shooting hand, height, weight, birth date, age, prior program, jersey, roster status and draft entry. Gold badges show confirmed professional honors. The source remains the simulation's identity and results, including on national-team, playoff, month, week and game reports. Existing team/league population tables keep their own records.

Per-game tables follow the supplied reference's column sequence: **Scope, Age, Team, Lg, Pos, G, GS, MP, FG, FGA, FG%, 3P, 3PA, 3P%, 2P, 2PA, 2P%, eFG%, FT, FTA, FT%, ORB, DRB, TRB, AST, STL, BLK, TOV, PF, PTS**, then estimated TS% and earned awards. FG/3P/2P/FT are makes per appearance. Percentages in these tables use the reference's decimal style (.500 means 50.0%); other explicitly percent-formatted detail tables remain readable percentages. G/GS remain counts. The table scrolls horizontally on narrow screens so columns and source links stay selectable. Career rows are seasons, season rows are months or distinct competitions, month rows are weeks, and week logs include individual game boxes. No competition totals are combined.

The SVG header is shared by pages with the same identity cutoff to avoid duplicate assets. Text equivalents retain all personal fields, honors and source links. Career-level regular-season and playoff tables remain visible beneath the overview and award banner.

## Earned-honor banners

`career/Dwyane_Wade/awards.json` supplies earned badges and the Awards column. `Awards.md` is its readable register. The initial register is empty. A nomination, voting placement, unclosed ballot or historical Wade award does not create a badge. Repeated honors are grouped into count badges; full award names and dates remain available in text.

Each entry needs `id`, `name`, `short_name`, `status: earned`, `competition`, `season` (or national edition), `period_start`, `period_end`, `awarded_on` and a `source` path relative to the player folder. The `name` of a league honor is canonical, because Wade's standing (`runtime/standing.py`) reads it: `All-Star` (filed in the `regular` competition), `All-NBA First Team`, `All-NBA Second Team`, `All-NBA Third Team`, `Most Valuable Player` and `Finals MVP` (`playoff`); other honors may use any name and do not move his standing. The source must be an existing closed award-decision record in the career; a fragment may identify its section. Use the report competition names in this document, or `career` for a lifetime honor. Confirm the decision and keep the existing season/month/week honor registers and league award record synchronized before adding its structured entry. The renderer displays honors; it does not decide award winners or replace the voting workflow.

The loader rejects duplicate honors, nominees, unsupported competitions, future announcements, invalid date order and missing/outside sources. NBA Cup and Play-In season gates also apply to their honors. A banner shows only awards announced by that page's identity cutoff. The table's Awards column uses the current career knowledge date and files each honor into the period containing its **period-end date**, as required by the calendar/award rules. Thus an award announced on Monday can appear in the prior week's table after confirmation; its announcement date is retained in the register, and the table names its knowledge cutoff. It never enters an earlier as-of banner before announcement.

The filled examples include fictional award badges to demonstrate appearance. They are kept outside the career directory and marked as illustrative.

The sample cards now use two linked destinations, **Shooting** and **Awards**, in place of the descriptive category strip. The [interactive shooting card](examples/player_cards_preview.html) adds location inspection, fixed FG% colors, frequency-scaled dots and period-specific regional calculations. Its locations are explicitly synthetic and reconcile to the existing fictional box scores. The Awards view shows yearly earned banners, with separate empty and fictional filled design cases. [Design, formulas and source requirements](shooting_and_awards_design.md) explain the missing-feed behavior and the distinction between sample visualization and live tracking support.

Weeks retain the repository's established **days 1-7, 8-14, 15-21 and 22-month end**, with full dates in every title. They are monthly buckets, not Monday-Sunday weeks. Official awards retain their own date windows. January-April belong to the second calendar year of an NBA season. The 2003-04 calendar is not universal: verify lockout, restart and future schedules at rollover.

## Professional identity

`professional_identity.json` is the structured companion to the established player profile. Append a dated snapshot when team, jersey, role, contract or national status changes. Do not replace earlier snapshots with today's state. Each report uses the latest snapshot on or before its cutoff. Measurements have their own recorded date.

The compact identity includes name, age at cutoff, team/league, position, jersey and roster status. `Professional_Identity.md` adds birth date, physical measurements, shooting hand, entry, prior program, contract, role, debut and national eligibility/selection. Unknown eligibility and an unassigned jersey remain explicit. The supplied alternate-history identity, including the 1984 birth date and UConn background, takes precedence over historical Wade's biography. Update measurements only with dated evidence.

## Calculation contract

These repository reporting definitions are implemented in `runtime/career_stats.py`.

| Field | Method |
| --- | --- |
| G / GS | Count appearances / recorded starts |
| Minutes | Sum exact seconds, then divide by 60; round only for display |
| Counting totals | Sum points, rebounds, assists, steals, blocks, turnovers, fouls and shot makes/attempts |
| REB / 2P | OREB + DREB / all field goals minus threes |
| Per game | Total / appearances in that scope; DNPs excluded |
| Per 36 | 36 × total / actual minutes; not a forecast or assumed game length |
| FG%, 2P%, 3P%, FT% | Pooled makes / pooled attempts |
| eFG% | (FGM + 0.5 × 3PM) / FGA |
| TS% (estimated) | PTS / [2 × (FGA + 0.44 × FTA)] |
| Three-point attempt share | 3PA / FGA |
| Free-throw attempt rate | FTA / FGA, displayed as a ratio |
| AST/TOV | AST / TOV; N/A at zero turnovers |
| Double-/triple-double | At least 10 in two/three of PTS, REB, AST, STL, BLK; triple-doubles also count as double-doubles |
| Game highs | Maximum observed single-game value; all ties and source links |
| Splits | Home, away, neutral, wins, losses and recorded team; overlapping views are not additive |

Recompute rates from raw totals, never averages of percentages. Comparisons use each period's own sample and cutoff; month-to-date never includes later weeks. NBA regular season, NBA playoffs and national competitions never share an additive total.

An empty scope has G = 0, counting totals = 0 and rates = N/A. Missing player coverage in a closed game makes full-period G, totals and rates N/A; known games stay visible. An absent player row is not a DNP. An explicit inactive entry or a zero-time, zero-stat nonappearance is required. A true subsecond appearance may supply `appeared: true` even if reported seconds are zero. Scheduled/canceled games are not appearances.

The engine supplies traditional boxes, exact seconds and a `started` boolean for each player in newly played games, fixed from the actual opening five after availability and injury replacements. Every recorded start counts equally, including Wade starting while another player is injured. GS updates when the game becomes a closed career record. Wade's standing still uses closed-season totals under `runtime/standing.py`; a midseason injury start does not bypass that timing. Later rotations never change a played game's starts, and historical boxes without `started` keep GS unavailable instead of inferring it from minutes or today's depth chart.

Plus/minus remains N/A unless an observed optional `plus_minus` field is supplied. New engine results supply spatial FGA events; older results retain missing locations. Player on-court possessions, detailed play types, drives and hustle tracking remain unavailable. Detail pages identify the evidence needed for usage, assist/rebound opportunity percentages, possession ratings, on/off, clutch and lineups. Full-game team possessions are not the player's on-court possessions. League ranks require a same-period simulated comparison population and eligibility rules.

## Competition ownership

| Competition | Canonical home | Treatment |
| --- | --- | --- |
| Summer League | `<season>/02_Summer_League/` | Separate exhibition-development record; retain event-specific game length and rules |
| Preseason | `<season>/05_Preseason/` | Separate preseason record |
| Regular season | `<season>/06_Regular_Season/<month>/Week_N/` | Includes applicable Cup group, quarterfinal and semifinal games once |
| Play-In | `<season>/07_Play_In_Tournament/` | Separate; unavailable before 2019-20; restart format differs from 2020-21 onward |
| Playoffs | `<season>/08_Playoffs/<round>/` | Separate postseason/series totals |
| NBA Cup championship | `<season>/10_NBA_Cup/Championship/` | Separate championship-only record; first season 2023-24 |
| National team | `National_Team/<family>/<edition>/<stage>/` | Separate competition, edition and stage; never NBA totals |

NBA Cup starts in **2023-24**. Earlier seasons receive no Cup folder, markers or games. Non-championship Cup games use `competition: regular` with `cup_stage: group`, `quarterfinal` or `semifinal`. The Cup page references their original notes. Its championship uses `competition: nba_cup_championship` and `cup_stage: championship`. Do not duplicate games. Qualification, dates and future format changes require the rules for that edition. Reporting gates do not enable an unverified engine era or authorize advancing time.

## Result-to-report workflow

1. Create only an actually scheduled game or explicit cancellation using `scripts/create_game_note.py`. Run `--help` for supported NBA phases. National events use the path contract below.
2. Follow the existing Railway workflow. Save the full JSON from `/games/<event_id>` beside the owning note as `Game_N.result.json`; `/games/<event_id>/box` is the readable box score. Do not hand-edit performance or rerun a closed game.
3. Set note metadata: `status: played`, `date`, `opponent`, `venue`, `competition`, `result` (player-team W/L and score), `event_id`, `simulation_source`, and `result_file: Game_N.result.json`. A stray response is not a career result.
4. Update the checkpoint and affected identity snapshot under the normal event workflow.
5. Run `python scripts/update_player_reports.py`, `python scripts/validate_repository.py` and `python -m unittest discover -s tests -q`. Use `python scripts/update_player_reports.py --check` for read-only freshness checking.

The JSON retains the engine's `event_id`, `game_date`, `season`, `game_type`, `terminated`, `home`, `away`, `venue`, `game_seconds`, `final_score`, `player_stats` and `inactive`. Player rows identify the player and supply exact `seconds` plus `pts`, `fgm`, `fga`, `tpm`, `tpa`, `ftm`, `fta`, `orb`, `drb`, `ast`, `stl`, `blk`, `tov`, `pf`. Preserve the entire original response, including team/period fields. Weighted-free-throw feeds must declare `free_throw_mode: weighted` and observed `ft_points`; conventional 0.44 TS% is unavailable in affected aggregates.

The reader checks event uniqueness, aliases, season/date/folder agreement, completed status, scoring arithmetic, shooting bounds and playing time. Existing game metadata and decisions are retained; only the marked report block is generated. Existing award text is preserved. Rendering never calls the engine, imports historical Wade's output, advances time, chooses player identity or writes team/league results. Steps 3 and 5 are automated by the write-back below.

## Write-back

`python scripts/write_back_results.py --write` turns the engine's collected answers into the career record (`runtime/write_back.py`, roadmap item 13). `--check` verifies without writing and repository validation runs the same checks. In order:

1. **Game notes.** Every Miami note under `05_Preseason` and `06_Regular_Season/<month>/Week_N` whose `result_file` exists beside it, whose status is still `scheduled` and whose date is on or before the career clock becomes `played`: `result` gets the label from Miami's side (`W 95-90`), the body gets a `<!-- game-result -->` block with the score, opponent, venue, the plain-text box score (`runtime/boxscore.py`), the result file reference and the Miami injuries the result reports with games out. `simulation_source`, `event_id` and `result_file` stay; the request and result files are never edited. A preseason result is marked as evidence for the preseason record and the camp decisions only; it never enters regular-season statistics.
2. **Phase note and injuries.** The game is appended to the owning phase note (`05_Preseason/note.md`, Events) or week note (`Games and events`) with its score, result, link and injuries. Each Miami injury is appended to the player's Miami card under "Changes and coaching notes" with the date, the event and the games out; a player without a card is reported, and the phase-note line stands as his record. The game builder reads the injury from the result (`injured_out`), not from the card.
3. **Wade's reports.** The reporter above rebuilds the game, week, month, season and competition pages from the played notes, with the per-game columns and the pooled percentages of this document.
4. **Miami and league pages.** `Stats_and_Awards/Team/<season>/...` and `Stats_and_Awards/League/<season>/...` are aggregated from the closed regular-season results: Miami's from its played notes, the other clubs' from `Stats_and_Awards/League/<season>/Games/<game_id>.result.json`. Week and month pages summarize the closed games in their calendar buckets, the season page the whole season; every percentage is recomputed from summed makes and attempts; a player without an appearance keeps G = 0 and N/A, never zero; GS counts recorded starts when every appearance has an observed `started` value and otherwise stays N/A. Players are matched to the registry by bbr_id (from the request or the real roster file), then by name; a player in a result who is not in the registry is reported by the script and never added. The Miami pages keep every row that is there (departures stay) and add any Miami player who appeared. The dated "not started" lines are kept until a period has a closed game.
5. **League cards.** `scripts/build_league_cards.py --write` runs last; the cards read the same closed results and validated engine shot events. Older games remain untracked; a separate tracked-games cohort supplies complete regional rates without changing full-period totals.

The write-back never runs the engine, never advances time, never edits a request or a result, and never invents data (no starts, locations, tracking or results it was not given). A result dated after the clock waits and is listed as waiting. Re-running changes nothing. Validation: an existing result beside a scheduled note dated on or before the clock is an error ("unwritten result"); a played note must have its result file, its label must match the score, its result block must be present, its game must be logged in the phase note and each injury on the player's card; the Miami and league pages must match a fresh aggregation. Playoff and Play-In notes, standings and award aggregation are later roadmap items.

## National team / FIBA

FIBA is the governing body, not an additional competition on top of the World Cup. The initialized hub has no invented selection or edition. Add an edition when a simulation event requires it. Five-on-five only; 3x3 requires another model.

| Family | Stage folder | `competition` |
| --- | --- | --- |
| `World_Cup` | `Qualifiers` / `Final_Tournament` | `world_cup_qualifier` / `world_cup_finals` |
| `Olympics` | `Qualifiers` / `Final_Tournament` | `olympic_qualifier` / `olympic_finals` |
| `Continental_Cups` | `Qualifiers` / `Final_Tournament` | `continental_qualifier` / `continental_finals` |
| `Friendlies` | `Games` | `national_friendly` |

Example path shape: `National_Team/World_Cup/<edition>/Final_Tournament/<round>/Game_1.md`. Qualifying cycles use their target edition even when dates span years. Populated window/round folders receive local READMEs. Each national note additionally needs `edition` matching its folder and `player_team` naming the country. The JSON must have the same `edition` and national `game_type`. Record selection, eligibility, actual date, opponent, venue, regulation length, overtime and applicable rules in the event evidence. An NBA contract does not establish national eligibility.

## Research references

These sources inform structure and terminology, never simulated outcomes. Apply the rules valid on the event date; modern manuals do not retroactively govern earlier games.

- [NBA statistics glossary](https://www.nba.com/stats/help/glossary): reference terminology for traditional, shooting, possession and tracking statistics.
- [NBA inaugural tournament announcement](https://pr.nba.com/nba-in-season-tournament-2023-24-season/): 2023-24 debut; championship excluded from regular-season counting.
- [NBA 2020-21 season structure](https://official.nba.com/nba-announces-structure-and-format-for-2020-21-season/) and [Play-In history](https://www.nba.com/news/play-in-tournament-history): modern format and restart exception.
- [FIBA Statisticians' Manual 2024](https://assets.fiba.basketball/image/upload/documents-corporate-fiba-statisticians-manual-2024.pdf): primary event-recording reference for applicable editions; use the historical manual for earlier events.
