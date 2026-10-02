# How to collect the careers data

This one dataset does two jobs:

1. **Player ability** (option C): every real player's season-by-season rates.
2. **The real league** (option D): every non-Miami team's roster and how its minutes were split, season by season.

That means it needs **every player who played**, not just the stars. Every opponent needs a full lineup.

## What to download

Two tables per season from Basketball-Reference, for 11 seasons, 2003-04 through 2013-14. That makes **22 CSV files**.

Basketball-Reference names a season by the year it ends, so 2003-04 is `NBA_2004`.

| Season | Totals page | Advanced page |
|---|---|---|
| 2003-04 | https://www.basketball-reference.com/leagues/NBA_2004_totals.html | https://www.basketball-reference.com/leagues/NBA_2004_advanced.html |
| 2004-05 | https://www.basketball-reference.com/leagues/NBA_2005_totals.html | https://www.basketball-reference.com/leagues/NBA_2005_advanced.html |
| 2005-06 | https://www.basketball-reference.com/leagues/NBA_2006_totals.html | https://www.basketball-reference.com/leagues/NBA_2006_advanced.html |
| 2006-07 | https://www.basketball-reference.com/leagues/NBA_2007_totals.html | https://www.basketball-reference.com/leagues/NBA_2007_advanced.html |
| 2007-08 | https://www.basketball-reference.com/leagues/NBA_2008_totals.html | https://www.basketball-reference.com/leagues/NBA_2008_advanced.html |
| 2008-09 | https://www.basketball-reference.com/leagues/NBA_2009_totals.html | https://www.basketball-reference.com/leagues/NBA_2009_advanced.html |
| 2009-10 | https://www.basketball-reference.com/leagues/NBA_2010_totals.html | https://www.basketball-reference.com/leagues/NBA_2010_advanced.html |
| 2010-11 | https://www.basketball-reference.com/leagues/NBA_2011_totals.html | https://www.basketball-reference.com/leagues/NBA_2011_advanced.html |
| 2011-12 | https://www.basketball-reference.com/leagues/NBA_2012_totals.html | https://www.basketball-reference.com/leagues/NBA_2012_advanced.html |
| 2012-13 | https://www.basketball-reference.com/leagues/NBA_2013_totals.html | https://www.basketball-reference.com/leagues/NBA_2013_advanced.html |
| 2013-14 | https://www.basketball-reference.com/leagues/NBA_2014_totals.html | https://www.basketball-reference.com/leagues/NBA_2014_advanced.html |

Regular season only. Playoff tables are not needed.

## Steps for each page

1. Open the page.
2. Find the main table: "Player Totals" or "Player Advanced".
3. If the table has a toggle that hides partial rows or non-qualifiers, **turn it off** so every row shows.
4. Above the table, click **Share & Export**, then **Get table as CSV (for Excel)**.
5. The page now shows the table as text. Select all of it, copy it, paste it into an empty Notepad file and save it as plain text with the name below.

| Table | Save as |
|---|---|
| Totals | `nba_2004_totals.csv`, `nba_2005_totals.csv`, ... `nba_2014_totals.csv` |
| Advanced | `nba_2004_advanced.csv`, `nba_2005_advanced.csv`, ... `nba_2014_advanced.csv` |

Use the year in the page address. The file names tell the importer the season and the table.

## Do not change anything

- **Keep the traded-player rows.** A traded player appears once per team plus a combined row, marked `TOT` on older exports or `2TM`/`3TM` on newer ones. All of them are needed: the team rows give each team's roster and minutes, and the combined row gives the player's season.
- **Keep the last column**, `Player-additional`, if it appears. It holds each player's Basketball-Reference ID, such as `jamesle01`, which is how players are matched across seasons. If your export has no such column, that is fine; say so when you upload.
- **Keep the repeated header lines and blank lines.** The importer skips them.
- **Don't edit, sort, filter or open-and-resave in Excel.** Excel can change names with accents and number formats. If you open a file in Excel, close it without saving.

## Quick check before uploading

Each season's totals file should have roughly 450 to 600 data rows: about 430 to 480 players plus extra rows for traded players. The 2003-04 file should include LeBron James on CLE and the 2013-14 file should include Kevin Durant on OKC. A file with only around 20 rows is the wrong table (team totals instead of players).

## Upload

1. Put all 22 files in one folder, for example `C:\Users\alexl\OneDrive\Desktop\Different LLM\Basketball\Repo\careers`.
2. Go to https://github.com/Alex-Oss222/stone-basketball-career/tree/milestone-1/library/incoming
3. **Add file → Upload files**, drag in all 22, choose **Commit directly to the milestone-1 branch**, and click **Commit changes**.
4. Tell Claude "careers uploaded".

## What happens next

The importer builds two library files and checks them:

- `library/careers/nba_player_careers.json`: each player's season rates for the engine (option C).
- `library/<year>/league/nba_<season>_team_rosters.json`: each non-Miami team's roster and minute shares for that season (option D).

The raw CSVs are then removed from `library/incoming`. Nothing in this data is shown to Miami's front office or on player cards before the season it describes is played.
