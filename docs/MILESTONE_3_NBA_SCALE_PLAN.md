# Milestone 3 — NBA-scale league (execution plan)

## Decision (approved)

- **Full NBA rebuild**: 30 teams, 82 games per team (41 home / 41 away), the real
  174-day October→April regular season, play-in, four best-of-seven playoff
  rounds, NBA Cup, and the full off-season timeline.
- **Authoritative dates**: the milestone/phase events are generated into the
  `SeasonCalendar` (V2 snapshot content), not merely derived in the UI.

This intentionally replaces the frozen Milestone 2 contracts of "8 teams, 28
games per team, 112 games". Those numbers were always described as the *current*
rule, changeable in a versioned task — this is that task.

## Proven foundations already landed (green, committed)

Pass 1 and pass 3a are done as pure, tested modules that break nothing:

- **`src/domain/seasonTimeline.ts`** — anchor-rule NBA dates from the starting
  year (Tuesday opening in Oct 18–24, 174-day season, All-Star = 3rd Sunday of
  February, trade deadline = All-Star Sunday − 10 days, play-in, playoffs,
  lottery, finals, draft, and the two free-agency dates). Verified against the
  real 2025-26 calendar (`tests/domain/seasonTimeline.test.ts`).
- **`src/generation/scheduleMatrix.ts`** — `buildBalancedMeetingMatrix` yields a
  deterministic, perfectly balanced meeting set: 30 teams × 82 games = 1230
  meetings, 41 home / 41 away each, 24 opponents played 3× and 5 played 2×
  (`tests/generation/scheduleMatrix.test.ts`).

These are the two hard parts (the dates and the balanced matchups). What remains
is mechanical wiring plus coordinated test updates.

## Why the rest is one coordinated commit

`generateLeague` seed-**selects** its teams from `FICTIONAL_TEAM_IDENTITIES`, so
even *adding* identities changes which 8 teams the current league draws and
breaks the pinned fingerprints. And ~11 characterization tests assert the 8/28/
112 invariants. Therefore team-count, schedule generation, and the fixture/test
updates must land together in a single green commit — never half-migrated.

## Integration steps (the remaining work)

1. **Identities → 30.** Append the 18 new records in the appendix below to
   `src/data/fictional/teamIdentities.ts` (they are already designed with unique
   abbreviations and fictional cities/nicknames).
2. **Counts.** `src/domain/league.ts`: `LEAGUE_TEAM_COUNT = 30`. Confirm
   `LEAGUE_PLAYER_COUNT` (360) and generation scale; keep `PLAYERS_PER_TEAM = 12`.
3. **Conferences / divisions.** Add `conference` (`east` | `west`) and `division`
   (6 divisions, 5 teams each) to the `Team` domain model + V2 DTO + validation.
   Assign the 30 identities to 2 conferences × 3 divisions. Needed for standings
   and the per-conference play-in / playoffs.
4. **Schedule generation.** Replace the uniform round-robin with the balanced
   matrix: feed `buildBalancedMeetingMatrix({ teamCount: 30, gamesPerTeam: 82 })`
   through the opponent-requirement/`explicit_matrix` path in
   `src/generation/generateSchedule.ts`, then assign the 1230 meetings to
   game-days/dates across the 174-day window (no team twice per day; back-to-backs
   allowed). This date-assignment is the main remaining algorithm — build it as a
   pure, tested module first (`assignMeetingsToDates` or similar), then wire it in.
5. **Season foundation.** `createSeasonFoundation`: derive the opening date from
   `buildSeasonTimeline(startingYear).openingNight` (or validate the supplied
   date is that Tuesday), set the schedule window to the 174-day span, and
   generate the full timeline events into the `SeasonCalendar` with their real
   event kinds (`regular_season_opening`, `trade_deadline`, `all_star_break`,
   `regular_season_conclusion`, `play_in_event`, `playoffs_start`, `finals_start`,
   `draft_event`, `free_agency_event`, etc.). Update `validateSeasonFoundation`
   expected-kinds accordingly.
6. **V2 + fixtures + tests.** Update `leagueSnapshotV2.fixture.ts` and every
   characterization assertion pinning 8/28/112 to the new invariants (30 teams,
   360 players, 82 games/team, 1230 games, expanded calendar). Files to touch
   (from the current blast-radius scan): `tests/generation/generateLeague.test.ts`,
   `tests/generation/generateSchedule.test.ts`, `tests/domain/schedule.test.ts`,
   `tests/app/commands/createSeasonFoundation.test.ts`,
   `tests/app/leagueSnapshotDomainAdapter.test.ts`,
   `tests/app/teamScheduleViewModel.test.ts`,
   `tests/app/calendarViewModel*.test.ts`,
   `tests/app/enrichedCalendarViewModel.test.ts`,
   `tests/ui/schedulePages.test.tsx`, and the persistence V2 tests.
7. **Retire the derived overlay.** Once the calendar events are authoritative,
   replace the app-layer `leagueMilestones` overlay on the League Calendar with
   the real `SeasonCalendar` events (or keep the deriver only as a fallback).
8. **Postseason + Cup (pass 5).** Play-in (Tue/Wed/Fri), four best-of-seven
   rounds seeded per conference, and the NBA Cup group/knockout. New domain +
   generation + UI.

## Migration & display notes

- The retained `groupGamesByGameDay` and the M2 read-only presentation keep
  working; only the counts change.
- With 30 teams the League Calendar by-date list (already built) will show a full
  slate per night — its scroll container is ready.
- Keep the managed team prioritized everywhere; `formatTeamName` is the single
  source for names.

## Appendix — the 18 additional team identities (ready to paste)

Append these to `FICTIONAL_TEAM_IDENTITIES` (after Mossbarrow) to reach 30. They
were validated for unique abbreviations and a fictional style.

```ts
  { city: 'Northwatch',     nickname: 'Nomads',      abbreviation: 'NWN', colors: { primary: '#243b4a', secondary: '#c8763d', accent: '#eadfc9' } },
  { city: 'Oakenford',      nickname: 'Outriders',   abbreviation: 'OKO', colors: { primary: '#3c4a2b', secondary: '#c7a24a', accent: '#eef0df' } },
  { city: 'Pinehollow',     nickname: 'Pathfinders', abbreviation: 'PHP', colors: { primary: '#1f4d43', secondary: '#5fb0a0', accent: '#f0e6c8' } },
  { city: 'Quillhaven',     nickname: 'Questers',    abbreviation: 'QHQ', colors: { primary: '#4a2f5c', secondary: '#b98cd0', accent: '#efe4f3' } },
  { city: 'Ravenmoor',      nickname: 'Rooks',       abbreviation: 'RMR', colors: { primary: '#2b2f38', secondary: '#8a94a6', accent: '#e5e8ee' } },
  { city: 'Saltcliff',      nickname: 'Sentinels',   abbreviation: 'SCS', colors: { primary: '#1d4b5e', secondary: '#4fa6bd', accent: '#eaf1f2' } },
  { city: 'Thornevale',     nickname: 'Thistles',    abbreviation: 'TVT', colors: { primary: '#3f2d4d', secondary: '#9d6fb0', accent: '#e7dbef' } },
  { city: 'Umberdale',      nickname: 'Umbermarks',  abbreviation: 'UMB', colors: { primary: '#4d3a26', secondary: '#c98f4e', accent: '#f0e2cc' } },
  { city: 'Verdant Hollow', nickname: 'Vanguards',   abbreviation: 'VHV', colors: { primary: '#26492f', secondary: '#68b070', accent: '#e8f0da' } },
  { city: 'Westreach',      nickname: 'Wardens',     abbreviation: 'WRW', colors: { primary: '#334155', secondary: '#c07a3e', accent: '#e9e4d6' } },
  { city: 'Xanthe Point',   nickname: 'Xebecs',      abbreviation: 'XPX', colors: { primary: '#1f3b52', secondary: '#e0b24c', accent: '#eef2f4' } },
  { city: 'Yarrowmere',     nickname: 'Yeomen',      abbreviation: 'YMY', colors: { primary: '#4a4327', secondary: '#c6b24d', accent: '#f0ecd2' } },
  { city: 'Zephyr Cove',    nickname: 'Zealots',     abbreviation: 'ZCZ', colors: { primary: '#25506b', secondary: '#59a9c4', accent: '#e8f1f4' } },
  { city: 'Ashenford',      nickname: 'Anvils',      abbreviation: 'AFA', colors: { primary: '#3a2f2b', secondary: '#c47a55', accent: '#efe3d8' } },
  { city: 'Bramblewick',    nickname: 'Badgers',     abbreviation: 'BWB', colors: { primary: '#2f3a2b', secondary: '#a9b06a', accent: '#eef0e0' } },
  { city: 'Coldwater',      nickname: 'Cormorants',  abbreviation: 'CWC', colors: { primary: '#21414f', secondary: '#5aa0b2', accent: '#e9f0f2' } },
  { city: 'Dunmoor',        nickname: 'Drifters',    abbreviation: 'DMD', colors: { primary: '#3d3550', secondary: '#8f83b8', accent: '#e8e3f2' } },
  { city: 'Elmsworth',      nickname: 'Embers',      abbreviation: 'EWE', colors: { primary: '#5a3327', secondary: '#d07a45', accent: '#f0ddc6' } },
```

Suggested conference/division split (East / West, 3 divisions × 5):

```text
EAST  Atlantic: ARA BRB CVC DMN EFK   Central: FGK GWN HBW IHF JRW   Southeast: LBT MSW NWN OKO PHP
WEST  Northwest: QHQ RMR SCS TVT UMB  Pacific: VHV WRW XPX YMY ZCZ   Southwest: AFA BWB CWC DMD EWE
```
