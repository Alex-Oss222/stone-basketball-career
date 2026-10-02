# Library

League-wide historical source data lives here.

Career folders contain the branch's live player/team state. The library contains broader source material used to build and update that state without copying the entire league into every season.

Season schedules live at `library/<start year>/league/nba_<YYYY>_<YY>_schedule.json` (dates and matchups only, no results). Raw exports go in `incoming/` and are converted with `python scripts/import_schedules.py`.

## Season schedules on file

Regular season and preseason for 2003-04 through 2013-14. Sources: regular seasons from ESPN via SportsDataverse; preseasons from NBA.com via the Kaggle "NBA games data" set. All are the schedule as played, with no results.

| Season | Regular season | Preseason | Notes |
|---|---:|---:|---|
| 2003-04 | 1,189 | 114 | 29 clubs |
| 2004-05 | 1,230 | 48 | Charlotte Bobcats join (30 clubs). Preseason source covers only Oct 22-29, 2004; earlier games are missing |
| 2005-06 | 1,230 | 113 | New Orleans/Oklahoma City Hornets (Hurricane Katrina relocation) |
| 2006-07 | 1,230 | 110 | New Orleans/Oklahoma City Hornets |
| 2007-08 | 1,230 | 95 | |
| 2008-09 | 1,230 | 110 | Seattle SuperSonics become the Oklahoma City Thunder |
| 2009-10 | 1,230 | 112 | |
| 2010-11 | 1,230 | 111 | |
| 2011-12 | 990 | 30 | Lockout: 66 games per club from Dec 25, 2011; preseason in December |
| 2012-13 | 1,229 | 106 | Brooklyn Nets. Indiana at Boston (Apr 16, 2013) cancelled and not made up |
| 2013-14 | 1,230 | 108 | New Orleans Pelicans |

Hindsight caution: a schedule as played reflects in-season events. The 2012-13 file already lacks the cancelled Indiana at Boston game, and postponed games sit on their played dates. Before the career reaches a season, decide whether the published schedule should be restored for such cases. Season-specific counts are encoded in `runtime/schedule.py` (`SEASON_EXCEPTIONS`).
