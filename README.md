# Basketball Player Career Simulation

An empty, player-centered basketball career framework. The user controls one player's consequential choices. The simulation records the basketball world around that player without granting the user coach, general manager, or league authority.

## Start here

1. Read `state/career_state.json`.
2. Read `state/player_profile.md`.
3. Read `config/season_structure.json`.
4. Open the current area or week note.
5. Follow `AGENTS.md` before advancing the career.

No player, team, season year, schedule, result, contract, injury, award, or transaction is prefilled.

## Season route

1. `01_Free_Agency`
2. `02_Summer_League`
3. `03_Offseason`
4. `04_Training_Camp`
5. `05_Preseason`
6. `06_Regular_Season`
7. `07_Play_In_Tournament`
8. `08_Playoffs`
9. `09_Draft`

The numbered folders are navigation. Actual dates control chronology. The draft lottery and combine can occur while the playoffs are still running.

## Stability model

- Stable rules live in `foundation` and `config`.
- Live player/career state lives in `state`.
- Actual events are written once in the applicable area/week/game note.
- Conditional play-in and playoff games are never represented by ambiguous empty game notes.
- `scripts/validate_repository.py` checks structure and note state.
- `tests` checks calendar week bucketing and best-of-seven rules.
- GitHub Actions runs validation and tests without third-party Python packages.

Run locally:

```sh
python scripts/validate_repository.py
python -m unittest discover -s tests -v
```
