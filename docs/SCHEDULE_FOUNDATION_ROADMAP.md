# Schedule & Calendar — foundation status and path to simulation

Living status for the schedule/calendar area and what it takes to move on to the
next system. Supersedes the schedule notes in the Milestone 1 roadmap for
day-to-day planning.

## Decision (current)

Keep the **8-team** league for now. **Prove the simulation at 8 teams first** —
sim one game, then a full season, then several seasons — before scaling to a
full 30-team NBA league. The NBA-scale engines are already built and tested;
they wait on the shelf until the sim is proven.

## What's accomplished

### 8-team schedule & calendar (done, shipped)
- Deterministic 28-game / 4-cycle regular-season generation (circle method),
  stable game and game-day IDs, separate original/current/actual dates, typed
  constraints, full schedule validation.
- Season lifecycle (`currentDate`, `currentPhase`), team-season records, and a
  `SeasonCalendar` with authoritative opening/conclusion events.
- Milestone 2 calendar UI: month-grid League Calendar (two-pane, list ↔
  calendar swap, scrollable by-date list with full team names), Team Schedule
  command center (next-game bar, rest/B2B/road-trip/homestand badges, Today,
  stage & broadcast tabs, results filter), derived schedule-pressure overview,
  and a derived league-events timeline.
- V2 snapshot persistence with strict validation and V1→V2 migration.

### NBA-scale engines (built, tested, NOT wired — deferred)
Pure and green, ready for the eventual 30-team expansion:
- `domain/seasonTimeline.ts` — anchor-rule NBA dates (verified vs 2025-26).
- `generation/scheduleMatrix.ts` — balanced 30×82 meeting matrix (41/41).
- `generation/scheduleDatePlacement.ts` — conflict-free placement over 174 days.
- `domain/leagueStructure.ts` — 2 conferences × 3 divisions of 5.
- `generation/generateNbaSchedule.ts` — full 1230-game NBA schedule generator.
- 18 additional team identities + a conference/division split are captured in
  `MILESTONE_3_NBA_SCALE_PLAN.md`.

## Is the schedule foundation solid enough to start simulation?

Yes. Simulation needs scheduled games with two real teams, dates, home/away, and
rosters/ratings — all of which exist today for the 8-team league. Nothing on the
schedule side blocks the sim. Checklist, all satisfied:

- [x] Every team has a full, valid, dated schedule (28 games, 14/14).
- [x] Games carry stable IDs, home/away, and a status field ready to move to
      `completed`.
- [x] Season has a `currentDate` and ordered game-days to advance through.
- [x] Rosters, ratings, and tendencies exist for both teams in every game.
- [x] Persistence exists to store the season snapshot.

## What's left before / for the next step (simulation)

The next step is a **new system**, not more schedule work. To go "sim 1 game →
sim a season → sim 5 seasons" at 8 teams:

1. **Game simulation kernel** — pure, seeded, possession-based (or a simpler
   result model first), producing a final score, winner, and box score for one
   game from two rosters. No React / no `Math.random`.
2. **Results persistence (needs a snapshot version bump → V3)** — completed
   games must store score / winner / box score. V2 has no result fields, so this
   is the first real use of the **V3** decision: define `LeagueSnapshotV3` with
   game results + box scores and a V2→V3 migration.
3. **Season advancement** — advance `currentDate` game-day by game-day, sim the
   day's games, mark them `completed`, and write results. This is what turns
   "sim 1 game" into "sim a season."
4. **Standings & season stats** — fold completed results into standings and
   player/team season totals (recompute-verified).
5. **Multi-season loop** — roll a completed season into the next (new schedule,
   aged rosters as far as current systems allow) to reach "sim 5 seasons."

Once results exist, the **derived** league-events timeline and the **Results =
Final** filter light up with real data, and the Team Schedule badges gain W/L
and records.

### Minimum to call the sim foundation "solid" before expanding
- One game sims deterministically with a valid box score (invariants hold).
- A full 8-team season sims end-to-end; standings equal the completed results.
- Several seasons sim in a loop without drift or corruption.
- All of it deterministic from seed, and persisted/restored across V3 saves.

## V3 result schema — DECIDE IN STEP 2, RECORD HERE IMMEDIATELY

Once step 2 settles the `LeagueSnapshotV3` result shape, write the decided field
names here (and in `CLAUDE.md`) **before** clearing the session — every later
step (season advancement, standings, multi-season) depends on these exact names.

- Game result: `score` (home/away points), `winner`, ... — **TBD**
- Box score: player line fields (points, rebounds, assists, minutes, ...) — **TBD**
- Migration: `migrateLeagueSnapshotV2ToV3` back-fills completed=false / no
  results for existing V2 saves — **TBD**

## Deferred: 30-team NBA expansion (unblocked, engines ready)

When the sim is proven at 8 teams, the flip is mechanical because the hard parts
are done: append the 18 identities, `LEAGUE_TEAM_COUNT = 30`, add
conference/division to the Team model + snapshot, wire
`generateNbaRegularSeasonSchedule` + `buildSeasonTimeline` into
`createSeasonFoundation`, generalize the M1-locked ID/validation guards, make the
calendar events authoritative, and update the characterization tests together.
Full detail in `MILESTONE_3_NBA_SCALE_PLAN.md`.

## Sequence

```text
[done]   8-team schedule + calendar (M1 + M2)
[done]   NBA-scale engines built & tested (on the shelf)
  ->     Simulation kernel: sim 1 game (V3 results)
  ->     Season advancement: sim a full 8-team season + standings
  ->     Multi-season loop: sim ~5 seasons
  ->     Expand to 30 teams (flip: engines already ready)
  ->     Postseason (play-in + best-of-7) + NBA Cup
```
