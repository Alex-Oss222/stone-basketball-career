# Team pace data (engine problem E6, later)

Today every club plays at the league's pace. Real clubs played faster or slower, and that changes possessions, scoring and how much a good team's edge adds up over a game. One table per season covers it.

Nothing here is needed before opening night. Upload it when convenient; the importer is built when the data arrives.

## What to download

The **Advanced Stats** team table on each season page, 11 seasons, 2003-04 through 2013-14. Basketball-Reference names a season by the year it ends.

| Season | Page | Save as |
|---|---|---|
| 2003-04 | https://www.basketball-reference.com/leagues/NBA_2004.html | `nba_2004_team_advanced.csv` |
| 2004-05 | https://www.basketball-reference.com/leagues/NBA_2005.html | `nba_2005_team_advanced.csv` |
| 2005-06 | https://www.basketball-reference.com/leagues/NBA_2006.html | `nba_2006_team_advanced.csv` |
| 2006-07 | https://www.basketball-reference.com/leagues/NBA_2007.html | `nba_2007_team_advanced.csv` |
| 2007-08 | https://www.basketball-reference.com/leagues/NBA_2008.html | `nba_2008_team_advanced.csv` |
| 2008-09 | https://www.basketball-reference.com/leagues/NBA_2009.html | `nba_2009_team_advanced.csv` |
| 2009-10 | https://www.basketball-reference.com/leagues/NBA_2010.html | `nba_2010_team_advanced.csv` |
| 2010-11 | https://www.basketball-reference.com/leagues/NBA_2011.html | `nba_2011_team_advanced.csv` |
| 2011-12 | https://www.basketball-reference.com/leagues/NBA_2012.html | `nba_2012_team_advanced.csv` |
| 2012-13 | https://www.basketball-reference.com/leagues/NBA_2013.html | `nba_2013_team_advanced.csv` |
| 2013-14 | https://www.basketball-reference.com/leagues/NBA_2014.html | `nba_2014_team_advanced.csv` |

## Steps for each page

1. Open the page and scroll to **Advanced Stats** (the team table with columns such as Age, W, L, MOV, SRS, ORtg, DRtg, Pace).
2. Click **Share & Export**, then **Get table as CSV (for Excel)**.
3. Copy the text into an empty Notepad file and save it under the name in the table.
4. Put the files in `library/incoming/` and commit.

## What happens to it

Only each club's **Pace** is kept, as a style of play. Wins, losses, margin, ratings and every other result column are dropped on import, because they are real outcomes. Miami's row is ignored, since Miami is simulated.
