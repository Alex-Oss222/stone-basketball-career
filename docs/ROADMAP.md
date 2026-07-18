# Stone Basketball GM — Roadmap

The single authoritative plan. If any other document disagrees with this one
about *what is done* or *what is next*, this file wins and the other file is a
bug to be fixed.

## How to use this file

- **One sequence.** Sections are ordered. Finish one, then start the next. Do not
  work ahead into a later section because its inputs happen to exist.
- **Each section has a Goal, Work, and an Exit gate.** A section is done when its
  exit gate passes — not when the code looks finished.
- **Status lives only here.** `/CLAUDE.md` points at the current section and
  restates the standing rules; it does not duplicate the plan.
- **Reference specs are not status.** They describe *intended design*, much of it
  unbuilt. When a spec disagrees with the code, the code wins.
- **Every section ends green:** `npm test`, `npm run typecheck`, `npm run lint`,
  `npm run build`. No section is done with a red gate.
- **Every section's exit gate implicitly includes the deferred-slot sweep:**
  run `grep -rn "DEFERRED(§N)" src/` for the section's number and fill every
  hit before calling the section done. See "Deferred-slot ledger" below —
  this is how UI built ahead of its data gets finished instead of forgotten.

## Document map

| File | Kind | Answers |
| --- | --- | --- |
| `ROADMAP.md` (this file) | **plan** | What is done, what is next, when a section is finished |
| `/CLAUDE.md` | **pointer** | Standing rules and which section is current |
| `GAME_DESIGN.md` | reference | What the game is and its acceptance criteria |
| `DATA_MODEL.md` | reference | Entity shapes and invariants (incl. unbuilt ones) |
| `SEASON_AND_SCHEDULING.md` | reference | Season / calendar / schedule architecture (built) |
| `SIMULATION_MODEL.md` | reference | The intended sim contract and possession model (**unbuilt** — §9, §14) |
| `NBA_SCALE_PLAN.md` | reference | 30-team step detail and the 18 identities (deferred — §15) |
| `adr/` | decisions | Why a boundary is where it is; supersede, never edit |
| `archive/` | dead | Superseded plans, kept for history. **Never cite as current.** |

Only the plan and the pointer carry status. Everything else is design or history.

## How this project works: UI first

**The UI is a design tool, not just an output.** Seeing a screen generates ideas
and requirements that no amount of specification produces. So the order here is
deliberately: *build the screen → learn what data it needs → make the data → make
it real.* The data model follows the interface, not the reverse.

This is why §6 comes before the simulation. The result contract has blocked this
project across several sessions precisely because it was treated as something to
decide by thinking. It is not. **The box score screen decides it:** whatever
fields the screen shows are the contract.

Two things make this safe rather than reckless:

1. **Version bumps are cheap** (§7), so letting the UI move the data shape costs
   nothing. This only works *because* of the no-migrations decision.
2. **Fixtures never reach the real app.** Designing against fake data is fine;
   showing fake data to a player is not. See the guardrails in §6.

## Standing rules (do not violate)

- **Fictional data only.** No real teams, players, or logos.
- **Local only.** No backend, accounts, analytics, telemetry, or runtime network
  requirements. IndexedDB for persistence.
- **Determinism.** All domain, generation, and simulation code is pure: an
  injected seeded `RandomSource` only, never `Math.random`; no React, DOM,
  persistence, or network imports. Identical seeds and versions produce
  deeply-equal output.
- **Never fabricate results.** Per
  [ADR 0005](adr/0005-scheduled-game-vs-game-result.md), a game result is a
  separate immutable aggregate keyed to one `GameId` — never fields on
  `ScheduledGame`, never inferred from `status: 'completed'`. Until a result is
  really simulated, the app shows an honest absence.
- **Versioned formulas.** Changing a formula, random call order, seed derivation,
  or RNG algorithm requires a version bump and new golden tests.
- **Eight teams until the sim is proven.** `LEAGUE_TEAM_COUNT = 8` holds until
  §13 passes. The NBA-scale engines are built and green but deliberately
  **unwired** — see §15. Do not wire them early.

## Status

**Current section: §8 rotation half + §8A coach profiles (§8B is complete).**

Sections 1–7 are shipped. §7 closed 2026-07-17: the save format is collapsed to
one monotonic version (`LEAGUE_SNAPSHOT_VERSION = 3`); the V1 DTO and the whole
migration module are deleted; an old record now surfaces a "start a new league"
version-mismatch screen instead of a migration.

**Re-sequenced 2026-07-17:** §8B (detailed ratings) runs **before** the §8
rotation half, §8A, and §9. The rotation ability-selector and every §9 event
formula must read the detailed sub-ratings, so the ratings model is built once,
up front. §8's rule-pack half (`src/domain/leagueRules.ts`) is done; its rotation
half — `RotationPlanV1`, the validator, deterministic CPU generation, and the
functional Adjust Rotation editor — now follows §8B and consumes §8B's versioned
ability selector. **R1 is done** — the taxonomy is frozen in ADR 0008 (Accepted):
18 categories, 67 sub-ratings. **R2 is done (2026-07-18)** —
`src/domain/detailedRatings.ts`, the pure detailed-rating domain, taxonomy
pinned by an independent test manifest. **R3 is done (2026-07-18)** —
`src/generation/generateDetailedRatings.ts`, deterministic generation under the
labeled three-stream hierarchy, five 67-value golden vectors + distribution
lock; adversarial verification independently recomputed every golden value
from the ADR with zero deviations. **R4 is done (2026-07-18)** — the stored
model IS the detailed model: `generateLeague` produces 67-sub-rating players,
`LEAGUE_SNAPSHOT_VERSION` bumped 3 → 4 (clean break, no migration, old records
offer a new league), league stores the schema + category-definition versions,
validation checks all 67 keys, and the view models derive 18 category rows —
the Skills accordion now drops down real sub-ratings. **R5 + R6 are done
(2026-07-18)** — memoized view models; the versioned position-weighted Overall
(`playerDerivations.ts`, OVERALL_MODEL_VERSION 1) replaced the transparent
mean everywhere (quick view, player page, rail, roster, depth chart, team
averages); Position Profiles Off/Def/Ovr letters and quick-view numeric fit
are real; `grep -rn "DEFERRED(§8B)" src/` is empty. **R7 + R8 are done
(2026-07-18)** — `rotationAbility.ts` (ROTATION_ABILITY_VERSION 1, the one
CPU-planning evaluation) and `simulationReads.ts`
(SIM_RATING_READ_VERSION 1): sixteen frozen event selectors covering exactly
the 61 possession-relevant sub-ratings, Durability/Intangibles excluded,
documented in SIMULATION_MODEL.md with a code↔doc agreement test and an
architecture guard on `src/simulation/`. **§8B is COMPLETE.** Next: the §8
rotation domain + §8A profiles (Path-to-§9 milestone 6), then the functional
editor (milestone 7), then §9.

**UI-first head start (2026-07-17):** the §8B R6 screens already exist with
their results-era slots deferred — the rebuilt roster (tabs: Players / Depth &
Roles / Contracts / Compare), the hover-only quick view (a 5-second dwell pins
it and unlocks its Health / Development tabs), and the full player page. The
whole **Team section** is also imposed from Alex's references (2026-07-17):
**Coach's Chair** (the command-center rework of Team Overview, with the roomy
real-schedule Schedule Pressure strip), and UI-first shells for **Rotation &
Gameplan** (the §8 editor's screen — board + 48-minute map, non-functional
until §8), **Medical Department**, and **Coaching & Development**. Health is
always plain words, never invented risk scores. See the deferred-slot ledger.
(2026-07-18: the §8B data landed underneath these screens — ratings, grades,
overalls, and fits are now real; the remaining dashes are §8/§11/later slots.)

**Path to §9 (sequenced 2026-07-18).** One milestone ≈ one session: finish it
→ sweep the tags it clears → gates green → `/clear`. The specs live in the
sections named; this list is only the order. (An external "engine buildout"
runbook was reviewed 2026-07-18 and its surviving content folded in here — it
is not a second plan. Its migration-based approach was rejected outright: the
§7 rule stands, version breaks offer a new league, no migrations before §17.)

1. **§8B R2 ✅ done 2026-07-18** — the pure detailed-rating domain
   (`src/domain/detailedRatings.ts`): 18/67 registry, strict parser,
   selectors; taxonomy pinned twice (module + independent test manifest);
   adversarially verified against ADR 0008 with zero mismatches.
2. **§8B R3 ✅ done 2026-07-18** — deterministic generation
   (`src/generation/generateDetailedRatings.ts`) under the three labeled
   streams; five 67-value golden vectors + distribution lock; verification
   independently recomputed every golden value from the ADR text.
3. **§8B R4 ✅ done 2026-07-18** — stored model swapped to detailed;
   `LEAGUE_SNAPSHOT_VERSION` 3 → 4, clean break, no migration; legacy macro
   model deleted; restore parses exactly and never regenerates.
4. **§8B R5 + R6 ✅ done 2026-07-18** — memoized view models; versioned
   position-weighted Overall (`playerDerivations.ts`, model v1) live in
   quick view / player page / rail / roster / depth chart / team averages;
   Position Profiles Off/Def/Ovr letters + quick-view numeric fit real;
   Skills accordion shows real sub-ratings; `DEFERRED(§8B)` sweep empty.
5. **§8B R7 + R8 ✅ done 2026-07-18** — `rotationAbility.ts` (v1) is the one
   CPU-planning evaluation; `simulationReads.ts` (v1) freezes sixteen event
   selectors covering exactly the 61 possession-relevant sub-ratings
   (Durability/Intangibles excluded), with a SIMULATION_MODEL.md ↔ code
   agreement test and an architecture guard on `src/simulation/`. **§8B
   complete.**
6. **§8 + §8A domain — NEXT.** `RotationPlanV1` exactly as specced above (no
   situational lineups, no field-level ownership — `source` is the
   ownership), the typed-issue validator, the eight §8A profiles (contract
   as written), deterministic CPU generation consuming R7 + the planning
   halves. Golden plans for all eight profiles; plans persist behind another
   monotonic bump (4 → 5). **Resolved 2026-07-18:** the board's "Close"
   toggle is removed from the V1 plan — closing behavior is §8A *runtime*
   (§9); the column becomes a read-only later slot.
7. **§8 editor functional** — the built Rotation & Gameplan board becomes
   the real editor: edit → typed issues → save blocked until valid →
   persists; user-edited plans survive regeneration; roster changes repair
   deterministically. Sweep `DEFERRED(§8)`; tick §8 + §8A.
8. **§9 kernel** — record the tendency-normalization and game-seed decisions
   in SIMULATION_MODEL.md, then `simulateGame`: walking-skeleton basketball
   model behind the frozen §6 contract, live rotation at dead balls,
   box-score invariants from the first slice, ties resolved by the rules
   pack's real overtime (saved plans stay 240), golden games, and the §6
   screens render a simulated result with zero shape changes. Tick §9 —
   simming exists. §10 then makes it playable (commit, advance, tripwires
   rewritten positive).

Open §6 polish, deliberately deferred: Alex dislikes how the empty Standings
card sits in the Home layout — revisit when its data lands (tagged on the
card's `DEFERRED(§11)` note).

---

# Part I — Shipped

These are done. They are recorded here for sequence only; do not re-plan them.

### 1. Strict TypeScript and test foundation ✅

Strict mode across app, tooling, and tests. Vitest as a dev-only dependency.
`typecheck` script. Branded `StableId<Kind>` types with runtime guards. Seeded
RNG: `xoshiro128**` (`RANDOM_SOURCE_VERSION = 'xoshiro128ss-v1'`) behind the
injected `RandomSource` interface, with labeled seed derivation
(`deriveSeed(rootSeed, label)`, `SEED_DERIVATION_VERSION = 'seed-derivation-v1'`)
so every independent decision draws its own stream.

### 2. Domain model and deterministic league generation ✅

8 teams × 12 players = 96 players, generated deterministically from a root seed.
16 rating keys (0–100 integers, exact set enforced), 6 tendencies, positions,
ages, jersey numbers. Every stored rating draws from its own labeled stream.
League validation over identity, ownership, counts, ranges, and uniqueness.

**Not built here, despite what the old roadmap claimed:** rotations. There is no
`RotationPlan`, no rotation generation, and no rotation validator anywhere in the
tree. That work is §8.

### 3. Season, schedule, and calendar ✅

Timezone-free `LocalDate` / `YearMonth`. Seeded circle-method regular season: 28
games per team, 112 games, 28 ordered game days, 14 home / 14 away. Stable game
and game-day IDs. Separate original / current / actual dates. Typed hard/soft
constraints and whole-report diagnostics. `Season` lifecycle, `SeasonCalendar`
(20 event kinds; only opening and conclusion are currently generated), and
`TeamSeason` records. `createSeasonFoundation` self-checks by regenerating the
schedule and comparing structurally.

### 4. Calendar and schedule UI ✅

Month-grid League Calendar (two-pane, list ↔ calendar swap, by-date list). Team
Schedule command center: next-game bar, rest / back-to-back / road-trip /
homestand badges, Today, stage and broadcast tabs, All/Upcoming/Final filter.
Derived schedule-pressure overview and a derived league-events timeline. All of
it is a pure projection of the snapshot; none of it invents results.

### 5. Local persistence bridge ✅

`LeagueSnapshotV1` (league only) and `LeagueSnapshotV2` (adds season, calendar,
team-seasons, schedule, creation metadata). Strict *closed* parsers — every DTO
rejects unknown keys. Cross-object consistency validation. Revision-guarded
writes with stale-write detection. IndexedDB adapter. Confirmed corrupt-storage
purge.

This is a bridge, not the final save system. It has no autosave history, no named
manual saves, and no export/import — that is §17.

---

# Part II — Simulation

The goal of Part II is the whole loop: design the screens → one game → a full
season → several seasons, all deterministic and persisted. The basketball model
stays simple throughout; depth is §14.

### 6. Results UI — discover the contract ✅

**Goal.** Build the result, box score, and dashboard screens against hand-written
fixtures, and move things around until they feel right. **The fields those
screens end up consuming are the result contract** that §9 must produce.

**Why this is first.** See "How this project works" above. The contract cannot be
decided in the abstract — it has stalled repeatedly when tried. The screen
decides it. And because §7 makes bumps cheap, letting the UI drive the shape is
now nearly free.

**Nothing here is simulated and nothing is persisted.** This section touches no
snapshot and needs no RNG.

**Work.**
- Draft the result types in `src/domain/gameResult.ts`: score, winner, period
  totals, team and player box-score lines. Domain — not `src/simulation/` — so
  the UI can consume them without importing the sim, and the sim produces them
  without owning them. Treat these as **disposable drafts**; the screens are in
  charge.
- Hand-write fixtures (`tests/fixtures/` or a dev module). See the guardrails.
- Build components as **pure functions of their props**:
  - game result view — score, winner, period totals;
  - player box-score table;
  - home dashboard — result tiles, recent/next, and the buttons and nav that tie
    them together.
- Add a **dev-only preview route** rendering those components against fixtures,
  guarded by `import.meta.env.DEV` so it is tree-shaken out of the production
  build. No new dependency.
- Iterate. Move things, add and drop fields, change the layout. The types follow
  the screens.

**Guardrails.**
- **Fixtures must obey the invariants** — team points equal the sum of player
  points, minutes total 240, makes never exceed attempts. Designing against
  producible data means the screen cannot quietly ask for something the sim can
  never make.
- **Fixtures are dev/test only.** No fixture may reach a real game. The real
  Calendar and Team Schedule keep showing an honest absence of results.
- **The absence tests must stay green.**
  `tests/ui/schedulePages.test.tsx:297`,
  `tests/app/teamScheduleViewModel.test.ts:844`, and
  `tests/app/dashboardViewModel.test.ts:99` assert that no score, winner, or
  record appears in the real app. Through this whole section they should keep
  passing — **if one goes red, a fixture has leaked into the real app.** They get
  rewritten in §10, when results become real, and not before.

**Exit gate.**
- The three screens look right to you. This is a **judgement gate, not a metric** —
  it passes when you are happy with them.
- `GameResult` and the box-score types are frozen, and recorded in
  `SIMULATION_MODEL.md` as the target §9 implements against.
- Every new component is a pure function of its props — no simulation, no
  persistence, no RNG.
- The dev preview route is absent from the production build.
- The absence tests still pass.
- All four gates green.

**Accomplished so far (first build, 2026-07-17).** The screens exist and are
green — what remains for the gate is the iterate-and-freeze loop: look at them,
move things, then freeze the types.

- **Draft contract**: `src/domain/gameResult.ts` — `GameResult`,
  `PlayerBoxScoreLine` (14 counting stats + started/DNP reason, integer
  seconds), `TeamPeriodScoring`, and `collectGameResultIssues` /
  `assertValidGameResult` enforcing every structural invariant (points
  arithmetic, 240-minute + overtime reconciliation, makes ≤ attempts, exactly
  five starters, plus/minus = 5 × margin, one winner). These validators are the
  seed of §9's finalization checks.
- **Fixture**: `src/dev/exhibitionGameResult.ts` — Emberlyn Forgekeepers 118,
  Duskmere Nightjars 112 (OT), 12 players per side incl. DNPs, every number
  reconciling; proven against the validator in `tests/domain/gameResult.test.ts`.
- **Home** (`src/ui/homePage.tsx` + `src/app/homeViewModel.ts`), iterated
  twice in-session and settled on: **the mockup's card grid without the
  duplicate Home subtab row** (Home's nav pages are just Home + planned
  **My**, the future user-customized dashboard; the sidebar owns
  Team/League/Front Office). Command bar shows identity once (the page h1 is
  the team name) with season · phase · date, avg rating, roster count, and
  disabled Continue / Sim to Next Event. Cards: **Needs Attention** (real
  caught-up state naming the next event — no injury/trade systems exist — with
  live Review Offers / View Free Agents entry points), **Roster Health** (real
  count + positions, health deferred, live Adjust Rotation), **Front Office**
  (deferred, live View Finances), **Next Game** (real matchup + real
  avg-rating comparison of both rosters; disabled **Watch Game** / Sim Game —
  watching needs the event log), **Recent Results** (honest none; hosts the
  dev preview), **Upcoming Games** (≤5 real compact rows, live View Full
  Schedule), **Standings** (one card, two sections: Division and Conference,
  both deferred — divisions/conferences arrive with §15), **Season Pulse /
  Important Headlines / Team Stats** (deferred). Card buttons navigate to
  their real sidebar destinations — a planned page honestly states its
  requirement. Three-way honesty split throughout; nothing fabricates a value.
- **Post-game workspace** (`src/ui/gameResultPage.tsx` +
  `src/app/gameResultViewModel.ts`): score header, quarter/OT line; tabs are
  **Overview | Team Stats | Play-by-Play | Charts**. Overview carries top
  performers **and the full classic-order box score** (Both Teams | EFK | DMN
  toggle; starters/bench/DNP, totals + shooting rows) — there is no separate
  Box Score tab. Team Stats carries the comparison table **plus the Four
  Factors**. Key moments fold into the Play-by-Play coming-later tab; Lineups
  was removed (the box score already shows who played). Records/venue,
  summary, and both deferred tabs need the sim's event log or standings.
  Percentages are null-safe (zero attempts render "—", never NaN).
- **Dev preview**: DEV-only lazy route from the Recent Results card
  ("Preview the post-game screen"); verified absent from the production bundle
  along with the fixture and workspace code.
- Gate: 1,162 tests green across 57 files; typecheck, lint, build clean. The
  three absence tests pass untouched, and the fixture/workspace remain
  verified absent from the production bundle.
- **Known deferred polish**: the global app header still shows the team name
  in its chrome and still carries the derived "View Schedule" action — the
  spec wants Continue as the one primary action there, which lands when
  Continue becomes real (§10). Card-level phase-awareness (Next Event becoming
  draft/free-agency/playoffs) needs those phases to exist.

### 7. Collapse the save format to one version ✅

**Goal.** Stop paying a migration tax for saves that do not exist, so that every
later section can change the snapshot shape freely.

**Why.** The app has never shipped (`"private": true`; publishing is forbidden),
so there are zero real saves in the world. Yet V1 exists only to be migrated:
nothing in `src/app` or `src/ui` imports it — its only readers are its own
migration and its own tests. The V1→V2 migration cannot even run alone, because
V1 has no season and the caller must hand it synthetic season inputs. Meanwhile
the storage version axis is *enumerated, not parameterized*: two fixed slots
(`{ v1, v2 }`), a mutation union that hardcodes `write-v2`, and a hardcoded
`restore()` precedence ladder. Left alone, every future shape change costs a new
slot, a new rung, a new migration, and a new closed key list.

**Decision (approved 2026-07-17).** One current snapshot, no migrations before
1.0. On version mismatch, refuse to load and offer "start a new league." This
still versions, still validates, and still never silently overwrites — so the
repository rules hold. Real migrations begin at §17, when saves start mattering.

**Work.**
- Rename `LeagueSnapshotV2` → `LeagueSnapshot`; `SNAPSHOT_VERSION = 3`.
  **Keep the number monotonic — never reset to 1** — so pre-existing browser
  records written as 1 or 2 are correctly refused rather than mis-parsed.
- Delete `src/persistence/leagueSnapshot.ts` (V1 DTO + parser, 484 lines).
- Delete `src/persistence/migrations/migrateLeagueSnapshotV1ToV2.ts` (305 lines)
  and the `migrateV1ToV2` orchestration + stage list in
  `leagueSnapshotRepository.ts`.
- Delete `tests/persistence/leagueSnapshot.test.ts` and
  `tests/persistence/migrateLeagueSnapshotV1ToV2.test.ts`; drop the V1 import in
  `tests/app/commands/createNewLeagueSnapshotV2.test.ts`.
- Collapse `VersionedLeagueSnapshotStorageState { v1, v2 }` to a single slot and
  drop the hardcoded `write-v2` mutation kind.
- Reduce `restore()` from a precedence ladder to three outcomes: parsed |
  version mismatch | empty. Add the mismatch variant to
  `LeagueSnapshotRestorationResult` and surface it in the UI as a clear "this
  league came from an older build — start a new league" path.
- Keep untouched: the strict closed parsers, cross-object validation,
  revision-guarded writes, and the corrupt-storage purge.

**Exit gate.**
- Exactly one snapshot type, one version constant, one storage slot.
- Restoring a record whose version ≠ `SNAPSHOT_VERSION` returns the mismatch
  result, reports it clearly, and never mutates or overwrites the stored record.
- No migration code remains in the tree.
- Roughly 1,570 lines of V1/migration code and tests are gone.
- All four gates green.

**Accomplished (2026-07-17).** Done as planned, in the shape the code revealed.
`leagueSnapshotV2.ts` became the sole `leagueSnapshot.ts`
(`LEAGUE_SNAPSHOT_VERSION = 3`, monotonic), absorbing the V1 closed parsers it
used to delegate to; the V1 DTO, the `migrations/` directory, and their tests
are deleted. `restore()` now returns `empty | restored | version-mismatch |
recovery-required`, and the mismatch and recovery paths never touch stored data.
The IndexedDB adapter keeps a single `current` slot but still *reads* the legacy
`current-v2` key (active wins; legacy surfaces only when `current` is empty), so
an old save is refused as a version-mismatch rather than mistaken for empty.
`App.tsx` / `setupPages.tsx` replaced the migration flow with a
`VersionMismatchScreen` whose only destructive action is a user-confirmed,
version-guarded `clear()` → new league. Net −1,949 lines. Verified beyond the
gate by bundle-purity checks and a five-dimension adversarial review
(save-integrity, restore contract, parser preservation, version consistency,
absence-test tripwires — zero findings). Not committed yet.

### 8. League rules and rotation plans

**Goal.** Build the two sim inputs that do not exist, on one organizing
principle (Alex's spec, 2026-07-17):

> **`LeagueRulesV1` determines what is legal. `RotationPlan` describes what
> the coach intends. The live rotation engine (§9/§14) decides what actually
> happens.** Never combine these three responsibilities in one object, and
> never put CPU strategy fields inside the rules.

**Rules half done (2026-07-17, by request — no coupling to §7):**
`src/domain/leagueRules.ts` ships the nested `LeagueRulesV1` contract and the
frozen `MILESTONE_1_LEAGUE_RULES` pack: 4×720s quarters; 300s unlimited
overtime with the 20-OT termination guard; 24/14/8-second clocks; 6 personal
fouls with unlimited re-entry; team-foul penalty on the **5th regulation** /
**4th overtime** team foul plus the **final-2:00 single-foul rule**; offensive
fouls never count toward the bonus; shooting-foul free throws 2 (missed two) /
3 (missed three) / 1 (and-one) and 2 in the penalty; dead-ball-only
substitutions. Regulation player-minutes are **derived**
(`deriveRegulationTeamSeconds` = 4 × 720 × 5 = 14,400s = 240 min), never a
stored magic number; tests prove agreement with the frozen result contract.

**Remaining: the rotation half.**

- `RotationPlanV1` (concrete contract, decided 2026-07-18): `version: 1`,
  `teamId`, exactly five `starters`, `minuteTargetsSeconds:
  Readonly<Record<PlayerId, number>>` (whole minutes at the editor edge,
  integer seconds in domain state), `benchOrder`, `source: 'cpu-generated' |
  'user-edited'`, plus the §8A `generation?`/`autoRepair?` metadata. No
  wall-clock timestamps in deterministic data. **V1 has no scripted
  substitution timeline, situational lineups, closing-lineup field, or
  field-level ownership — `source` is the ownership boundary.**
- **Resolved (2026-07-18): the board's editable "Close" toggle is removed
  from V1.** Closing behavior belongs to the coach *runtime* profile and §9;
  the plan contract does not grow to satisfy a visual shell. The board's
  Close column becomes a read-only later slot.
- `validateRotationPlan` returning **structured issue codes** (starter count,
  duplicate starter, ineligible player, minute total, per-player minutes) so
  the editor can show exact errors. A valid regulation plan: five unique
  eligible starters, all targeted players on the team, minutes 0–48 whole,
  ≥5 players and all starters with positive minutes, total exactly the
  derived 240, bench order duplicate-free. Position balance is a **soft CPU
  preference, not a validator rule** — the rules require five legal players,
  not one per named position.
- Deterministic CPU generation per team from its own labeled stream
  (`deriveSeed(leagueSeed, 'rotation/v1/<teamId>')`): filter eligible →
  deterministic rotation score → sort with playerId tie-break → five starters
  with soft balance → 8–10-player rotation → minute template (default
  nine-man 34/33/32/31/28/24/22/20/16 = 240) adjusted by quality and
  endurance → normalize to exactly 240 → validate → save only if valid. Team
  processing order must not change any team's output.
- **User-edited plans are never overwritten** by CPU regeneration.
- **Roster-change reconciliation**: when a player becomes unavailable, remove
  from starters, zero their minutes, preserve unaffected targets, fill
  starters deterministically, redistribute and normalize to 240, re-validate,
  and mark the plan as auto-repaired.
- **Adjust Rotation becomes a functional editor** (this clears
  `DEFERRED(§8)`; a visual mockup does not): 240/240 header, five starter
  slots (role labels are suggestions), player table with starter toggle and
  minute steppers, Auto Rotation / Reset / Save / Cancel. Save validates,
  blocks invalid plans with the exact issues, persists, and the next
  simulation consumes the updated plan.

**Runtime behavior — §9/§14, not §8:** the engine compiles the plan at legal
dead-ball opportunities (plans are workload targets, not scripted
timestamps); quarter breaks are guaranteed checkpoints; foul-outs, injuries,
and ejections override immediately; overtime allocates its extra 25
player-minutes at runtime — **the saved plan stays 240**; foul-trouble
sitting policy is coaching AI, not a league rule.

**Deliberately out of scope** (implement coherently later or not at all —
never half-implement): challenges, replay, flagrant/clear-path/take fouls,
technicals, defensive three seconds, timeouts.

**Exit gate.**
- Identical league seed + roster produce deeply-equal plans; save/load and
  team processing order change nothing; streams are per-team. **Amended by §8A:**
  the full deterministic input also includes coach profile ID + version and the
  generator version — see §8A's combined exit gate, which supersedes this bullet.
- All eight default rotations validate; every plan totals exactly the derived
  240 with five unique eligible starters.
- Invalid plans cannot be saved; errors are specific, typed issues.
- User edits persist and survive CPU regeneration; roster changes repair
  plans deterministically.
- The Adjust Rotation editor works end-to-end. (**That the simulator consumes
  the saved plan is §9's integration gate, not §8's** — no simulator exists
  at §8; corrected 2026-07-18.)
- Plans and coach assignments persist behind the next monotonic snapshot bump
  (4 → 5), no migration.
- `grep -rn "DEFERRED(§8)" src/` returns nothing. All four gates green.

### 8A. Coach rotation profiles

**Goal.** Add deterministic coaching archetypes that shape CPU rotation
generation now and live substitutions later, **without** putting strategy in
`LeagueRulesV1` or turning `RotationPlanV1` into a substitution script. This
extends the §8 organizing principle to four responsibilities (Alex's spec,
2026-07-17):

> `LeagueRulesV1` — what is legal.
> `RotationPlanV1` — the intended regulation workload (starters, minutes, bench).
> `CoachRotationProfileV1` — how a coach *generates and interprets* that workload.
> Live rotation engine (§9/§14) — what actually happens at each legal sub.

The profile is a **policy input**: its `planning` half feeds §8 generation and
repair; its `runtime` half is consumed only by §9/§14. Legality and the
rotation-plan validator never depend on coaching style.

**Fictional-only.** Persisted data uses generic archetype IDs only. The
real-coach inspirations in the pack table below are design documentation —
never stored, never in game logic — so the labels can't rot as real coaches
change teams or roles.

**Contract** (planning consumed by §8; runtime is a validated data husk until
§9/§14). Every `RotationTendency` is a whole number 0–100 — sim tuning
constants, not measurements of real people:

```ts
type CoachRotationProfileId =
  | 'adaptive-matchup' | 'balanced-system' | 'workhorse-core'
  | 'development-lab'  | 'meritocratic-flex' | 'star-stagger'
  | 'deep-collective'  | 'veteran-hierarchy'

interface CoachRotationProfileV1 {
  version: 1
  profileId: CoachRotationProfileId
  planning: {                 // §8 CPU generation + deterministic repair
    targetRotationSize: 8 | 9 | 10
    // length = targetRotationSize, sums to exactly 10_000; SHARES, not stored
    // minutes — applied to deriveRegulationTeamSeconds(rules)
    workloadSharesBps: readonly number[]
    selectionWeights: { currentAbility; endurance; development; experience }
    incumbentStarterBias; softRoleBalance; hierarchyRigidity; exploration
  }
  runtime: {                  // §9/§14 only
    planAdherence; longStintPreference; fatigueConservatism; foulTroubleConservatism
    matchupResponsiveness; hotHandResponsiveness; primaryCreatorStagger
    unitContinuity; closingLineupFlexibility; garbageTimeBenchUse; playoffCompression
  }
}
interface CoachRotationAssignmentV1 {
  version: 1; coachId: string; profileId: CoachRotationProfileId
}
```

The profile belongs to the **coach**, not the franchise — it travels when a
coach changes teams. If Milestone 1 has no coach entities yet, a team-level
assignment is an acceptable temporary adapter, but persist around a stable
`coachId`.

**`RotationPlanV1` gains generation/repair metadata** (policy identity, not the
policy itself; no timestamps in deterministic data):

```ts
generation?: { generatorVersion: 'rotation-generator-v1'; coachProfileId; coachProfileVersion: 1 }
autoRepair?:  { repairVersion: 'rotation-repair-v1';
                reason: 'player-unavailable' | 'player-removed' | 'starter-ineligible' }
```

**The eight-profile pack.** The baseline curves are documentation/fixtures; the
implementation stores equivalent basis-point shares and applies them to the
derived regulation total. Every curve below totals 240 under the Milestone 1
pack — a documentation convenience, not the allocation mechanism:

| Profile | Design inspiration (doc only) | Players | Baseline workload | Character |
|---|---|--:|---|---|
| `adaptive-matchup`  | Spoelstra-like    |  9 | 34/33/31/30/28/24/22/20/18      | matchup-flexible, balanced, flexible closers |
| `balanced-system`   | Stevens-era       | 10 | 32/31/30/29/27/23/21/18/16/13   | broad trust, stable roles (safest default) |
| `workhorse-core`    | Thibodeau-like    |  8 | 38/37/36/35/32/24/20/18         | short rotation, heavy starters, rigid |
| `development-lab`   | Hardy-like        | 10 | 31/30/29/28/27/24/21/19/17/14   | young-player minutes, experimentation |
| `meritocratic-flex` | Mazzulla-like     | 10 | 33/32/31/30/28/23/20/17/14/12   | performance-driven roles, low rigidity |
| `star-stagger`      | Redick-like       |  9 | 36/35/33/31/28/23/21/18/15      | heavy creators, strong staggering |
| `deep-collective`   | generic depth     | 10 | 30/29/28/27/26/24/23/20/18/15   | egalitarian, frequent subs, fatigue-protective |
| `veteran-hierarchy` | generic veteran   |  9 | 35/34/32/31/28/24/21/19/16      | experience-first, stable bench, predictable closers |

Example stored shares (`workhorse-core`):
`[1583, 1542, 1500, 1458, 1333, 1000, 834, 750]` (Σ = 10,000 bps), applied to
whatever regulation team-seconds the active rules derive.

**Deterministic assignment.** For the default eight-team league, assign one of
each preset so coaching differences are visible instead of six near-identical
coaches: sort stable coach IDs, then
`deterministicShuffle(sortedProfileIds, deriveSeed(leagueSeed, 'coach-profile/v1/default-eight'))`.
Save the assignments (loading never silently reassigns); never depend on object
iteration order; never reuse team-generation RNG; a coach keeps their profile
across team changes. Adding coaches/teams later needs a *versioned* assignment
policy, not a silent remap. Beyond eight teams (§15) duplicate archetypes are
fine via a per-coach stream `deriveSeed(leagueSeed, 'coach-profile/v1/<coachId>')`.

**How planning shapes generation** (extends §8's sequence). Resolve coach +
profile → filter eligible → score
`currentAbility·w + endurance·w + development·w + experience·w + incumbentBonus + boundedExploration`
→ sort with playerId tie-break → pick `targetRotationSize` → five starters with
soft role balance → apply the workload-share curve → adjust for quality /
endurance / development → normalize to the derived regulation minutes → bench
order → validate → save only if valid. Team processing order changes no team's
output.
- `developmentValue` is the value of *investing minutes* in a player, not raw
  age — a 21-year-old with no upside must not auto-outrank a productive veteran.
- **Exploration is per-player-seeded** (`deriveSeed(teamRotationSeed, 'player/<id>')`)
  so adding/removing one player doesn't shift everyone's draw. Tightly bounded:
  may reorder comparable players and the last 1–2 rotation slots; may never make
  an ineligible player eligible or lift a clearly inferior player over a star
  (≈ one tier at most).
- **Whole-minute normalization** is a deterministic capped largest-remainder
  allocator in 60-second units (`deriveRegulationTeamSeconds(rules) / 60` = 240):
  floor each share → cap each player at 48 → redistribute overflow → hand out the
  remainder by descending fractional part → playerId final tie-break → convert to
  integer seconds. Never float-accumulate and patch the last player.
- `softRoleBalance` may reward ballhandling / size / shooting / defensive
  coverage, but **must never make `validateRotationPlan` reject an otherwise-legal
  five** — position balance is a soft CPU preference, not a validator rule.

**Roster-change reconciliation** honors the profile without erasing intent:
- *CPU plan* — remove the player, zero their minutes, let the profile pick a
  replacement, redistribute by shares + headroom, rebuild bench order, normalize
  to the derived total, validate, mark auto-repaired.
- *User-edited plan* (conservative) — preserve every unaffected target, fill a
  starter vacancy from the saved bench order first (profile only as a final
  tie-break), redistribute only the orphaned minutes, never a full regeneration,
  keep `source: 'user-edited'`, mark auto-repaired. A coach change may regenerate
  a CPU plan but must **preserve a user-edited plan** until the user chooses Auto
  Rotation.

**Runtime (§9/§14, data-only in §8).** At each legal dead ball: eliminate illegal
candidates first, then score legal lineups by
`planAdherence·deficit + fatigueConservatism·relief + foulTroubleConservatism·risk + matchupResponsiveness + hotHandResponsiveness + primaryCreatorStagger·coverage + unitContinuity + closingLineupFlexibility`.
Hard requirements always win (five legal players; no fouled-out / injured /
ejected; legal opportunity only; OT's extra ~25 player-minutes allocated at
runtime while the saved plan stays 240). Preferences choose among legal options;
they never legalize one. **Adherence floor:** user-edited plans use
`max(planAdherence, 85)` so coach personality can't make the Adjust Rotation
feature feel fake — forced injuries / foul-outs / ejections still override.

**Adjust Rotation editor** gains a **read-only** coach-style panel (archetype +
one-line character). Auto Rotation previews using the current coach's *planning*
profile; Reset restores the last *persisted* plan (not a fresh CPU plan); Save
validates → persists → marks `source: 'user-edited'` (even when it began from
Auto Rotation — that explicit save is what protects the plan from future
background CPU regeneration); Cancel discards. Coach style is changed on the
coach-management / hiring screen, never in the rotation editor.

**Separate coach-profile validator** with structured issues — `UNKNOWN_PROFILE_ID`,
`ROTATION_SIZE`, `WORKLOAD_SHARE_COUNT`, `WORKLOAD_SHARE_TOTAL` (= 10,000),
`WORKLOAD_SHARE_VALUE`, `TENDENCY_RANGE`: known ID; size ∈ {8,9,10}; share count =
size; each share a positive whole number; shares sum to exactly 10,000; every
tendency a whole 0–100; no team/player IDs embedded in a preset.
**`validateRotationPlan(plan, roster, rules)` takes no profile** — a plan's
legality never depends on coaching style.

**Hard type-level cutoff:** §8 may read only `profile.planning`; §9/§14 may read
only `profile.runtime`. Enforce it with the function signatures, not comments.

**Combined §8 + §8A exit gate** (supersedes §8's determinism bullet):
- Deep-equal plans from identical **league seed + roster/availability snapshot +
  coach profile ID/version + generator version**; save/load and coach/team
  processing order change nothing; streams are per-team and per-coach.
- All eight presets validate; the eight default coaches receive deterministic
  assignments that loading never silently changes.
- Changing only *runtime* tendencies does not change §8 generation; changing
  *planning* tendencies changes a controlled roster's plan while it stays valid.
- Every generated plan totals exactly the derived regulation minutes with five
  unique eligible starters and ≥ 5 positive-minute players; invalid plans cannot
  be saved (specific, typed issues).
- The `workhorse-core` fixture has fewer positive-minute players and a higher
  top-five minute share than `deep-collective`; the `development-lab` fixture
  gives a qualified prospect more planned minutes than `veteran-hierarchy`; the
  `star-stagger` runtime fixture keeps an eligible primary creator on court when
  a legal substitution allows.
- No profile can legalize an unavailable or disqualified player.
- User-edited plans survive CPU regeneration and coach-profile changes; roster
  repair preserves unaffected user targets and uses the profile only for the
  necessary replacement/redistribution decisions.
- Auto Rotation uses the current coach's planning profile; saving from the editor
  marks the plan `user-edited`; the simulator reads the saved plan and the
  assigned runtime profile.
- `grep -rn "DEFERRED(§8)" src/` returns nothing. All four gates green.

### 8B. Detailed player ratings and category drilldown

**Decision (2026-07-17).** The authoritative player-skill model becomes the
**67 numeric sub-ratings**; the existing **16 categories become derived
letter-grade headings**, joined by two new derived categories — **Durability**
and **Intangibles** — for **18 total**. This reverses today's model, where the 16
categories are themselves the stored numbers (`src/domain/ratings.ts`). The full
taxonomy, weights, and grade boundaries are frozen in **ADR 0008** (Accepted
2026-07-17).

Single source of truth:

> Stored sub-ratings → derived category score → derived letter grade.

Never store both layers — a stored parent could disagree with its derived
children. Grades, category scores, offense/defense summaries, position fit, and
**Overall are all derived, never stored**.

- **Overall is derived + displayed only** — shown on cards and the player quick
  view, never written to the save, never read by the simulation. **Potential is
  removed entirely** (not stored, not shown, not a rating). Development is its
  own system (§12) and never surfaces a potential-ceiling number.
- **Simulation reads sub-ratings** through *versioned event selectors* (driving
  finish, catch-and-shoot three, pass, turnover, rebound, fatigue, …), never the
  letter grade and never the category weighted score as a shortcut. Display-
  category weights and simulation-event weights carry **separate versions** —
  changing a UI weight must not change a game outcome.

**Sequencing (decided 2026-07-17).** §8B lands **before** the §8 rotation half,
§8A, and §9. The rotation generator's `currentAbility` becomes a *versioned,
position/role-aware ability selector over sub-ratings* (never a hidden overall),
and every §9 event formula reads sub-ratings — so the model is built once and
everything downstream consumes it from day one.

**Sub-steps.**
- **R1 — Freeze the taxonomy (ADR 0008). ✅ done 2026-07-17.** 18 categories, 67
  sub-ratings; names and structure locked (basis-point weights, each category
  totals 100%). Weights are V1 pending simulation calibration. Review trimmed
  Pass Versatility, Situational Awareness, and Adaptability; merged the two
  rebound-read skills into a shared Rebound Reading; and added the Durability and
  Intangibles categories.
- **R2 — Pure detailed-rating domain. ✅ done 2026-07-18.** Exact sub-rating key
  constant; closed strict record type + parser (reject
  missing/extra/non-integer/out-of-range); category-definition registry;
  weighted category selector; existing grade selector; version constants.
  Grades and scores are never stored. Shipped as
  `src/domain/detailedRatings.ts` with the full taxonomy pinned twice — module
  registry + an independent manifest in the tests — so silent drift on either
  side fails. Adversarially verified against ADR 0008 field-by-field (zero
  transcription mismatches). Note: ADR 0008's H1 and one Compatibility line
  still carry the stale pre-review "16/65" counts; the decided body (18/67) is
  what the code implements — ADRs are superseded, never edited.
- **R3 — Detailed generation V2. ✅ done 2026-07-18.** Player-quality baseline +
  category aptitude + position bias (+ optional archetype bias) +
  field-specific variation → clamp to a 0–100 integer. Labeled seed hierarchy
  `player-quality/v1/{id}`, `player-category/v1/{id}/{cat}`,
  `player-skill/v1/{id}/{sub}` so adding a future field shifts nothing. Golden
  vectors; distribution reports. Shared Rebound Reading takes the rounded mean
  of its two categories' aptitude + bias terms.
- **R4 — League validation + snapshot bump. ✅ done 2026-07-18.** Replace the
  stored macro ratings with the detailed model; add
  schema/generation/definition versions; **monotonic snapshot bump** (3 → 4) —
  clean version break, no migration (per §7), a new league is required.
  No-regeneration restore preserved. The legacy 16-macro model was deleted
  (`ratings.ts` keeps only the grade scale); the view models bridge to 18
  derived category rows and the Skills accordion shows real sub-ratings.
- **R5 — Rating view models. ✅ done 2026-07-18.** Category rows, grade derivation, child rows,
  calculation disclosure, grouping; memoized by (player reference, definition
  version).
- **R6 — Player-details UI. ✅ done 2026-07-18 (built UI-first, wired at R5).** The quick view + player page (see below). Accordion
  category grades; click a category to reveal its numeric children; keyboard +
  `aria-expanded`/`aria-controls`; grade as text, not colour alone; mobile stacks
  vertically; expansion is transient React state — never persisted, never a save
  revision.
- **R7 — Integrate with §8 rotation. ✅ done 2026-07-18 (selector shipped; §8 consumes it next).** Define the versioned rotation-ability
  selector (position/role-weighted over categories); rotation legality stays
  rating-independent; pin CPU-plan golden vectors.
- **R8 — Freeze before §9. ✅ done 2026-07-18.** Document each event → sub-rating usage; confirm
  grades are presentation only; §9 consumes the detailed model from its first
  line.

**Ratings vs tendencies.** Ratings = *how well* (derived, letter-graded);
tendencies (usage / rim / mid / three / pass / draw-foul) = *how often*
(numeric or bars, never graded, high ≠ good). They stay separate sections.

**Scouting (later).** True sub-ratings always drive the sim; scouting is a
separate knowledge layer that shows owned players exactly and outside players as
ranges + confidence — never the true number plus a cosmetic band.

**Player quick view (hover-only preview) — built UI-first 2026-07-17
(`playerQuickView.tsx` + shared `playerSections.tsx`):**
1. Identity — name, jersey, primary/secondary position, age, team; **Overall**
   to the right; the left-to-right Key Stats row
   (PTS/REB/AST/STL/BLK/FG%/3P%/TS%) beneath.
2. Target Role — one full-width block, label left / value right: target role,
   actual role, target MPG, actual MPG, usage rate.
3. Contract — same label/value rows: contract, years left, guaranteed, total
   value, contract type (the one contract summary that stays on the player
   surface; detailed contracts → Finance).
4. Position & Role Coverage — same label/value rows, last.

Nothing else on the preview: no Health, no grades, no action buttons — and it
renders **only while a roster row is hovered or keyboard-focused** (Alex:
never visible otherwise).

Hover shows the quick view; **click opens the full player page** (no separate
"player card") — built UI-first 2026-07-17 (`playerPage.tsx`), in the quick
view's visual language (Alex: "keep that texture"). Alex's Court Dynasty
reference is **imposed whole**, with exactly three deltas: **no badges** (we
don't use badges — the Shooting Zones court spans that entire area), **no
Potential anywhere**, and every panel whose system doesn't exist shows an
honest Coming-later absence:
- **Roster rail (left, real)** — the team's players with position, OVR
  number + letter; clicking switches the open player. Team Chemistry panel
  beneath it is a later slot (morale system).
- **Hero band** — jersey number, name, team · positions · age (real);
  height/weight/wingspan/handedness and the Status / Team Status / Draft /
  College / Agent / Personality / Work Ethic profile list are later slots
  (player bio + personality systems); Quick Summary top-right is a later
  slot (scouting).
- **Stat-card row, left-aligned** — OVR (real: number + letter), then
  Contract (format: years · total value), Health, Morale, Fatigue as honest
  Coming-later cards.
- **Tabs** — Overview and Skills live; Performance (§11), Role (§8),
  Contract and Career (later).
- **Overview, three columns like the reference, letters only**: Position
  Profiles (fit real; per-position Offense/Defense/Overall letters are §8B)
  + Physicals + Mental | Season Stats grid
  (MIN/PTS/REB/AST/STL/BLK/FG%/3P%/FT%/TS%/USG%/PER, §11) + Shooting Zones
  court (zone FG% from shot locations, §14) | Skill Breakdown + derived
  **Concerns / Strengths** (real: worst/best four graded categories,
  display-only).
- **Skills tab** — the complete breakdown as a letter accordion (grouped
  Skills / Physicals / Mental); clicking a letter drops its stored number
  down; the §8B sub-ratings replace that single number. Expansion is
  transient React state, never persisted.
- **Bottom action bar** — Compare Player · Trade Center · Watch Player ·
  Edit Player, all Coming later (comparison / trade / watchlist / editor).
Trade Block → **Trade Center**.

**Roster screen (rebuilt 2026-07-17, references captured):** table columns
Player · Status · Pos/Role · Age · OVR · Impact · Contract (years) · Dev — no
Potential and no Skills columns anywhere; the right rail holds the half-court
**Depth Chart** panel (`rosterDepthChart.tsx`, natural players ordered by the
derived Overall until §8 supplies real depth). The quick view floats as a
compact popover anchored beside the hovered row, clamped to the viewport so it
is always fully visible.

**Cross-screen UI notes (2026-07-17), captured so they aren't lost:**
- Team Overview: Recent Transactions / News moved flush-left into the gap beside
  Team Metrics; Age Breakdown removed — age distribution is background-only, never
  shown. *(Done 2026-07-17.)*
- Roster screen (later, §18): reuse the depth-chart panel; delete the roster-
  composition block; salary tiers and contract expirations → Finance.
- Training camp ↔ preseason: relationship **TBD** — decide later.
- G-League affiliate development: **autonomous background** system that emits
  player news; not a manual screen.

**Exit gate.**
- Every player stores all approved sub-ratings and **no** grade, category score,
  overall, or potential.
- All 16 grades derive from the versioned definition; clicking a category reveals
  its numeric children (keyboard accessible, mobile-friendly, no persistence
  write).
- Identical seed reproduces identical detailed players; adding a field shifts
  nothing; restore never regenerates.
- CPU rotation selection uses the versioned ability selector; simulation has an
  approved sub-rating → event mapping and display weights cannot change outcomes.
- Snapshot version bumped. All four gates green.

### 9. Simulation kernel — one game

**Goal.** `simulateGame(input, random): GameResult` producing a **real** instance
of the contract §6 froze. Pure and in-memory — this section persists nothing and
changes no snapshot.

**Keep the basketball model simple.** This is a walking skeleton behind the box
score interface. Depth is §14; hitting the §6 contract is what matters here. When
this lands, the §6 screens render simulated data instead of fixtures, and the
fixtures become test data.

**Decide and record in `SIMULATION_MODEL.md`:**
- **Tendency normalization.** `rim`, `midrange`, and `threePoint` are
  independent 0–100 values that do **not** sum to 100. How they become a shot
  distribution is a versioned formula — choose deliberately and write it down.
- **Game seed derivation:** `deriveSeed(rootSeed, 'game/v1/<gameId>')`, using the
  existing labeled-derivation machinery.

**Work.**
- Create `src/simulation/`. Implement `SimulateGameInput` and `simulateGame`
  against the frozen §6 types, consuming `MILESTONE_1_LEAGUE_RULES` and the
  §8 rotation plans — the sim reads the rule pack, never constants.
- The live rotation engine compiles the saved plan into decisions at legal
  dead-ball opportunities: compare actual vs expected minutes, swap
  over-target and tired players for under-target eligible ones, keep five
  legal players always. The plan is a workload target, not a script — never
  stop live play because a planned substitution second arrived. Overtime
  allocates its extra 25 player-minutes at runtime; the saved 240 is never
  edited. Foul-outs force legal replacement.
- Build the box-score builder and its invariant assertions **from the first
  slice**, so an invalid result can never be constructed.
- Record `SIMULATION_VERSION`, RNG version, rules version, derived game seed,
  and an input fingerprint on every result.

**Exit gate.**
- Exactly one winner per game; no ties survive.
- Team points = summed player points = summed period points.
- Regulation player time totals exactly 240 minutes per team; overtime exact.
- Made shots never exceed attempts; no statistic negative, fractional where
  integral, infinite, or `NaN`.
- Identical inputs + seed deep-compare equal across a large fixed seed set.
- The §6 screens render a simulated result with no shape changes — if they need
  changes, the contract was wrong and that is worth knowing here.
- Nothing under `src/simulation/` imports React, DOM, persistence, or network,
  and `Math.random` appears nowhere.
- All four gates green.

### 10. Commit a result and advance the clock

**Goal.** One game reaches **Final** end-to-end: `currentDate` → find the day's
games → validate rosters and rotations → simulate → commit → the real Calendar
and Team Schedule show a real result.

**This is the first snapshot bump** — cheap now, thanks to §7. The shape is
whatever §6 designed and §9 produced; do not redesign it here.

**Work.**
- Add results to `LeagueSnapshot`; bump to the next monotonic version
  (**6** — §8 takes 5 for rotation plans; numbers assigned when they land). Per
  [ADR 0005](adr/0005-scheduled-game-vs-game-result.md), `GameResult` stays a
  **separate immutable aggregate keyed to one `GameId`**.
- `commitGameResult`: revision-guarded and atomic — validate, store the result,
  and update schedule lifecycle together. Copy the `updateManagedTeam` pattern
  (`expectedRevision` → re-parse → `LeagueSnapshotStaleWriteError` → write →
  verify by re-read).
- `advanceToNextGameDay`: move `Season.currentDate`.
- **Unpin the clock.** `createSeasonFoundation.ts:551` currently *asserts* that
  `currentDate` differing from `regularSeasonStartDate` is an error. Its own
  comment concedes it "is not a validator for later published, postponed, or
  completed season state." It must be narrowed to creation-time only.
- **Now rewrite the absence tests — deliberately, not by deletion.** The ring
  that held through §6 (`tests/ui/schedulePages.test.tsx:297`,
  `tests/app/teamScheduleViewModel.test.ts:844`,
  `tests/app/dashboardViewModel.test.ts:99`) asserts results cannot exist. That
  was correct and honest. **This is the section where it stops being true.** Turn
  each into its positive counterpart — asserting results *do* render — rather
  than quietly removing it.

**Exit gate.**
- One scheduled game goes from `scheduled` to `completed` with a committed
  result, persisted and restored across a reload.
- The real League Calendar and Team Schedule show that game as Final with a real
  score; the Final filter returns it.
- A stale-revision commit is rejected, not applied.
- Re-simulating identical inputs reproduces a deeply-equal result.
- All four gates green.

### 11. Standings and season statistics

**Goal.** Derive standings and season totals as a **pure fold over committed box
scores**. Box scores stay the source of truth; nothing is stored that cannot be
recomputed.

**Work.**
- Fold completed results into standings; deterministic tiebreakers.
- Fold player box scores into season totals; derive per-game values and nullable
  percentages.
- Note: `TeamSeason` has no win/loss fields today. Prefer deriving the record
  over storing it; if it is stored, it must be verified by recomputation.
- Aggregation consumes no randomness and is re-runnable.
- The standings and season-stat **screens** are §18 — but if you want to design
  them first, do it the §6 way: fixtures, dev preview, absence tests green.

**Exit gate.**
- Wins + losses = games played; league wins = league losses = completed games.
- Standings match every committed result exactly.
- Season player totals match the sum of game rows.
- Zero-attempt percentages are null, never `NaN`.
- All four gates green.

### 12. Full season

**Goal.** Sim all 112 games across 28 game days at 8 teams.

**Work.** Advance game-day by game-day to the season's end. Handle the season
lifecycle transition at conclusion. Add a fixed-seed full-season fixture.

**Exit gate.**
- A full season sims from opening to conclusion with no invalid state.
- Standings equal the completed results.
- Identical seeds reproduce a deeply-equal season.
- All four gates green.

### 13. Multi-season loop

**Goal.** Roll season to season and sim ~5 seasons without drift or corruption.
**This is the gate that unlocks §15.**

**Work.** Season rollover: new season, new schedule, carried league state.
Player aging is *out of scope* unless it is explicitly added as its own section.

**Exit gate.**
- ~5 consecutive seasons sim cleanly in a loop.
- No drift, corruption, or ID collision across seasons.
- Every season deterministic and persisted/restored.
- All four gates green.

---

# Part III — Depth

### 14. Deepen the possession engine

**Goal.** Make the basketball good. Because the box score is the interface, this
changes internals only — the §6 screens, standings, and persistence are
unaffected.

**May start any time after §9**, since it lives behind the box-score interface.
Sequenced here so the loop is proven first.

Narrow vertical slices, box-score assertions active throughout:

1. period clock, possession switching, exact player seconds;
2. valid lineups, dead-ball substitutions, planned-minute targeting;
3. shot selection and two-/three-point make/miss;
4. turnovers and steals;
5. fouls, bonus, foul-outs, free throws;
6. rebounds and offensive-rebound continuation;
7. assists, blocks, defensive effects;
8. fatigue;
9. overtime and termination guards;
10. final box-score validation and reproducibility metadata.

Each slice adds forced-path tests plus deterministic seed-loop invariant tests.

**Exit gate.**
- Every slice's forced paths are covered.
- Invariants hold over a large fixed seed set.
- Fixed-seed distribution reports fall in documented broad bands.
- Any formula change carries a `SIMULATION_VERSION` bump and new golden tests.
- All four gates green.

---

# Part IV — Scale

### 15. Thirty teams

**Gated on §13.** The hard parts are already solved and green on the shelf: NBA
date anchors, the balanced 30×82 meeting matrix, conflict-free date placement,
conference/division alignment, and the additive 1230-game generator. What remains
is wiring plus coordinated test updates.

**This must land as one coordinated commit.** `generateLeague` seed-*selects*
teams from `FICTIONAL_TEAM_IDENTITIES`, so merely appending identities changes
which 8 teams today's league draws and breaks pinned fingerprints. Team count,
schedule generation, and the fixture/test updates cannot be half-migrated.

Step detail and the 18 ready-to-paste identities: **`NBA_SCALE_PLAN.md`**.

**Exit gate.**
- 30 teams, 360 players, 82 games each (41/41), 1230 games over the 174-day
  window; no team twice in a day.
- Calendar events are authoritative rather than derived.
- All characterization tests updated together; the suite is green in one commit.

### 16. Postseason and NBA Cup

Play-in, four best-of-seven rounds seeded per conference, and the Cup group /
knockout. New domain, generation, and UI.

---

# Part V — Product

### 17. Full save system

**Migrations become real here.** From this section on, saves belong to players and
must survive. Autosave with the latest 20 revisions; named manual saves retained
until explicit confirmed deletion; staged JSON export/import with a 50 MiB
ceiling; collision-safe "keep both"; a real migration registry and fixtures.

**Exit gate.**
- A failed save or import cannot alter the prior head.
- Only autosaves outside the newest-20 window are pruned; no named save is ever
  overwritten or deleted without explicit confirmation.
- Quota failures preserve prior state and are reported clearly.
- Corrupt or unsupported files are rejected with actionable errors.
- Round trips preserve domain state.

### 18. Remaining screens

Roster; depth chart; standings; season player statistics; save management,
export, import preview, and confirmations. (Result and box score are §6; the
rotation editor is §8.) Components dispatch commands — they never contain
possession formulas, mutate season state, or reinterpret statistical rules.

Build these the §6 way: screens first against fixtures, then the data.

**Exit gate.** The full player loop works from new league through a completed
season. Invalid rotations and imports are visibly blocked. Every completed game
stays inspectable. Keyboard and semantic-table/form checks pass.

### 19. Release gate

Deterministic full-season suites over fixed seed sets. Storage quota and
interrupted-write behavior. Export/import across fresh browser storage. Verify no
runtime request leaves the app. Audit all generated identities for fictional,
local-only compliance. Accessibility audit. Remove unused starter assets and the
dev preview route if it is no longer wanted.

**Release gate.** Acceptance criteria in `GAME_DESIGN.md` pass; invariants in
`DATA_MODEL.md` pass; all four gates pass from a clean checkout; known
limitations documented. **`grep -rn "DEFERRED(" src/` returns nothing** — every
numbered tag was filled by its section, and every `DEFERRED(later)` item was
either given a section and built, or consciously cut and recorded here.

---

## Deferred-slot ledger (plug in as we go)

UI-first means screens ship with slots their data can't fill yet. Each such
slot carries a **`DEFERRED(§N)` comment in the code at the exact place to
change**, naming the roadmap section that unblocks it. The code tags are
canonical — this table is the human index and may lag them; when in doubt,
grep.

**The rule:** finishing section N means sweeping its tags. `grep -rn
"DEFERRED(§N)" src/` → fill every hit → the tag comes out with the fix. A
section with surviving tags is not done. That is the whole system: nothing to
remember, only a grep that must come back empty.

Current index (2026-07-17):

| Unblocks at | Slot | Where |
| --- | --- | --- |
| §8 | The Rotation & Gameplan board + 48-minute map become the functional editor (a visual mockup does not clear this); Coach's Chair Rotation chip/pulse tile + Lineup Reality; quick-view Target Role rows; player-page Role tab; roster Role column; roster Target column; depth-chart depth ordering (OVR-order placeholder) | `rotationGameplanPage.tsx`, `homePage.tsx`, `teamOverviewPage.tsx`, `playerSections.tsx`, `playerPage.tsx`, `dashboardPages.tsx`, `rosterDepthChart.tsx` |
| §10 | Continue (advance game day); Sim Game; Recent Results fills with real Finals; retire the dev-preview entry | `homePage.tsx` |
| §11 | Record · Seed · Streak (command bar); Records · Ranks · Last 10 (Next Game); Season Pulse (all of it); Standings values; Team Stats ranks; team records in the post-game header; Coach's Chair Record chip, Opponent Prep matchup stats, Performance pulse tile, Last 10 Games; quick-view Key Stats row; player-page Season Stats grid + Performance tab; roster Impact / Actual / USG% / Form columns | `homePage.tsx`, `gameResultPage.tsx`, `teamOverviewPage.tsx`, `playerSections.tsx`, `playerPage.tsx`, `dashboardPages.tsx` |
| §12 | Sim to Next Event (multi-day advance) | `homePage.tsx` |
| §14 | Watch Game; and the event log unlocks at once: Game summary, Play-by-Play + key moments, Charts (game flow, shot chart), largest lead / lead changes / points off turnovers / points in paint; player-page Shooting Zones court | `homePage.tsx`, `gameResultPage.tsx`, `playerPage.tsx` |
| §15 | Division/Conference standings split (needs the 30-team alignment) | `homePage.tsx` |

**`DEFERRED(later)` — needs systems not yet on the roadmap.** These must each
either get a roadmap section or be consciously cut at §19; they may not just
evaporate:

| Slot | Needs |
| --- | --- |
| Needs Attention actionable items (injuries, trade offers, deadlines, roster problems) | injury, trade, contract systems |
| Next Game availability report | injury system |
| Roster Health (injuries, fatigue, availability) | player-health systems |
| Front Office card (payroll, cap, tax, contracts) | financial model |
| Important Headlines | league news system |
| Post-game Game Info layer (venue, attendance, referees, game time) | venue/officials systems |
| Coach's Chair: Next Decision Point, Decision Stack, Cross-Department Conflicts, header chips (Availability / Team Readiness / Chemistry / Cap Room), Schedule Pressure workload flags, Health + Development pulse tiles | decision / medical / morale / financial / development systems |
| Coach's Chair: Recent Transactions / News | transaction + news systems |
| Medical Department: availability board, workload, injuries & rehab, return-to-play stages | medical system |
| Coaching & Development: player plans, staff, weekly plan, progress, mentorship | development + staff systems |
| Quick view (pinned): Health and Development tabs | medical / development systems |
| Roster: Contracts and Compare tabs | financial / comparison systems |
| Player surfaces: Contract / Health / Morale / Fatigue stat cards; hero bio (height/weight/wingspan/handedness) + profile list (status, team status, draft, college, agent, personality, work ethic); Team Chemistry rail panel; Contract + Career tabs; scouting Quick Summary; quick-view Contract rows; roster Status / Contract / Dev columns; Compare Player, Trade Center, Watch Player, Edit Player | financial / medical / morale / development / scouting / player-bio / watchlist / player-editor / trade systems |

Clickable destinations already wired (live now; they land on honest planned
pages until those pages are built): Review Offers → `front-office-market`,
View Free Agents → `front-office-free-agency`, Adjust Rotation →
`team-rotation-gameplan`, View Finances → `finances-overview`, View Full
Schedule → `schedule-team-schedule`. Team Overview adds: Review Rotation →
`team-rotation-gameplan`, Medical Department / View Health → `team-health`,
Front Office → `front-office-overview`, View Development → `team-development`.

## Risks

| Item | Risk | Handling |
| --- | --- | --- |
| Docs drifting ahead of code | specs describe unbuilt systems as though they exist; a false claim survived long enough to reach a plan | this file is the only status; specs are explicitly design-only and lose to the code |
| Fixtures leaking into the real app | a designed-against-fake screen ships showing invented results, violating ADR 0005 | fixtures are dev/test only; the absence tests stay green through §6 and are the tripwire |
| UI-first drifting into endless polish | the screens keep improving and no basketball is ever played | §6 exits when the types freeze; §9 follows immediately |
| A screen that cannot be simulated | the box score asks for data the engine can't plausibly produce | fixtures must obey the invariants, so the design is always against producible data |
| Generated identities | a combination could resemble a real professional identity | deliberately fictional components, uniqueness checks, content audit at §19 |
| Simulation balance | deterministic formulas can be correct but unfun | fixed-seed distribution reports; version constants intentionally |
| Test runtime | thousands of games slow the normal loop | keep the fast required suite separate from an extended deterministic suite |
| Save evolution after 1.0 | formula changes cannot reproduce old results | preserve completed results; record engine and data versions on every result |
| Import safety | structurally valid JSON can still be semantically corrupt | stage as `unknown`, validate whole-season invariants, then write atomically |
| Rotation plan vs actual minutes | users expect exact individual minutes | label values "planned"; show actual box-score minutes |