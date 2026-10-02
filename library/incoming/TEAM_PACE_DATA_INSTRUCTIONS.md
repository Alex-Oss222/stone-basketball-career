# How to collect the team pace data (engine problem E6)

Today every club plays at the league's average pace. Real clubs played faster or slower, and that changes possessions, scoring and how much a good team's edge adds up over a game. One team table per season fixes it.

Not needed before opening night. Upload it whenever convenient; the importer is built when the files arrive.

## What to download

One table per season, the **Advanced Stats** team table on each season's main page, for 11 seasons, **2002-03 through 2012-13**. That makes **11 CSV files**.

Each simulated season uses each club's pace from the season **before** it, the same rule as the league averages (AGENTS.md: a season is never calibrated on its own final numbers). So 2003-04 games use the 2002-03 table, and the last season the career data covers, 2013-14, uses 2012-13.

Basketball-Reference names a season by the year it ends, so 2002-03 is `NBA_2003`.

| Season | Used for | Page | Save as |
|---|---|---|---|
| 2002-03 | 2003-04 | https://www.basketball-reference.com/leagues/NBA_2003.html | `nba_2003_team_advanced.csv` |
| 2003-04 | 2004-05 | https://www.basketball-reference.com/leagues/NBA_2004.html | `nba_2004_team_advanced.csv` |
| 2004-05 | 2005-06 | https://www.basketball-reference.com/leagues/NBA_2005.html | `nba_2005_team_advanced.csv` |
| 2005-06 | 2006-07 | https://www.basketball-reference.com/leagues/NBA_2006.html | `nba_2006_team_advanced.csv` |
| 2006-07 | 2007-08 | https://www.basketball-reference.com/leagues/NBA_2007.html | `nba_2007_team_advanced.csv` |
| 2007-08 | 2008-09 | https://www.basketball-reference.com/leagues/NBA_2008.html | `nba_2008_team_advanced.csv` |
| 2008-09 | 2009-10 | https://www.basketball-reference.com/leagues/NBA_2009.html | `nba_2009_team_advanced.csv` |
| 2009-10 | 2010-11 | https://www.basketball-reference.com/leagues/NBA_2010.html | `nba_2010_team_advanced.csv` |
| 2010-11 | 2011-12 | https://www.basketball-reference.com/leagues/NBA_2011.html | `nba_2011_team_advanced.csv` |
| 2011-12 | 2012-13 | https://www.basketball-reference.com/leagues/NBA_2012.html | `nba_2012_team_advanced.csv` |
| 2012-13 | 2013-14 | https://www.basketball-reference.com/leagues/NBA_2013.html | `nba_2013_team_advanced.csv` |

Regular season only. Use the year in the page address; the file name tells the importer the season.

## Steps for each page

1. Open the page.
2. Scroll down to the table called **Advanced Stats**. It has one row per team and columns including Age, W, L, MOV, SRS, ORtg, DRtg, **Pace**, FTr, 3PAr and TS%, followed by the "Offense Four Factors" and "Defense Four Factors" groups. It is not the "Per Game Stats" or "Shooting Stats" table, and not a player table.
3. Above that table, hover over **Share & Export** and click **Get table as CSV (for Excel)**.
4. The table turns into text. Drag from its first line to its last to select it, copy it, paste it into an empty Notepad file and save it as plain text with the name from the table above.

## Do not change anything

- **Keep every team row**, including teams that moved or were renamed (for example the New Orleans/Oklahoma City Hornets in 2005-06 and 2006-07, the Seattle SuperSonics through 2007-08, the New Jersey Nets through 2011-12).
- **Keep the League Average row** and any first line with group names such as "Offense Four Factors". The importer skips them.
- **The asterisk after playoff teams' names is fine.** The importer removes it.
- **Don't edit, sort or open-and-resave in Excel.** If you open a file in Excel, close it without saving.

## Quick check before uploading

- 2002-03 and 2003-04 should have **29** team rows; every season from 2004-05 on should have **30** (the Charlotte Bobcats joined in 2004-05).
- The **Pace** column should hold numbers around 85 to 100.
- The 2002-03 file should include the Miami Heat and the New Orleans Hornets. Miami's row is fine to leave in; the importer ignores it.
- A file with 400 or more rows is the wrong table (players instead of teams).

## Upload

1. Put all 11 files in one folder, for example `C:\Users\alexl\OneDrive\Desktop\Different LLM\Basketball\Repo\team_pace`.
2. Go to https://github.com/Alex-Oss222/stone-basketball-career/tree/milestone-1/library/incoming
3. **Add file → Upload files**, drag in all 11, choose **Commit directly to the milestone-1 branch**, and click **Commit changes**.
4. Tell Claude "team pace uploaded".

## What happens next

The importer keeps only each club's **Pace**, as its style of play, and writes one file per season: `library/<year>/league/nba_<season>_team_pace.json`. Wins, losses, margin, SRS, offensive and defensive ratings and every other column are dropped on import, because they are real results. Miami's row is ignored, since Miami is simulated. The raw CSVs are then removed from `library/incoming`.

Then the engine gives each real club its pace from the season before, scaled so the league as a whole still matches the season's calibration environment. A club with no previous season (Charlotte in 2004-05) plays at the league pace. Miami's pace stays a simulated coaching decision. Nothing in this data is shown to Miami's front office or on player cards before the season it describes is played.
