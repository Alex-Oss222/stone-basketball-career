# Stone Basketball Career

Dwyane Wade · Miami Heat · June 26, 2003

No. 5 draft pick. Miami owns Wade's rights; his contract is unsigned. The 2003-04 NBA season has not started.

## Open the career

| Record | What is here |
| --- | --- |
| [Current checkpoint](career/Dwyane_Wade/2003-04/current_state.json) | Career date, phase and pending player decisions |
| [Wade's profile](career/Dwyane_Wade/Dwyane_Wade_Player_Profile.md) | Established alternate-history background and abilities |
| [Miami team desk](career/Dwyane_Wade/2003-04/00_Team/README.md) | Organization, roster, player cards and rotation |
| [Eight-season cap sheet](career/Dwyane_Wade/2003-04/00_Team/Finances/cap_sheet.md) | Existing obligations from 2003-04 through 2010-11 |
| [Stats and awards](career/Dwyane_Wade/Stats_and_Awards/README.md) | Wade, Miami, league players and award records |
| [Current draft note](career/Dwyane_Wade/2003-04/09_Draft/note.md) | The event that established this checkpoint |

Wade's legitimate player decisions belong to the user. Miami's basketball operations belong to the AI/GM. Contracts, roster moves, games and honors enter the record when they occur in this branch.

## Statistics and player grades

The [2003 source library](library/2003/league/README.md) holds league evidence separately from career results. All 428 players in the supplied 2002-03 veteran dataset have dated engine profiles; 14 Miami veteran cards show statistical estimates and supporting production. The draft class is outside that rating import.

[Rating method](docs/statistical_ratings.md) · [Miami player cards](career/Dwyane_Wade/2003-04/00_Team/Team/Player_Cards/README.md)

The stats hub follows the existing season, month and week folders. Historical rating inputs do not count as current-season results. The cap sheet rolls forward existing obligations; its separate historical cap archive cannot guide decisions before the relevant publication date.

## Running and maintaining the simulation

[Game engine](runtime/README.md) · [Update workflow](docs/update_workflow.md) · [Season structure](docs/season_structure.md) · [Operating rules](AGENTS.md)

Games run on Railway from validated request files. A result becomes canonical only after it is written into the owning game note. Do not edit a closed game's request to obtain another result.

After a record change, run `python scripts/validate_repository.py` and `python -m unittest discover -s tests -q`. Veteran-source changes also require `python scripts/import_veteran_stats.py --check`.
