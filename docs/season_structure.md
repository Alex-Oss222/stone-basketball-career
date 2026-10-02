# Season and player-report structure

[Career](../career/Dwyane_Wade/README.md) · [Filled statistics preview](examples/player_stats_preview.md) · [Definitions and update contract](player_statistics.md)

The active season is 2003-04, at June 26, 2003. This reporting structure does not advance the simulation.

| Location below `career/Dwyane_Wade/` | Purpose |
| --- | --- |
| `Professional_Identity.md` / `professional_identity.json` | Player identity, physical profile and dated professional status |
| `2003-04/README.md` | Season overview, separate competition rows and monthly rollup |
| `2003-04/00_Team/` | AI/GM-owned organization, roster, depth chart, cards and finances |
| `2003-04/01_Free_Agency/` | Dated player/club decisions |
| `2003-04/02_Summer_League/` | Player summary, detailed stats and actual Summer League games |
| `2003-04/03_Offseason/` | Dated offseason decisions |
| `2003-04/04_Training_Camp/` | Dated camp decisions |
| `2003-04/05_Preseason/` | Player summary, detailed stats and preseason games |
| `2003-04/06_Regular_Season/<month>/Week_N/` | Season/month/week READMEs, owning notes and game results |
| `2003-04/07_Play_In_Tournament/` | Compatibility index; explicitly inapplicable in 2003-04; no games |
| `2003-04/08_Playoffs/<round>/` | Postseason and series reports; games when scheduled |
| `2003-04/09_Draft/` | Draft event and decisions |
| `Stats_and_Awards/<season>/<month>/Week_N/` | Regular-season player reports and preserved award links |
| `Stats_and_Awards/Team/` and `League/` | Existing same-period team, league-player and award records |
| `National_Team/<family>/<edition>/<stage>/` | Separate national competitions and stages |

Months stay named `10_October`, `11_November`, `12_December`, `01_January`, `02_February`, `03_March`, `04_April`. Prefixes preserve existing paths. January-April use the second calendar year. Future season calendars must follow their verified schedules.

| Week | Dates |
| --- | --- |
| Week 1 | Days 1-7 |
| Week 2 | Days 8-14 |
| Week 3 | Days 15-21 |
| Week 4 | Day 22 through month end |

READMEs contain professional identity and a concise statistical summary. `Stat_Detail.md` adds totals, per-game and per-36 production, shooting, estimated efficiency, splits, highs and source games. Decisions remain in `note.md`; one game has one canonical owner. Do not create empty game placeholders.

NBA Cup appears only in existing **2023-24 onward** seasons at `<season>/10_NBA_Cup/`. Its non-championship games stay in regular-season weeks and are referenced by the Cup view. Only the championship owns a game in `10_NBA_Cup/Championship/`, excluded from regular-season and playoff totals. No future career season is created merely to display the Cup.

Play-In is unavailable before 2019-20. That restart had an exceptional format; 7-through-10 starts in 2020-21. Reporting support does not unlock engine eras. Verify each competition's dates and rules for the applicable season.

National folders are `World_Cup`, `Olympics`, `Continental_Cups` and `Friendlies`. Editions, qualifiers/finals and represented countries are explicit. See the [national-game contract](player_statistics.md) for paths and metadata.

Actual dates control chronology, so the June 26 draft can close before June 30 free agency despite Draft being folder 09. Team state, finances and the detailed alternate-history profile remain separate from player reports.
