# 2003 NBA league datasets

These files are source evidence, not live career state.

| File | Snapshot | Primary use |
|---|---|---|
| `nba_2003_end_of_season.json` | Each club at the end of its 2002-03 season | League roster baseline, depth slots, player IDs, birth dates and image metadata |
| `nba_2003_draft_class.json` | June 26, 2003 after draft-night trades | Draft-rights destinations, rookie identity data and image metadata |
| `nba_2002_03_player_stats.json` | All 428 players who appeared in the 2002-03 regular season | Original totals, advanced rates and source provenance |
| `nba_2003_veteran_ratings.json` | June 26, 2003; based only on 2002-03 | Generated statistical estimates, display grades and sample sizes |
| `nba_2003_veteran_import_report.json` | June 26, 2003 import coverage | Validation and roster matches |
| `nba_2002_03_league_environment.json` | Supplied 2002-03 league averages | Engine calibration baseline for 2003-04 |
| `nba_2003_04_schedule.json` | 2003-04 regular season, 1,189 games | Dates and matchups only; source: ESPN via SportsDataverse, as played |
| `nba_2003_04_preseason_schedule.json` | 2003-04 preseason, 114 NBA-vs-NBA games | Dates and matchups only; source: NBA.com via Kaggle, as played |
| `nba_awards_catalog.json` | Every NBA award across eras: first season, electorate, scoring rule, dated rule changes, each fact marked sourced/derived/unverified | Era gating of award votes (`runtime/award_records.awards_in_force`, `docs/awards_catalog.md`); kept here like the cap history, never a source of winners |

The schedules are pre-season knowledge and may be used before the games are played. They were taken from the schedule as played, so any game postponed during the season appears on its played date. No scores or results are stored.

## Chronology

The end-of-season dataset is the earlier baseline. Apply dated transactions after each club's final game rather than treating that snapshot as a permanent roster.

The draft-class dataset establishes where the 2003 draftees' rights sit after draft-night trades. It does not establish that those players have signed contracts or received depth-chart roles.

## Images

The datasets include Wikimedia image URLs and license metadata when available. Player cards may reference those fields. Do not invent a photo where the source field is null.

## Contracts and the cap (league-wide)

| File | Snapshot | Primary use |
|---|---|---|
| `nba_2003_contracts.json` | Every club's contracts, options, draft holds and dead money on June 26, 2003, scheduled through 2010-11 | League-wide cap ledgers (`runtime/contracts.py`) |
| `nba_2003_expiring_contracts.json` | 128 contracts expiring June 30, 2003 | The free-agent pool; `rfa_eligible` is eligibility only |
| `nba_2003_contracts_import_report.json` | What the import removed or recast, and residual risks | Audit |
| `../../<year>/league/nba_<YYYY>_<YY>_cap_rules.json` | Cap, tax line, exceptions, salary minimums and maximums for 2003-04 through 2013-14; rookie scale for 2003 | Rules each front office applies |

The raw uploads were imported once with `scripts/import_contracts.py`, which removed everything dated after the checkpoint: eight post-June 30 signing notes, the June 27 trade, and a release dated October 2003. It also recast "restricted" free-agent marks as eligibility, because a qualifying offer is a June 30 club decision the simulation makes. Miami's sheet in `00_Team/Finances` stays authoritative for Miami. Cap figures are usable by a front office only from their recorded publication date (`league_cap_history.json`); 2003-04 becomes live on July 15, 2003, and later seasons stay reference-only until their dates are researched.

## 1999 agreement rules and free-agent rights

| File | Content |
|---|---|
| `cba_1999_salary_cap_faq_extract.txt` | Rules extracted from Larry Coon's 1999 Salary Cap FAQ, with question numbers |
| `nba_1999_cba_rules.json` | The same rules as data (`runtime/cba.py`): cap holds, maximum salary, average-salary line, qualifying offers, Bird exceptions, minimum exception, rookie scale, renouncing |
| `nba_1999_cba_minimum_salary_scale.json` | Minimum salary by years of service, 1998-99 to 2004-05 |
| `nba_2003_free_agent_rights.json` | Bird class, cap hold and qualifying-offer amount for all 129 expiring players, every club. Restricted marks are recast as eligibility. |
| `miami_expiring_tenure.csv` | Tenure facts behind Miami's rights file (`00_Team/Finances/free_agent_rights.json`), which must agree with the league file |

