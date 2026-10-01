# Season structure

The active hierarchy is:

```text
career/<player>/<year>/
```

The player profile is stored at `career/<player>/player_profile.md`. Each year contains the AI/GM team state and the season route.

## Team state

`00_Team` exists before the numbered player phases because the game runner needs a roster, rotation and team context.

It contains only:
- team configuration
- roster
- rotation
- team player cards
- finance state

These records are AI/GM-owned.

## Season route

| Folder | Window |
|---|---|
| `01_Free_Agency` | June 30 to early July |
| `02_Summer_League` | July |
| `03_Offseason` | August to mid September |
| `04_Training_Camp` | late September |
| `05_Preseason` | early to mid October |
| `06_Regular_Season` | mid/late October to mid April |
| `07_Play_In_Tournament` | after regular season |
| `08_Playoffs` | April to June |
| `09_Draft` | lottery/combine in May, draft in late June |

Folder order is navigation. Real dates control chronology.

## Month weeks

- Week 1: days 1 to 7
- Week 2: days 8 to 14
- Week 3: days 15 to 21
- Week 4: day 22 through month end

October contains Weeks 3 and 4. November through March contain Weeks 1 through 4. April contains Weeks 1 and 2.

## Game files

Regular-season game files live inside the applicable month/week folder.

Play-In and playoff game files live in their respective tournament/series folders.

Do not pre-create empty game files. Use `scripts/create_game_note.py` when a game is actually scheduled, or when an unused conditional slot must be explicitly recorded as `not_played`.
