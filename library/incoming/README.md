# Incoming raw data

Drop raw league exports here (CSV, TSV, JSON or XLSX), for example season schedules from Basketball-Reference. Nothing in this folder is read by the engine.

`python scripts/import_schedules.py` converts every schedule here into `library/<start year>/league/nba_<YYYY>_<YY>_schedule.json`, one file per season, with dates and matchups only. Scores, overtime, attendance and any other result column are dropped, because results would leak real outcomes into the simulation. Playoff rows after a "Playoffs" marker are ignored.

Careers data (22 Basketball-Reference CSVs): follow [CAREERS_DATA_INSTRUCTIONS.md](CAREERS_DATA_INSTRUCTIONS.md).
Miami's cap holds and player tenure (roadmap items 2 and 3): follow [MIAMI_CAP_DATA_INSTRUCTIONS.md](MIAMI_CAP_DATA_INSTRUCTIONS.md).
