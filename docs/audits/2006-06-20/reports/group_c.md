GROUP C (league): REPORT. Worktree /home/user/wt-c, branch audit-fix-c. 21 of the 22 findings are fixed; awards-standings/F2 is partly fixed (reason below). Reconcile ends with "Repository validation passed."

FINDINGS
- league-stats/LS-1: fixed. Implemented the integrator's decision: the Club / rights cell is now a dated club. A player who played in the period shows the clubs he played for, in stint order, joined with "/". A player who did not play shows his club on the page's label date: `club_on` unchanged for 2003-04, `club_truth.holder` from 2004-05. Examples: Anthony Johnson MIA, Kidd NJ/MIL, Jumaine Jones MIA/BOS, Stockton and Jordan FA.
- cards-contracts/F3: fixed. Dated club as above; the header count and the age caption are computed from the page.
- league-stats/LS-3: fixed. Jerome Beasley shows "MIA rights" through October 2003 and FA after his rights were renounced on 2003-11-11. From 2004-05 a "rights" label comes only from a Miami holding recorded as draft rights, since no other club's unsigned picks are modelled.
- league-stats/LS-2, ages-identity/ID-08, cards-contracts/F14: fixed. The three registry rows are named Wayne Simien, Matt Walsh and Gerald Fitch, each with a dated `name_corrected` note. Their closed lines are identical before and after (82, 21 and 2 records, checked by hash).
  - Cards, all league pages, the 2006 Playoff_Stats page and their contract pages now show the names.
  - `registry_additions` resolves an id-keyed player to his careers-file name.
  - `offseason.later_book` does the same, gated (see below).
  - Not changed, on purpose: the 2005 market record `free_agency_2005.json`, the played game requests and results, and the 7 Miami game notes. Those are past-decision and played-game records.
- league-stats/LS-5, ages-identity/ID-05, awards-standings/F6: fixed. "653 tracked players" and the six group counts come from the rows. Rows are now sorted alphabetically, so the README's "alphabetically" is true.
- league-stats/LS-6, ages-identity/AGE-04, awards-standings/F7: fixed. The caption states the label date actually used, for example 2006-06-20, or 2003-11-07 for a week page.
- ages-identity/ID-06: fixed. A player whose registry `added_on` is after the label date and who has no record by then shows "—" as club and league. Example: Chris Paul and Dwight Howard on the 2003-04 pages.
- ages-identity/AGE-01, cards-contracts/F16: fixed. Card month and week rows use the age at min(scope_for(linked page).end, card date).
- cards-contracts/F2: fixed. Card period Team cells come from the period's appearances. The regular rows' team cells in 2003-04 and 2004-05 `card_lines.json` were rewritten from closed results (72 and 101 rows; G counts checked against the results).
- awards-standings/F2: partly. The 2003-04 card rows and card_lines now name the clubs he actually played for (Marshall CHI/TOR, Hill PHI, Glover ATL). The FIRST_SEASON branch of `league_cards.club_on` is unchanged, as instructed. Its other 2003-04-dated consumers (`followed_players`, `player_contracts`) still get the in-season-blind answer.
- cards-contracts/F11: fixed. Jersey, baseline, photo and 2002-03 line are looked up by bbr_id. "Unassigned" dropped from 136 cards to 93, and none of the 60 id-mismatched rows that has a club remains unassigned. Telfair shows #31, Livingston #14. One side effect: Sean Marks's card now shows his sourced 2002-03 line.
- cards-contracts/F15: fixed. New `club_code` takes later clubs' codes from the season roster files (CHA, NOK); no card shows "None" and no full club name sits in a code cell. The 8 null `team_code` values in the registry were filled.
- league-stats/LS-7, awards-standings/F3: fixed. Playoffs.md states its season's seeding rule from the rules file (2003-04 two division winners, later seasons three). The tie-draw packet text now names its season; it is unchanged for 2003-04.
- awards-standings/F9: fixed. The League README navigation and counts are generated (`season_pages.hub`) and list every season's players, awards, standings and playoffs pages. The stale "never added" and 349+58 cohort lines are corrected. AGENTS.md, docs/player_cards.md and docs/HOW_IT_WORKS.md no longer say 407; docs/ROADMAP.md A1 is updated.

FORWARD-ONLY GATES
- `offseason.BOOK_NAMES_FROM = "2006-07"`. The 2005-06 opening book still recomputes identical to the stored one (checked).
- The `later_book` docstring is the book's stored `rule` field, so it is left unchanged.
- Registry rows carry `name_corrected: {"on": "2006-06-21", ...}`. Recorded decisions are never recomputed, `registry_additions` finds no new player, and validation passes.
- No game request, result, decision packet or draw was touched. No reader on a decision path changed its answer:
  - `club_on` and `club_truth` behaviour are unchanged.
  - `_code` only affects the `code` field, which only the cards read.
  - `player_lines` is unchanged, so the Finals MVP input is unchanged. The registry-name mapping is applied only when the playoff statistics page and the cards display the lines.

COMMITS
- Source: 8320d1ee482 (code, tests, docs), cbf5f8110a5 (registry, card_lines, README), bc89fa96871 (tests/checkpoint.py restates the hub in checkpoint copies)
- Regenerate: f5a307ae320 (710 files)

TESTS (python3.12, one module at a time). All OK: test_audit_c (16 tests), test_league_cards, test_league_layout, test_contract_navigation, test_league_ages, test_playoffs, test_offseason_years, test_league_card_honors, test_league_shot_feeds (after a fix), test_award_pages, test_dated_registry, test_club_truth, test_career_continuity, test_no_shadowed_calls, test_rollover, test_award_records, test_season_games (after the checkpoint fix), test_write_back, test_reporting, test_view_independence, test_milestone_records, test_free_agency, test_repository. The new tests fail at the base commit: the functions they test are absent there and the registry still held the id names.

LAST LINES OF RECONCILE: "results into notes, statistics pages, Miami and league cards: current / career views: current / Repository validation passed." A later `reconcile.py --check` exited 0. `update_player_reports.py --check` printed "Detailed career views are current." and `build_league_cards.py --check` printed "League cards match the dated records."

RISKS FOR THE INTEGRATOR
- Likely conflicts:
  - runtime/write_back.py: I split `league_pages` out of `statistics_pages`, whose Team part I left untouched, and added `league_records` to `run()` and `write_back_errors`.
  - runtime/league_cards.py: `card_data` and `markdown_card`.
  - tests/checkpoint.py.
  - docs/player_statistics.md step 4.
  - AGENTS.md league-stats lines.
  - Regenerated League pages and cards will conflict with any group that regenerates them: re-run reconcile after merging.
- Cost and a new validation scope:
  - A dated club on 2004-05+ pages calls `club_truth.holder` for each label date. The new `league_cards.roster_cache()` memoizes `league_moves.season_roles` and `clubs_at_activation` during a build; I checked the answers are identical.
  - Write-back and validation now also rebuild and compare closed seasons' League_Stats pages and every bracket page; the hub is checked only with `--check`/cards. Total reconcile was about 9 minutes, and the card build went from about 70 s to about 90 s.
- Consumers I was unsure about:
  - `season_close.feedback` matches results to the registry by name, and `award_decisions.registry_names` and `season_awards.identities` map names the same way. A 2005-06 result keyed 'simiewa01' no longer name-matches the renamed row in those readers. Their 2005-06 outputs are recorded and never recomputed. Future seasons' books carry names, so this should not recur.
  - The 2005 market writer (`free_agency_2004`) still writes ids where it lacks a name. That is upstream and was not changed.