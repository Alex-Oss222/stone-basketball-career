# NBA League Stats & Awards

This is the league-wide companion to Wade's personal Stats & Awards record. Wade's existing `Stats_and_Awards/README.md` is not changed.

## Structure

```text
League/
  player_registry.json
  2003-04/
    League_Stats.md
    League_Awards.md
    10_October/
      League_Stats.md
      League_Awards.md
      Week_3/
        League_Stats.md
        League_Awards.md
      ...
```

The registry tracks every player in the June 26 league pool. Stats pages group every player by primary position: PG, SG, SF, F, PF, C. Inside a position, players are alphabetical so the page is a record, not a subjective ranking.

League leader tables sit above the full positional tables. This mirrors standard NBA/Basketball-Reference player-stat fields while preserving the user's position-grouped view.

Season awards publish the top three vote-getters. Weekly and monthly pages preserve a top-three internal shortlist, while the winner is marked **WINNER** when the award closes.
