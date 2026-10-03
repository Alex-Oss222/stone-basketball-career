# Stone Basketball Career

Dwyane Wade's alternate NBA career. The [current checkpoint](career/Dwyane_Wade/2003-04/current_state.json) and [live career desk](https://stone-basketball-career-production.up.railway.app/career) carry the current date and status.

Opening checkpoint: June 26, 2003, Miami's No. 5 draft pick with unsigned draft rights. Later status comes from the dated career records.

## Open the career

**Detailed career desk:** [Open live screens](https://stone-basketball-career-production.up.railway.app/career) · [Detailed career record](career/Dwyane_Wade/Milestones/README.md) · [Shooting and Awards](https://stone-basketball-career-production.up.railway.app/cards).

These screens read this branch's actual career state. Full detail is the default: dated status, complete evidence tables, contract terms, player responses, source records and the next checkpoint. They regenerate with the ordinary career-report and event-update commands. Opening a screen does not advance the career clock or make a player decision.

| Record | What is here |
| --- | --- |
| [Active milestone screens](career/Dwyane_Wade/Milestones/README.md) | Calendar, contract checkpoint, negotiation, free agency, training, trade, exit meeting, camp and statistics, populated from current records |
| [Current Shooting card](career/Dwyane_Wade/Stats_and_Awards/Shooting.md) · [Yearly Awards](career/Dwyane_Wade/Stats_and_Awards/Awards.md) | Actual closed results and earned awards; location coverage is stated explicitly |
| [Current checkpoint](career/Dwyane_Wade/2003-04/current_state.json) | Career date, phase and pending player decisions |
| [Wade's profile](career/Dwyane_Wade/Dwyane_Wade_Player_Profile.md) | Established alternate-history background and abilities |
| [Professional identity](career/Dwyane_Wade/Professional_Identity.md) | Player identity and professional status at the report date |
| [Player season](career/Dwyane_Wade/2003-04/README.md) | Summer League, preseason, regular season and playoff reports |
| [Filled statistics preview](docs/examples/player_stats_preview.md) | Sample season, month, week and game layouts with illustrative numbers |
| [Player milestone previews](docs/examples/player_milestones/README.md) | Contract, free agency, training, trade, exit-meeting and camp examples; [reusable templates](docs/templates/player_milestones/README.md) |
| [National team / FIBA](career/Dwyane_Wade/National_Team/README.md) | Separate World Cup, Olympic, continental and friendly records |
| [Miami team desk](career/Dwyane_Wade/2003-04/00_Team/README.md) | Organization, roster, player cards and rotation |
| [Eight-season cap sheet](career/Dwyane_Wade/2003-04/00_Team/Finances/cap_sheet.md) | Existing obligations from 2003-04 through 2010-11 |
| [Stats and awards](career/Dwyane_Wade/Stats_and_Awards/README.md) | Wade, Miami, league players and award records |
| [Current draft note](career/Dwyane_Wade/2003-04/09_Draft/note.md) | The event that established this checkpoint |

Wade's legitimate player decisions belong to the user. Miami's basketball operations belong to the AI/GM. Contracts, roster moves, games and honors enter the record when they occur in this branch.

## Statistics and player grades

The [2003 source library](library/2003/league/README.md) holds league evidence separately from career results. All 428 players in the supplied 2002-03 veteran dataset have dated engine profiles; 14 Miami veteran cards show statistical estimates and supporting production. The draft class is outside that rating import.

[Rating method](docs/statistical_ratings.md) · [Miami player cards](career/Dwyane_Wade/2003-04/00_Team/Team/Player_Cards/README.md)

The stats hub follows the existing season, month and week folders. Historical rating inputs do not count as current-season results. The cap sheet rolls forward existing obligations; its separate historical cap archive cannot guide decisions before the relevant publication date.

Player reports and active screens default to full detail. Tables cover raw totals, per-game and per-36 production, shooting, estimated efficiency, splits, highs and source games. [Definitions and source requirements](docs/player_statistics.md) explain missing data. NBA Cup is gated to 2023-24 onward, with its championship counted separately.

## Running and maintaining the simulation

[Game engine](runtime/README.md) · [Update workflow](docs/update_workflow.md) · [Season structure](docs/season_structure.md) · [Operating rules](AGENTS.md)

Games run on Railway from validated request files. A result becomes canonical only after it is written into the owning game note. Do not edit a closed game's request to obtain another result.

After a record change, rebuild player reports with `python scripts/update_player_reports.py`, then run `python scripts/validate_repository.py` and `python -m unittest discover -s tests -q`. Veteran-source changes also require `python scripts/import_veteran_stats.py --check`.

What still needs building, in career-clock order: [docs/ROADMAP.md](docs/ROADMAP.md).
