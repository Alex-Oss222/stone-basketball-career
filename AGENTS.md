# Agent operating rules

This is a player-career simulation.

## Player authority

The user controls only decisions a real player can control, such as accepting or rejecting offers when the player has that choice, representation, training choices, responses, and other player-level decisions.

The user does not directly control coaching, rotations, roster construction, trades initiated by teams, salary-cap accounting, medical clearance, officiating, league actions, opponents, teammates, awards, or game results.

## AI/GM-owned team state

Everything under `career/<player>/<year>/00_Team` is simulation-owned.

The AI/GM maintains:
- `team_config.json`
- `Team/roster.json`
- `Team/rotation.json`
- team player cards
- `Finances/finance.json`

A player decision may cause the AI/GM to react, but do not rewrite team state merely because the user asks for a preferred rotation, transaction, contract accounting result, or roster move.

## Read order

Before advancing the career:

1. `career/<player>/player_profile.md`
2. `career/<player>/<year>/current_state.json`
3. `career/<player>/<year>/00_Team/team_config.json`
4. roster and rotation when a game or team decision needs them
5. the current phase/week/game note

Read finance data only when contracts, cap rules, transactions, or team-building consequences require it.

## Empty means unknown

The skeleton contains no real player, team, season, schedule, contract, injury, statistic, result, or transaction.

Null, blank and empty values are not zeroes and are not completed events.

## Chronology

Month week buckets are fixed:
- Week 1: days 1 to 7
- Week 2: days 8 to 14
- Week 3: days 15 to 21
- Week 4: day 22 through month end

Folder numbering is navigation. Actual dates control chronology. The draft can overlap the playoffs on the real calendar.

## Game records

Game execution may be performed by Relay or another game runner. A game result is not canonical until it is written to the correct career game note.

Game-note statuses:
- `scheduled`: date and opponent required, no result yet
- `played`: date, opponent and result required
- `not_played`: reason required, no result

Never use an empty game file as a placeholder.

Play-In Game 2 may exist only after Game 1 is played and says `next_game_required: true`.

Every playoff round is best of seven. Games 5, 6 and 7 are conditional. Create them only when scheduled, or explicitly mark an unused slot `not_played` if the simulation needs a closure record.

## Event ownership

Write an event once in its most specific note. Update `current_state.json` only for current-state consequences.

Plans are not results. Rumors are not transactions. Scheduled games are not played games.

## No hindsight

Do not use later real-world outcomes to steer earlier simulated choices. Year-specific real rules and dates must be verified for the season before they are treated as authoritative.

## After an event

1. write the event owner;
2. update affected current state;
3. update AI/GM team state only when the simulated team actually changed;
4. run repository validation;
5. run tests.
