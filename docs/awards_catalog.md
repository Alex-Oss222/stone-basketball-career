# NBA awards catalogue

[Catalogue](../library/2003/league/nba_awards_catalog.json) · [Helper](../runtime/award_records.py) · [Player honors](player_statistics.md) · [League awards hub](../career/Dwyane_Wade/Stats_and_Awards/League/README.md) · [Roadmap item 15](ROADMAP.md)

`library/2003/league/nba_awards_catalog.json` lists every NBA award and honor the career can meet, across eras: 36 awards in six scopes (`season`, `monthly`, `weekly`, `playoff`, `all-star`, `cup`) and 14 dated rule changes. It is kept in the 2003 folder, like `00_Team/Finances/league_cap_history.json`, because the career starts in the 2003 cycle; it is world knowledge about how the league decides honors, not a result of any season.

## What each entry holds

| Field | Content |
|---|---|
| `id`, `name`, `short_name`, `scope`, `category` | Identity; `category` is `performance` or `non_performance` (Sportsmanship, Kennedy Citizenship, Teammate of the Year, Social Justice Champion, Community Assist) |
| `competition`, `honor_names` | The report competition an earned honor is filed in, and the exact `name` strings written to `awards.json`; where `runtime/standing.py` has an `HONOR_*` name (All-Star, All-NBA First/Second/Third Team, Most Valuable Player, Finals MVP), the catalogue uses it |
| `first_season`, `last_season` | When the award began and, for a discontinued award (Comeback Player of the Year, 1980-81 to 1985-86), when it ended |
| `conference_split` | When a weekly or monthly award became one per conference (2001-02 for Player of the Week, Player of the Month and Rookie of the Month) |
| `electorate` | `kind` (media panel, coaches, players, fans, league office, committee, writers' association) and `size` |
| `scoring` | The ballot rule: MVP 10-7-5-3-1; Rookie of the Year, Defensive Player, Sixth Man, Most Improved and Coach of the Year 5-3-1; All-NBA 5-3-1; All-Defensive and All-Rookie 2-1 (coaches, no vote for a coach's own player, in 2003-04) |
| `eligibility` | Era rules such as the Sixth Man bench requirement and the statistical titles' qualification minimums |
| `era_rules` | Ids into `rules`: the dated changes that apply to the award |
| `period`, `sources`, `notes` | The award period (defined in `periods`, with announcement timing), the fetched pages, and remarks |

Every fact carries a `status`: `sourced` (stated by a fetched page listed under `sources`, each with its URL and the date it was read), `derived` (computed from figures on a fetched page, with the derivation in the note: the 2003-04 ballot counts of 123 for MVP and All-NBA, 118 for Rookie of the Year and 29 coaches for All-Defensive and All-Rookie come from the maximum point totals on the Basketball-Reference 2003-04 voting page) or `unverified` (no fetched page establishes it). An unverified electorate size or scoring rule is `null`: nothing is invented, and a vote may not use it until it is researched. The repository's 118-ballot fallback for Defensive Player, Sixth Man and Most Improved stays provisional for that reason.

## Era gating

`runtime/award_records.awards_in_force(season)` returns the awards whose `first_season` is on or before the season and whose `last_season` is null or on or after it; `rules_in_force(season)` does the same for the rule changes. Seasons are compared by their starting year (`1999-00` is 1999).

- Only an award in force may be voted. In 2003-04 that excludes the Clutch Player (2022-23), Hustle (2016-17), Teammate of the Year (2012-13), NBA Cup MVP and All-Tournament Team (2023-24), Social Justice Champion (2020-21) and the Bob Lanier season award, and includes MVP, Rookie of the Year, Defensive Player, Sixth Man, Most Improved, Coach and Executive of the Year, All-NBA, All-Defensive, All-Rookie, Player and Rookie of the Month, Player of the Week, the statistical titles, the All-Star honors and the Finals MVP.
- A later rule never applies retroactively. The 65-game eligibility rule (`games_played_65_2023_24`) is catalogued with the awards it covers and marked as a later rule the 2003-04 vote must not use; the same holds for positionless All-NBA and All-Defensive teams (2023-24), the media vote for All-Defensive (2013-14), the 58-game qualification for statistical titles (2013-14) and the All-Star format changes. In 2003-04 the statistical titles use 70 games or the era's total minimums (1,400 points, 800 rebounds, 400 assists, 125 steals, 100 blocks; 300 field goals, 125 free throws and 55 three-pointers made).
- The catalogue says how a vote is run, never who won. Real winners, vote totals and results after June 26, 2003 are not in it and must not be imported; the engine decides the simulated vote (roadmap item 15).

## Periods and announcements

`periods` defines the award windows: the regular season (voting closes after the last game; winners announced during the playoffs), the official Monday-to-Sunday award week (it can cross this repository's fixed day 1-7, 8-14, 15-21, 22-end buckets; the honor is filed on the week page containing the period's end date), the calendar month, the Finals, the All-Star break, game and weekend, and the NBA Cup. Announcement timings are marked like any other fact; most 2004 announcement dates are unverified.

## Not catalogued

Coach of the Month (first season not established by a fetched page), All-Star Saturday contests, the Executive of the Year method under The Sporting News, and team honors that are standings results.
