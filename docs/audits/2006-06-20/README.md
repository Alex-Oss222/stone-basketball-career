# Records audit at career date 2006-06-20 (save point)

The user asked, after the 2006 Finals: "make sure peoples stats are updated and ages correct ect check for errors". This folder saves that audit and its unfinished fixes. The run was stopped at the user's request ("create a proper save point and stop") before the fixes were reviewed and merged.

**State of the career:** unchanged. `milestone-1` holds the validated 2006-06-20 checkpoint (`e01d1427ac`, Toronto champion). No fix in this folder is applied, so the engine and every career record are exactly as they were. The clock must not advance past 2006-06-20 until the fixes are merged or deliberately set aside: several of them change what the 2006 summer reads (see "Fixes that act on later dates").

## What was checked and is correct

The four built-in checks passed: `scripts/reconcile.py --check`, `scripts/update_player_reports.py --check`, `scripts/build_league_cards.py --check` and `scripts/all_star_day.py --check`. Six independent auditors then recomputed the records from the closed results, and a seventh looked for gaps. Every finding was reproduced by a separate skeptic before it was accepted.

The statistics themselves are right:

- Wade: all 7,639 per-game table rows on 647 pages (game, week, month, season and career, regular season, playoffs, preseason, All-Star, Rookie Challenge, national team), pooled percentages, game highs, milestones with their ages, Shooting.md, the card data and `awards.json` (36 honors).
- League: every Age cell on all 92 League_Stats pages (60,076 cells) is correct at the page's cutoff; every player line matches the closed results.
- Every box-score player in 2004-05 and 2005-06 (56,949 player-game rows) played for the club `club_truth.holder` gives him on the game date.
- All 3,649 regular-season results match the real schedule; all 301 played Miami notes match their results; Chris Bosh's followed-player records match apart from the ages below.

## Errors found

`findings.json` holds every finding with its evidence and the skeptic's verdict; `groups.json` maps them to the five fix groups. About 45 distinct errors remain after duplicates, all in records derived from the results, not in the results:

| Group | Area | Main errors |
|---|---|---|
| A | Contract catalog and `/contracts` pages | Option decisions never shown (Wade's 2006-07 option exercised 2005-10-31 is missing; 58 of 58 decisions); in-season league moves ignored (91 players' current agreement at the wrong club, Jumaine Jones among them); expired Miami contracts shown as current; P.J. Brown split into two agreements; 80 players "under contract" with no contract in force; Jumaine Jones's waiver filed under his voided 2003 contract; two orphan pages |
| B | Miami cards, register, Team pages | No playoff rows or honors on any Miami card (42 cards); stale coverage lines; rights holders listed as Miami players on 128 Team-page rows; Slokar's unsigned rights counted as a contract (16 should be 15); expiring contracts unlabelled; Grant's and Butler's 2004-05 contract text; Team README frozen at 2003; Telfair SF instead of PG; eight missing birth dates; stale 2005-06 payroll ceiling text |
| C | League pages and league cards | Club column frozen at the 2002-03 label (Anthony Johnson "NJ" on a season he played 82 games for Miami); "407 tracked players" and old position counts on all 92 pages (653 listed); age caption names 2003-06-26; three players shown by raw id (Wayne Simien, Gerald Fitch, Matt Walsh); card month and week rows one year too old (7,504 rows); card period club wrong (672 rows); 43 cards "Unassigned" jersey; "None" club codes; Playoffs.md states the 2003-04 seeding rule |
| D | Wade's identity, notes, numbers | Identity role "staff plan 34 minutes" on 402 pages (the staff planned 36.6 to 40); availability ignores the injured list; interactive card opens on an empty 2006-07 season; Wade and Caron Butler both #3 in 2005-06; duplicate numbers at 24 other clubs; eight stale phase notes and the 2004 and 2005 drafts missing from their notes; `current_note` stuck on the training-camp note; Bosh's season ages one year low |
| E | Stored rules and forward records | Wade's points-per-game incentives met in 2004-05 and 2005-06 but recorded "unrecorded" ($236,180 + $252,660); 2006-07 trajectory feedback leaves out Mike Sweetney and Slava Medvedenko; prior-season totals drop sub-3-second games; FIBA 2005 page puts six scores against the wrong teams and ranks Uruguay above Venezuela; season-award and draft-order rule texts describe 2003-04 and 2004 |

Refuted and not fixed: preseason row ages (WADE-STATS-05, the documented row cutoff). The club column (LS-1, LS-3, F3) was judged a documented convention by its skeptics; group C changed it to a dated club anyway, by the integrator's decision, so the user should confirm that change.

## Fix status

Each group worked on its own branch from `e01d1427ac`. Only the source commits are saved here (`patches/<group>/`); the regenerated pages are rebuilt by `scripts/reconcile.py`, and no hand-edited record was in a regenerate commit.

| Group | State when stopped | Tests | Review |
|---|---|---|---|
| A contracts | complete; reconcile clean; report in `reports/group_a.md` | `tests/test_audit_a.py` (15) and 10 existing modules pass | not reviewed |
| B Miami | complete; reconcile clean; report in `reports/group_b.md` | `tests/test_audit_b.py` (19) and 66 existing modules pass | not reviewed |
| C league | 21 of 22 complete (F2 partly: `club_on`'s 2003-04 branch left unchanged for its other readers); reconcile clean; report in `reports/group_c.md` | `tests/test_audit_c.py` (16) and 22 existing modules pass | not reviewed |
| D Wade | code complete; its final tests, reconcile and commit were running | `tests/test_audit_d.py` written, final pass not confirmed | not reviewed |
| E records | six of seven items done; BIRTH-01 (birth-date conflict notes in the FIBA and prospect files) not started | no test file yet | not reviewed |

Patch conflicts (checked by applying the patches in a scratch worktree): A and E apply cleanly in any order. B and C both edit `runtime/write_back.py` (B: `period_rows`, `team_page`, `register_names`; C: splits `league_pages` out of `statistics_pages`) and `docs/player_statistics.md`. D conflicts with B or C only in `docs/player_statistics.md`.

## Fixes that act on later dates

Each is gated so every played game and recorded decision replays unchanged (validation recomputes frozen game inputs):

- Telfair: SF stays for every played game; PG from 2006-06-21 (`runtime/miami_register.py`, group B). From that date an arrival with no sourced position raises instead of becoming "SF", so the 2006 summer can stop on a missing position.
- Birth dates back-filled with `date_of_birth_from: 2006-06-21` (group B).
- Registry names corrected on 2006-06-21; later opening books resolve names from 2006-07 (`offseason.BOOK_NAMES_FROM`, group C).
- Season evidence counts every appearance only for seasons whose totals are not yet written (2005-06 on); the stored 2003-04 and 2004-05 totals stand (group E).
- Only `career/Dwyane_Wade/2006-07/trajectory_feedback.json` is regenerated (no 2006-07 game exists); the 2005-06 file stands (group E).
- Wade's incentive evaluations for 2004-05 and 2005-06 are dated correction records (`<season>/season_close_corrections.json`), since a season close never rewrites its file (group E). Whether the earned bonuses also flow into Miami's finance summary and cap sheet must be checked in review.

## How to resume

1. Branch from `milestone-1`. Apply the patches in order A, B, C, D, E with `git am -3 docs/audits/2006-06-20/patches/<group>/*.patch`, resolving the conflicts above by keeping both sides' changes.
2. Finish D (its final test pass) and E (BIRTH-01 and `tests/test_audit_e.py`).
3. Run `python3.12 scripts/reconcile.py` to regenerate every derived page, then the checks named above.
4. Review each group adversarially against `findings.json`, using the probes under `probes/` (written for the scratch paths of this session; the repository paths inside them are absolute): forward-only safety first, then that each finding's expected values now appear.
5. Run the full suite with python3.12 (`scripts/run_tests.py -j 6`), push to `milestone-1`, then remove this folder's patches or mark them applied.
