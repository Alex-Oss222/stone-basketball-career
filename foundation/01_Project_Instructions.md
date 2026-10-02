# Project instructions

## Purpose

Maintain one coherent basketball player career.

The user is the player. Team and league actors are independent.

## Minimal repository rule

Do not copy systems from the football project merely because they exist there. Add a record only when the basketball career needs it.

The retained team systems are limited to roster, rotation, player cards, team configuration and finance state.

## Source hierarchy

1. Explicit player facts and player decisions established by the user.
2. Closed simulation event/game notes.
3. AI/GM team state derived from simulated team decisions.
4. Current state derived from those records.
5. Verified year-specific league rules and dates when later added.

Templates and empty files are never evidence that an event happened.

## Team ownership

`00_Team` is controlled by the simulation's AI/GM. The player may receive offers, role information and team decisions, but does not directly author the team's roster, rotation, financial or tactical outcome.

## State transitions

Phase/week notes: `not_started`, `active`, `complete`.

Game notes: `scheduled`, `played`, `not_played`.

Unknown is not zero. Planned is not completed.

## Postseason

Play-In is not applicable before 2019-20. Its 2020 restart format differs from 2020-21 onward. Where applicable, Play-In Game 2 exists only when Game 1 requires it.

Every playoff series is best of seven. Games 5, 6 and 7 are conditional. A conditional game may remain absent if never scheduled, or be marked `not_played` with a reason.

## External game runner

A game may be simulated in Relay or another runner. The external output becomes part of the career only after it is written into the correct game record and passes repository validation.
