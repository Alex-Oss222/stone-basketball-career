# Agent operating rules

This is a player-career simulation centered on Dwyane Wade.

## Authority

The user controls Wade's legitimate player decisions.

The AI/GM controls Miami's organization, roster construction, cap accounting, contracts offered by the club, depth chart, rotation, tactics, staff decisions and transactions. The user can react to those decisions as Wade but cannot directly author them.

## Current checkpoint

- Date: June 26, 2003
- Event: 2003 NBA Draft
- Team: Miami Heat
- Selection: No. 5 overall
- Contract state: Miami owns Wade's draft rights; he is not yet signed.

Do not import a later 2003 event before the career clock reaches it.

## Read order

1. `career/Dwyane_Wade/Dwyane_Wade_Player_Profile.md`
2. `career/Dwyane_Wade/2003-04/current_state.json`
3. `career/Dwyane_Wade/2003-04/00_Team/Organization/README.md`
4. `career/Dwyane_Wade/2003-04/00_Team/team_config.json`
5. roster and depth chart
6. player cards needed for the current event
7. finances only when contract, cap or transaction consequences matter
8. current phase/week/game note

## Team state

Everything under `00_Team` is simulation-owned.

Organization files record basketball decision makers only. Business-side staff are excluded unless a future basketball event actually requires them.

Roster means the current team-control register at the stated date. Expiring contracts, pending options, draft rights and unavailable players must be labeled rather than silently treated as guaranteed active players.

Depth chart is a working basketball view, not a user choice and not a promise of minutes. At the June 26 checkpoint it carries the just-completed 2002-03 positional order and leaves the two new draft picks unassigned until the coaching staff makes a new decision.

## No hindsight

Do not import:
- Anthony Carter's June 30 option outcome before June 30.
- June 30 team-option, qualifying-offer or waiver decisions before June 30.
- July free-agent signings before their dates.
- the later 2003 head-coaching change before it occurs.
- final 2003-04 standings, statistics, awards or transactions.

A later source may be used to reconstruct a contract term that already existed, but not to reveal a future choice or result to the simulation.

`00_Team/Finances/league_cap_history.json` intentionally stores the real six-season cap sequence for continuity. Treat only a cap that has reached its season/publication gate as live front-office knowledge. Never use a future row to influence an earlier contract, trade or free-agency decision.

## Player cards

Every player in the team-control register has a player card.

Cards are personnel records, not automatic game-engine ratings. Objective identity, contract/control and prior production may be entered when sourced. Subjective grades remain `Unassessed` until the simulation has an evidence basis.

User-supplied player photos can be linked later. Do not invent image URLs.

## Game records

Game-note statuses are `scheduled`, `played`, or `not_played`.

Never create a blank game placeholder. Play-In Game 2 is conditional. Playoff Games 5, 6 and 7 are conditional.

Relay or another runner may simulate a game, but raw external output is not canonical until written into the correct career record.

## After an event

1. write the owning event note;
2. update current state;
3. update affected AI/GM team records only when Miami actually changed;
4. run repository validation;
5. run tests.
