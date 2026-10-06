# NBA 2004-05 | League slate

[League records](../../README.md) · [2004-05 players](../League_Stats.md) · [2004-05 awards](../League_Awards.md) · [Game engine](../../../../../../runtime/README.md)

Every regular-season game between two real clubs, as a game request for the engine, written by
`python scripts/build_league_slate.py --write <date>` on or before each game's date from the season
schedule (`library/2004/league/nba_2004_05_schedule.json`). Both clubs play
their real roster on the game's date (`"rotation": "real"`, world model D in `AGENTS.md`); Miami's games
are not here, they live in Miami's season folder with their game notes.

`<game_id>.request.json` is the request; `scripts/collect_results.py` writes the engine's answer to
`<game_id>.result.json` beside it. A result here is a simulation record of the league (standings and
league statistics read it), not a statistics page and not a player's game record. A request is never
edited once written.
