# Stone Basketball GM — working agreement

Base repository rules live in **AGENTS.md**. This file adds the standing
constraints a fresh session must not violate, and points at the plan.

**The plan is `docs/ROADMAP.md`. It is the only source of truth for what is done
and what is next.** Read its Status line first. Do not restate the plan here —
two copies of a plan drift, and that is exactly how a false claim ("rotation
validation already exists") survived long enough to be planned against.

## How this project works: UI first

**The UI is a design tool, not just an output.** Alex works by seeing a screen,
getting ideas, and moving things around — the interface is where requirements
come from, so **the data model follows the UI, not the reverse.** The order is:
build the screen → learn what data it needs → make the data → make it real.

Do not treat a UI-heavy tree with little engine as work done backwards. It isn't.
Do not propose "design the data contract first" — that has stalled this project
repeatedly, because you cannot know what a box score needs by thinking about it.
The screen decides it.

This is safe here for two reasons, and it stops being safe if either breaks:

1. **Version bumps are cheap** (see saves, below), so letting the UI move the
   data shape costs nothing.
2. **Fixtures never reach the real app.** Designing against fake data is fine;
   showing fake data to a player is not — see "Never fabricate results" below.

## Standing constraints (do not violate)

### Never fabricate results
Per `docs/adr/0005-scheduled-game-vs-game-result.md`, a game result is a separate
immutable aggregate keyed to one `GameId` — never fields on `ScheduledGame`,
never inferred from `status: 'completed'`. Until a result is really simulated, the
app shows an honest absence of one.

Fixtures used to design UI are **dev/test only** and must never reach a real
game. The tripwire is the ring of tests asserting no score/winner/record appears
in the real app (`tests/ui/schedulePages.test.tsx:297`,
`tests/app/teamScheduleViewModel.test.ts:844`,
`tests/app/dashboardViewModel.test.ts:99`). **If one goes red during UI work, a
fixture has leaked.** They are rewritten in roadmap §10 when results become real
— deliberately, into their positive counterparts, never by deletion.

### 8 teams first — do NOT scale to 30 yet
`LEAGUE_TEAM_COUNT = 8` holds until the simulation is proven at 8 teams: one
game → a full season → ~5 seasons (roadmap §13).

**Do NOT wire up the shelf engines** — `generation/generateNbaSchedule.ts`,
`generation/scheduleMatrix.ts`, `generation/scheduleDatePlacement.ts`,
`domain/seasonTimeline.ts`, `domain/leagueStructure.ts`. They are built, tested,
and green, but deliberately **unwired**. Because they exist and pass, an eager
session may try to integrate them early — don't. The 30-team flip is roadmap §15
and must land as one coordinated commit.

### Determinism (domain + generation + simulation)
All domain, generation, and simulation code is pure and deterministic: an
injected seeded `RandomSource` only, **never `Math.random`**; no React / DOM /
persistence / network imports; identical seeds and versions produce deeply-equal
output. AGENTS.md states this for simulation code; it applies equally to domain
and generation code.

Changing a formula, random call order, seed derivation, or RNG algorithm requires
a version bump and new golden tests.

### Saves: one version, no migrations before 1.0
**Decided 2026-07-17. This reverses the earlier "results require a V3 snapshot
plus a V2→V3 migration" rule — do not reinstate it.**

There are zero real saves in the world: the app has never shipped
(`"private": true`; publishing is forbidden by AGENTS.md). So there is **one
current snapshot type and one version constant**. When the shape changes, bump
the number; on mismatch, refuse to load and offer "start a new league."

- **Never reset the version number.** It stays monotonic (3, 4, 5…) so records
  from older builds are refused rather than mis-parsed.
- **Do not write a migration.** Real migrations begin at roadmap §17, when saves
  start belonging to players.
- This still versions, still validates, and still never silently overwrites, so
  the AGENTS.md save rules hold.

Because bumps are cheap, **do not design the snapshot shape ahead of the code**.
Build the system, learn the real shape, then bump. Per
`docs/adr/0005-scheduled-game-vs-game-result.md`, a game result is still a
separate immutable aggregate keyed to one `GameId` — never fields on
`ScheduledGame`, and never inferred from `status: 'completed'`.

### Docs: one plan, everything else is design or history
`docs/ROADMAP.md` is the plan. `/CLAUDE.md` is the pointer. The other `docs/*.md`
are reference specs describing *intended* design, much of it unbuilt — when a
spec disagrees with the code, **the code wins and the spec is a bug**.
`docs/archive/` is dead; never cite it as current. `docs/adr/` records decisions;
supersede, never edit.

Do not add a fifth planning document. Add a roadmap section.

## Working loop (per session)
Finish one roadmap section → **sweep its deferred slots**: `grep -rn
"DEFERRED(§N)" src/` for that section's number and fill every hit (see the
Deferred-slot ledger in `docs/ROADMAP.md` — UI ships ahead of its data on
purpose, and this grep is how those slots get finished instead of forgotten) →
tick it and move the Status line in `docs/ROADMAP.md` → keep `main` green
(tests, typecheck, lint, build) → `/clear` → open the next session by pointing
it at `docs/ROADMAP.md`.

When building new UI ahead of its data: mark every empty slot with a
`DEFERRED(§N)` comment at the exact place to change (or `DEFERRED(later)` if no
roadmap section provides the data yet), and add it to the roadmap ledger. The
code tags are canonical; the ledger is the index.
