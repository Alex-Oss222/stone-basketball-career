GROUP B (miami): REPORT

All 14 findings are fixed. Telfair's position correction only takes effect on 2006-06-21, because played games froze SF. Validation passes, my 19 new tests pass, and all 66 existing test modules that touch the files I changed pass.

FINDINGS
- miami-stats/MIA-1: fixed. Every card on file gets one playoff row per season and club, built the same way as the playoff pages (`playoff_stats.player_lines` and `aggregate`). For example, Wade now shows 2, 12 and 17 G; Eddie Jones 2003-04 shows 5 G; Okur shows 12 and 17 G.
- cards-contracts/F1: fixed. The yearly statistics block is now generated whole:
  - 2002-03 rows are kept, or added from the library file when missing.
  - Each simulated season gets its Miami row. Earlier seasons he did not spend entirely with Miami also get an every-club row from `season_totals.json`, which fills the gaps on the Mihm, Joe Smith, P.J. Brown, Marshall and Harpring cards.
  - Honors come from `awards.json` for Wade (36) and from the award records at rank 1 for everyone else (Mike James 2).
  - Coverage lines and dates are regenerated.
- miami-stats/MIA-3: fixed. Live and closed-season Team pages list only players Miami held under contract in the period (`write_back.contract_holdings`). Malik Allen, Beasley, Robinson, Drejer and Slokar rows are gone. Not-started pages name rights holders in their status line instead.
- miami-stats/MIA-4: fixed. The desk now reads "15 under contract (12 active, 3 on the injured list)". Slokar is shown as "Unsigned draft rights; not on the roster" with no role. His card role line and old rotation notes are rewritten to match.
- miami-stats/MIA-5: fixed. `team_status.expiring` labels the five contracts that end June 30, from the day after the regular season through June 30. Butler's label adds the rookie-scale qualifying-offer / restricted free agency note. The register's `status` field is untouched, because `gm.roster_values` reads it.
- miami-stats/MIA-6: fixed. The term clauses in each register's control text are regenerated from `contract_schedules.json` (`miami_cards.control_texts`, using the shared `rollover.contract_head`). Grant now reads 3 seasons, $43,008,660 and Butler 2 seasons, $4,392,297. Both cards are synced. The write-back keeps this current and validation flags drift.
- miami-stats/MIA-7: fixed. Coverage lines are generated for every wording, and the FG%/3P%/FT% columns use one format (45.2%).
- miami-stats/MIA-8: fixed.
  - Each season's Team page states Miami's playoff record and links `Playoffs/Team_Playoff_Stats.md` (`playoff_stats.team_season_section`, included in `pages()`).
  - `Stats_and_Awards/Team/README.md` is now generated with every season (`team_status.team_stats_readme`).
  - The missing `Player_Cards/README.md` index is generated for 2004-05 and 2005-06, which fixes the broken links.
  - The season-page template text is updated.
- miami-stats/MIA-9: fixed. An ended period with no games reads "complete; no Miami game" and lists only players Miami held then. Period tables show "No games" instead of "Not started". Closed seasons' Team pages are rebuilt as of their stated date (`write_back.closed_team_pages`). The dated June 26 control table is left as is, per the skeptic.
- miami-stats/MIA-10 and ages-identity/ID-03: fixed from 2006-06-21 only. The 2005-06 register row keeps `positions: ["SF"]` and now also carries `positions_corrected` (PG) from 2006-06-21. Every reader uses it by date. Pages and cards are built on the clock date, so they still show SF today and switch to PG on 2006-06-21. The 2006 rollover will carry PG.
- miami-stats/MIA-11 and ages-identity/AGE-02: fixed. Birth dates were back-filled on 7 rows in the 2004-05 register and Slokar's row in 2005-06, each with `date_of_birth_from` 2006-06-21. Frozen injury ages stay null, and cards and contract pages now show the ages. `signing.league_identity` and `Rollover.identities` now read the prospect evidence and `nba_player_births.json`.
- miami-stats/MIA-12: fixed. 2005-06 `team_config` records `payroll_ceiling` 61,700,000 with its basis, and keeps `payroll_ceiling_through_2004_05` at 57,000,000. `gm.payroll_ceiling` reads that new field for dates before 2005-06, so it returns the same value as before for every date. The rollover writes the season's tax line through `season_budget`.

FORWARD-ONLY GATES (all effective 2006-06-21)
- New module `runtime/miami_register.py`:
  - `positions_on`, `with_positions_on` and `carried` apply the dated position correction.
  - `required_position` keeps the old "SF" guess through 2006-06-20 and raises after it.
- Readers that apply the position correction by date:
  - `season_games.miami_side` (game date)
  - `rotation_reviews.review_input` (review date)
  - `gm.FrontOffice.__init__` (need score and camp)
  - `team_status.register`
  - `statistics_pages` (Team page position column)
  - card headers and the card index
  - `Rollover.register` (carries the correction into the next season)
- SF fallbacks now go through `required_position`: `rollover.py` (arrivals), `signing.py` (two register rows and the departures position), `camp.py`, `refill.py`, `gm.py`.
- Birth dates: `date_of_birth_from` on the back-filled rows. `trades.Assets` age fallback now honours it, and `TradeDesk.miami_player` passes it through.

COMMITS (branch audit-fix-b)
- Source: `ad59d80a484` "Audit fix b: Miami cards, register, team desk and Team pages"
- Regenerate: `0d37238e8e0` "Audit fix b: regenerate derived pages" (166 files: cards, Team pages, team READMEs, Player_Cards indexes, contract pages for drejech01 and slokaur01)

TESTS
- `tests/test_audit_b.py`: 19 tests, all fail before the fix and all pass after.
- 66 existing modules ran one at a time under python3.12; all pass.
  - First run: test_season_games failed because the checkpoint pin left post-checkpoint honor links on Wade's card. I fixed this in `tests/checkpoint.py` (pinned cards drop honor rows announced after June 26, 2003) and it now passes.
  - test_write_back failed once only because I cleared the shared temp directory while it was running. It passes on rerun.

RECONCILE (last lines)
```
results into notes, statistics pages, Miami and league cards: current
career views: current
Repository validation passed.
```
Both `update_player_reports.py --check` ("Detailed career views are current.") and `build_league_cards.py --check` ("League cards match the dated records.") pass.

RISKS FOR THE INTEGRATOR
- **Likely conflicts:**
  - `runtime/write_back.py`: `period_rows`, `register_names`/`team_page`, the new `contract_holdings`, `closed_team_pages`, `register_rights`, `statistics_pages` (positions, held and rights parameters), `run()` and `write_back_errors` (closed Team pages).
  - The `period_rows` change also turns ended periods with no games on live League pages into "No games". Closed seasons' League pages are not rebuilt, so the 2003-04 League October page still says "Not started".
  - `runtime/rollover.py`, `runtime/signing.py`, `tests/checkpoint.py`, and the two register files.
- **Code from other groups:** `miami_cards` builds `league_cards.CardContext(root).honors` and calls `career_stats.aggregate`, both of which other groups own. If they change those, Miami card honors and playoff rows follow.
- **Next hard stops:** from 2006-06-21, a Miami arrival, refill/camp/FA candidate or traded player with no known position now raises instead of getting "SF". This includes registry rows marked "unknown" position (`signing.league_identity` now uses `known_position`) and a 2006 rollover arrival without a sourced position. The 2006 summer or rollover could stop on such a gap and need a position added.
- **Not done:** the SF fallbacks in `league_moves.py`, `league_market.py`, `club_replacements.py` and `trades.py` are outside my brief and unchanged.
- **Cost:** `miami_cards.refresh` now covers every season on each write-back, light runs included, adding about 3 seconds.