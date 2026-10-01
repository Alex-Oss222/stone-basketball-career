# Basketball Player Career Simulation

An empty basketball career framework centered on one player.

The repository is organized like this:

```text
career/
  <player>/
    player_profile.md
    <year>/
      00_Team/
      01_Free_Agency/
      02_Summer_League/
      03_Offseason/
      04_Training_Camp/
      05_Preseason/
      06_Regular_Season/
      07_Play_In_Tournament/
      08_Playoffs/
      09_Draft/
```

The committed `career/PLAYER/YEAR` path is an empty skeleton. Rename `PLAYER` and `YEAR` when the career is initialized. It does not establish a real player or season.

## Ownership

The user controls the player.

`00_Team` is AI/GM controlled. Its team configuration, roster, rotation and finance records are maintained by the simulation, not chosen directly by the player.

Game execution may happen outside this repository, including Relay. The repository owns the stable career state, game records and continuity checks.

## Checks

```sh
python scripts/validate_repository.py
python -m unittest discover -s tests -v
```
