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

The schedules are pre-season knowledge and may be used before the games are played. They were taken from the schedule as played, so any game postponed during the season appears on its played date. No scores or results are stored.

## Chronology

The end-of-season dataset is the earlier baseline. Apply dated transactions after each club's final game rather than treating that snapshot as a permanent roster.

The draft-class dataset establishes where the 2003 draftees' rights sit after draft-night trades. It does not establish that those players have signed contracts or received depth-chart roles.

## Images

The datasets include Wikimedia image URLs and license metadata when available. Player cards may reference those fields. Do not invent a photo where the source field is null.
