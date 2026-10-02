# How to collect the league organization data (head coaches)

This gives every club's head coach, season by season: who coaches the opponents and who is eligible for Coach of the Year. The other 28 clubs follow history (world model D), so this is reference data. They make no simulated decisions, and Miami's own coaches stay in its organization records.

## What to download

One table per season, the **Coaches** table on each season's coaches page. That's 12 seasons, 2002-03 through 2013-14, so **12 CSV files**. 2002-03 gives the coaches as of the current career date, June 2003.

Basketball-Reference names a season by the year it ends, so 2002-03 is `NBA_2003`.

| Season | Page | Save as |
|---|---|---|
| 2002-03 | https://www.basketball-reference.com/leagues/NBA_2003_coaches.html | `nba_2003_coaches.csv` |
| 2003-04 | https://www.basketball-reference.com/leagues/NBA_2004_coaches.html | `nba_2004_coaches.csv` |
| 2004-05 | https://www.basketball-reference.com/leagues/NBA_2005_coaches.html | `nba_2005_coaches.csv` |
| 2005-06 | https://www.basketball-reference.com/leagues/NBA_2006_coaches.html | `nba_2006_coaches.csv` |
| 2006-07 | https://www.basketball-reference.com/leagues/NBA_2007_coaches.html | `nba_2007_coaches.csv` |
| 2007-08 | https://www.basketball-reference.com/leagues/NBA_2008_coaches.html | `nba_2008_coaches.csv` |
| 2008-09 | https://www.basketball-reference.com/leagues/NBA_2009_coaches.html | `nba_2009_coaches.csv` |
| 2009-10 | https://www.basketball-reference.com/leagues/NBA_2010_coaches.html | `nba_2010_coaches.csv` |
| 2010-11 | https://www.basketball-reference.com/leagues/NBA_2011_coaches.html | `nba_2011_coaches.csv` |
| 2011-12 | https://www.basketball-reference.com/leagues/NBA_2012_coaches.html | `nba_2012_coaches.csv` |
| 2012-13 | https://www.basketball-reference.com/leagues/NBA_2013_coaches.html | `nba_2013_coaches.csv` |
| 2013-14 | https://www.basketball-reference.com/leagues/NBA_2014_coaches.html | `nba_2014_coaches.csv` |

## Steps for each page

1. Open the page. It has one table, **Coaches**: one row per coach and club, with columns such as Coach, Tm, Seasons, and regular-season and playoff records.
2. Above the table, hover over **Share & Export** and click **Get table as CSV (for Excel)**.
3. Drag from the first line of the text to the last to select it, copy it, paste it into an empty Notepad file and save it under the name in the table above.

## Do not change anything

- **Keep every row.** A club that changed coaches during a season has two or three rows. The rows in between seasons are fine too.
- **Keep the extra header lines** (the group names above the columns). The importer skips them.
- **Keep the last column** if it holds the coach's Basketball-Reference ID (like `brownla01`).
- **Don't edit, sort or open-and-resave in Excel.**

## Quick check before uploading

- Each file has at least one row per club: 29 clubs through 2003-04 and 30 from 2004-05, plus a row for every mid-season change.
- The 2002-03 file includes Pat Riley with Miami (MIA).

## Upload

1. Put all 12 files in one folder, for example `C:\Users\alexl\OneDrive\Desktop\Different LLM\Basketball\Repo\coaches`.
2. Go to https://github.com/Alex-Oss222/stone-basketball-career/tree/milestone-1/library/incoming
3. Click **Add file → Upload files**, drag in all 12, choose **Commit directly to the milestone-1 branch**, and click **Commit changes**.
4. Tell Claude "coaches uploaded".

## What happens next

The importer keeps each club's coaches for each season, in order. Each coach gets the part of the season he coached, placed by his games coached, the same way traded players are placed. Wins, losses and playoff records are dropped, because they are real results. A coaching change counts only once the career clock reaches it, so nothing about a later change is used early (AGENTS.md, No hindsight). Miami's rows are ignored. Miami's coaches are simulated and live in `career/Dwyane_Wade/<season>/00_Team/Organization/`.

The files go into `library/<year>/league/nba_<season>_coaches.json`.
