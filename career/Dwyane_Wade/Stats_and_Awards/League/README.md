# NBA | Statistics and awards

<!-- contract-navigation:start -->
[Current contracts and contract history for every tracked player](../../Contracts/index.html)
<!-- contract-navigation:end -->

[Stats hub](../README.md) · [2003-04 players](2003-04/League_Stats.md) · [2003-04 awards](2003-04/League_Awards.md) · [2003-04 standings](2003-04/Standings.md) · [2004 playoffs](2003-04/Playoffs.md) · [2004-05 players](2004-05/League_Stats.md) · [2004-05 awards](2004-05/League_Awards.md) · [2004-05 standings](2004-05/Standings.md) · [2005 playoffs](2004-05/Playoffs.md) · [2005-06 players](2005-06/League_Stats.md) · [2005-06 awards](2005-06/League_Awards.md) · [2005-06 standings](2005-06/Standings.md) · [2006 playoffs](2005-06/Playoffs.md) · [Player registry](player_registry.json) · [Player cards](Players/README.md)

The league pages cover 653 registered players. All entries remain available in six position groups, with the complete per-game table in the same order as the player pages. A closed group keeps the page short; opening it reveals every player in that position, alphabetically.

![NBA per-game statistics](assets/per_game.svg)

Season, month and week pages include age on the page's label date (the period's end, or the career date while it runs), the dated club (the clubs he played for in the period, in stint order, else his club on the label date; `—` before he reached the league) or draft rights, league, position, games, starts, minutes, all shooting makes and attempts, shooting efficiency, offensive and defensive rebounds, assists, steals, blocks, turnovers, fouls and points. G and GS are counts; the other counting columns are per appearance. Shooting uses .500 = 50.0%. Identity comes from the dated registry; its birth dates are available in the registry link. The red-and-black section header has no awards banner; award decisions remain in their linked records.

An unavailable column stays N/A until closed branch game evidence supplies it. The presentation formatter (`scripts/format_league_reports.py`) preserves existing period values and navigation; it does not collect engine results, reconstruct attempts from rounded averages, or populate leaders. The write-back (`scripts/write_back_results.py`, [rules](../../../../docs/player_statistics.md#write-back)) aggregates the closed results into these pages and fills the period comparison under Leaders; a player in a closed result who is not yet registered is added, dated by his first appearance (`write_back.extend_registry`). The navigation above, the player count and the cohort counts below are restated from the season list and the registry on every full write-back (`season_pages.hub`), and a closed season's pages follow the registry's names and the dated club rule ([player cards guide](../../../../docs/player_cards.md)).

## Coverage and rankings

The registry combines 349 prior-season roster identities, 58 2003 draft entries and 246 players added at their first closed appearance in any season (cohort `2003_04_appearance`). The dated club or draft-rights label does not establish an active contract, availability or an opening-night team. The 428-player historical rating dataset is separate. Roster membership changes only through dated branch records.

G is appearances. Averages and percentages need valid denominators. Publish period leaders with G and relevant attempts, and verify the 2003-04 qualification rule before declaring an official season leader. Weekly and monthly leaders are period comparisons; they are not automatically qualified season leaders. No closed games means no leader, not a tie at zero.

## Award records

| Record | Display | Evidence needed |
| --- | --- | --- |
| Player of the Week | East and West, three internal shortlist slots each | Exact award period, announcement date and branch games |
| Player / Rookie of the Month | East and West shortlists for each honor | Exact period, availability and relevant branch production |
| Season individual vote | Top three finishers, first-place votes and points | Closed ballots or full tally, electorate, scoring and tie rule |
| All-NBA / All-Defensive / All-Rookie | Selected teams | Era-specific positions, eligibility and selection record |

Weekly and monthly shortlists are internal; they do not imply the NBA published ranked finalists or numerical ballots. Mark **WINNER** only after the decision closes. Keep the shortlist visible, with its evidence. A calendar bucket can contain no award. File an award in the bucket containing its official period's end date, including awards whose window crosses weeks or months.

Season pages retain the branch's 10-7-5-3-1 MVP and 5-3-1 individual-award scoring. The configured 123/118 ballot counts are procedure inputs, not votes already cast; the 118-voter fallback for DPOY, Sixth Man and MIP remains provisional. Verify award-specific rules and totals before closing. Do not import real winners or the later 65-game eligibility rule. The era-gated catalogue of every award, its electorate, scoring rule and first season is `library/2003/league/nba_awards_catalog.json` (`docs/awards_catalog.md`); only awards and rules it lists as in force for 2003-04 may be used. All-Rookie uses the established 29-coach, 2-1 model without votes for a coach's own player.

## Research basis

- [NBA traditional statistics](https://www.nba.com/stats/players/traditional): production and shooting categories. Shared units and aggregation rules are in the [stats hub](../README.md).
- [NBA conference weekly announcement](https://official.nba.com/miamis-bosh-and-golden-states-thompson-named-nba-eastern-and-western-conference-players-of-the-week/): exact periods, winners and other nominees, rather than a public ranked ballot. This is a format reference, not a 2003 result.
- [NBA voting publications](https://pr.nba.com/voting-results-2023-24-nba-regular-season-awards/): distinct published voting records for season awards. No later award categories are imported.
- [2003-04 Rookie of the Year procedure](https://www.nba.com/cavaliers/news/lbj_roy_040420.html) and [All-Rookie procedure](https://www.nba.com/cavaliers/news/lbj_allrookie_040427.html): existing era-method references, never sources for branch winners.

Update weekly evidence first, then its month and season. Retain the full positional registry on every period page and keep all source-game and decision links resolvable.
