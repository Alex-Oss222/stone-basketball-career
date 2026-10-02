# Library

League-wide historical source data lives here.

Career folders contain the branch's live player/team state. The library contains broader source material used to build and update that state without copying the entire league into every season.

Season schedules live at `library/<start year>/league/nba_<YYYY>_<YY>_schedule.json` (dates and matchups only, no results). Raw exports go in `incoming/` and are converted with `python scripts/import_schedules.py`.
