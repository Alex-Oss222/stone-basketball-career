# Stone Basketball GM — working agreement

Base repository rules live in **AGENTS.md**. This file adds the cross-session
decisions a fresh session must not violate, plus where to pick up.

## Current state

Active section: **simulation kernel — sim one game**, at 8 teams.
See `docs/SCHEDULE_FOUNDATION_ROADMAP.md` for the step sequence, exit criteria,
and the specific inputs each step consumes (for the kernel: the roster/rating
types and the V2 snapshot types).

## Durable constraints (do not violate)

### 8 teams first — do NOT scale to 30 yet
The league stays at **8 teams** (`LEAGUE_TEAM_COUNT = 8`) until the simulation is
proven at 8 teams: sim one game → sim a full season → sim ~5 seasons.

**Do NOT wire up the shelf engines yet** — `generation/generateNbaSchedule.ts`,
`generation/scheduleMatrix.ts`, `generation/scheduleDatePlacement.ts`,
`domain/seasonTimeline.ts`, `domain/leagueStructure.ts`. They are built, tested,
and green, but deliberately **unwired**. Because they exist and pass tests, an
eager session may try to integrate them early — don't. The 30-team flip is
gated on the sim and specified in `docs/MILESTONE_3_NBA_SCALE_PLAN.md`.

### Determinism (domain + generation + simulation)
All domain, generation, and simulation code is pure and deterministic: an
injected seeded `RandomSource` only, **never `Math.random`**; no React / DOM /
persistence / network imports; identical seeds and versions produce deeply-equal
output. AGENTS.md states this for simulation code; it applies equally to domain
and generation code.

### Snapshot versioning — results require V3
The V2 snapshot has **no result / score / box-score fields**. The first sim step
that persists a result must add a new `LeagueSnapshotV3` plus a V2→V3 migration —
do not push results into V2. Version and validate saves; never silently
overwrite (AGENTS.md).

**When the V3 result shape is decided** (field names for score, winner, box
score), record it in this file and in `SCHEDULE_FOUNDATION_ROADMAP.md`
immediately — every later sim step depends on those names.

## Working loop (per session)
Finish one roadmap step → update the sequence and checkboxes in
`SCHEDULE_FOUNDATION_ROADMAP.md` → update the "Current state" line above → keep
`main` green → `/clear` → open the next session by pointing it at that roadmap
file and the inputs the next step consumes.

## Pointers
- `docs/SCHEDULE_FOUNDATION_ROADMAP.md` — living status, the 5-step sim
  sequence, exit criteria, per-step inputs.
- `docs/MILESTONE_3_NBA_SCALE_PLAN.md` — the deferred 30-team expansion
  (engines, identities, flip steps).
- `AGENTS.md` — base repository rules (fictional data, IndexedDB, testing gate,
  task-handoff format).
