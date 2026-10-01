# Agent operating rules

This repository is a player-career simulation, not a coaching or front-office simulation.

## Authority

The user controls the player only: contract choices presented to the player, representation choices, training choices, public or private responses, participation choices when legitimately available, and other decisions a real player could make.

The simulator controls everything outside that authority: coaches, front offices, teammates, opponents, agents when not directly instructed, media, league decisions, schedules, game outcomes, awards, injuries, transactions initiated by other actors, and market interest.

Never silently give the player coach, general manager, owner, doctor, referee, or league powers.

## Read order

Before advancing anything:

1. `state/career_state.json`
2. `state/player_profile.md`
3. `config/season_structure.json`
4. the current phase/week/game note
5. any directly linked prior event note needed for continuity

Do not infer a completed event from an empty file, folder name, or future placeholder.

## Empty-state rule

This repository starts with no career facts. Blank profile fields and null state values are intentional. Do not fill them unless the user establishes the fact or the simulation legitimately resolves it.

## Clock and chronology

The numbered season route is navigation, not proof of date order. Actual dated events control the career clock.

Month-week buckets are fixed:
- Week 1: days 1 to 7
- Week 2: days 8 to 14
- Week 3: days 15 to 21
- Week 4: day 22 through the end of the month

Do not create a fifth monthly week.

## Event ownership

Write a factual event once, in the most specific owning note. Update `state/career_state.json` only for current-state consequences.

Do not duplicate the same game result, transaction, injury, or decision as separate competing narratives.

Plans are not results. Scheduled games are not played games. Rumors are not transactions.

## Game-note protocol

A game note may have only one of these statuses:

- `scheduled`: the game is actually scheduled; date and opponent are required.
- `played`: the game occurred; date, opponent, and result are required.
- `not_played`: the slot is explicitly unused; a reason is required.

Never create a blank game note.

Play-In Game 2 does not exist unless Game 1 was played and its metadata says `next_game_required: true`.

Every playoff series is best of seven. Games 5, 6, and 7 are conditional. Create one when it is scheduled. After a series ends, an unused conditional game may remain absent or may be recorded as `not_played`. Absence is not a game result.

## Player perspective

Keep player knowledge separate from omniscient simulation state. The player can learn only what has been communicated, observed, published, or otherwise made available to the player.

Do not expose hidden team deliberations as known facts unless the simulation has a legitimate information channel.

## No hindsight

Do not use future real-world outcomes to steer an earlier simulated decision. If historical data is later added, label its information date and do not leak later results backward.

## Update discipline

After a completed event:

1. update the owning note;
2. update current state only if the event changes current state;
3. preserve unresolved choices as unresolved;
4. validate the repository;
5. run tests.

If validation fails, do not treat the career as advanced.
