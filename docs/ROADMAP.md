# Stone Basketball GM — Milestone 1 Roadmap

## Scope

This roadmap ends with Milestone 1. Generic season and scheduling contracts
include explicit versioned rule-pack, event, constraint, and diagnostic
boundaries so the current engine is not tied to one league formula. Those
boundaries are not delivery commitments or placeholder behavior for later
gameplay systems.

Milestone 1 delivers:

- eight fictional teams with 12 fictional players each;
- team selection;
- roster and depth-chart/rotation screens;
- five starters and a valid 240-minute regulation plan;
- a deterministic generated regular-season schedule;
- possession-based simulation with player/team box scores;
- standings and season player statistics;
- IndexedDB autosave with the latest 20 revisions plus retained named manual saves; and
- validated, versioned JSON export/import.

Excluded systems remain excluded rather than being represented by inactive fields or placeholder screens.

## Current repository baseline

As inspected on 2026-07-16:

- the repository is a minimal React 19 + Vite 8 TypeScript starter;
- `package.json` has `dev`, `build`, `lint`, and `preview` scripts;
- there is no automated test script or test source;
- TypeScript project references cover the browser app and Vite configuration;
- neither TypeScript configuration explicitly enables `strict`;
- Oxlint enables React hooks and component-export rules;
- the current application source is only the starter counter/documentation screen;
- React and React DOM are the only production dependencies;
- the lockfile is version 3 and the installed top-level dependency tree is valid; and
- Git branch `milestone-1` was clean before the planning files were created.

No dependency or application-source change is part of this planning task.

## Delivery principles

- Explicitly set `"strict": true` in every TypeScript configuration before introducing domain types.
- Build and test pure domain/simulation modules before connecting React.
- Generate fictional league data deterministically from the league seed, persist the generated snapshot, and validate it as part of tests.
- Treat box scores as the source of truth for standings and season statistics.
- Treat every simulation result and save revision as immutable after commitment.
- Add persistence through an adapter so browser APIs never enter simulation code.
- Prefer platform capabilities and existing dependencies; justify any proposed production dependency before adding it.
- Complete each phase with automated tests, TypeScript checking, linting, and a production build.

## Phase 0 — Record the approved baseline

The approved baseline is:

1. eight deterministically generated fictional placeholder teams using initials/CSS marks;
2. 12 deterministically generated fictional players per team, persisted with all identity and basketball fields;
3. 28 games per team in a four-round-robin schedule;
4. four 12-minute quarters, 24/14-second clocks, six personal fouls, and five-minute overtime;
5. whole-minute rotation editing with internal seconds;
6. chronological game-day advancement;
7. IndexedDB with the latest 20 autosave revisions and all named manual saves retained until explicit deletion;
8. deterministic extreme-overtime and insufficient-player continuation guards;
9. a 50 MiB JSON import ceiling; and
10. Vitest as a future development-only test dependency.

Exit gate: these decisions remain consistent across all Milestone 1 design documents before implementation begins.

## Phase 1 — Strict TypeScript and test foundation

Work:

- explicitly enable TypeScript strict mode for app, tooling, and tests;
- add a standalone `typecheck` script;
- add Vitest as a development dependency;
- add cross-platform `test` and extended fixed-seed test scripts;
- add architecture checks that forbid React imports and `Math.random` in simulation code; and
- keep React starter behavior unchanged during the foundation step.

Exit gate:

- strict type checking passes;
- the single test runs on the supported local command;
- lint and production build pass; and
- Vitest is development-only and no production dependency is added.

## Phase 2 — Domain model and fictional league data

Work:

- add branded stable IDs and narrow runtime parsing helpers;
- add team, player, ratings, tendencies, rotation, schedule, box-score, and season types;
- implement deterministic generation of eight fictional placeholder teams and exactly 96 fictional players from a dedicated league seed, with an independent versioned field stream for every stored player rating;
- generate and persist player names, IDs, ratings, ages, positions, team assignments, and tendencies;
- generate valid deterministic CPU starters and 240-minute rotations;
- implement league-data and rotation validators; and
- add tests for identity, ownership, counts, ranges, uniqueness, and rotation totals.

Exit gate:

- identical league seeds and generator versions produce deeply equal teams, players, and rotations;
- every player belongs to exactly one team;
- every team has exactly 12 players;
- all identifiers, fictional placeholder components, colors, and initials/CSS marks are local and unique;
- all eight default rotations are valid; and
- strict checking, tests, lint, and build pass.

## Phase 3 — RNG and schedule

Work:

- implement the injected `RandomSource` abstraction;
- implement and version seed normalization, derivation, and `xoshiro128**`;
- pin golden vectors;
- implement the seeded circle-method schedule;
- add timezone-free `LocalDate`, generic season lifecycle, event-calendar, and
  team-season records;
- construct a canonical opponent-requirement matrix before placing games;
- represent the fictional eight-team format as an explicit versioned rule set;
- separate original, current scheduled, and actual dates;
- add typed hard/soft constraint and whole-report diagnostic boundaries;
- derive stable game IDs and game seeds; and
- validate all schedule invariants.

Exit gate:

- identical root seeds produce identical schedules;
- different labeled streams are independent in golden tests;
- every schedule has 112 games and exact pairing/home-away counts;
- every schedule has 28 ordered, correctly spaced game days with four games
  and one appearance per team on each day;
- unsupported optimizer constraints are reported rather than ignored;
- every game references valid distinct teams; and
- strict checking, tests, lint, and build pass.

## Phase 4 — Game simulation kernel

Build in narrow vertical slices, keeping the box-score builder and assertions active from the first slice:

1. period clock, possession switching, and exact player seconds;
2. valid lineups, dead-ball substitutions, and planned-minute targeting;
3. shot selection and two-/three-point make/miss;
4. turnovers and steals;
5. fouls, bonus, foul-outs, and free throws;
6. rebounds and offensive-rebound continuation;
7. assists, blocks, and defense effects;
8. fatigue;
9. overtime and termination guards; and
10. final box-score validation and reproducibility metadata.

Each slice adds forced-path tests plus deterministic seed-loop invariant tests.

Exit gate:

- every completed game has exactly one winner;
- all required minute and statistical invariants pass over a large fixed seed set;
- identical inputs and game seeds deep-compare equal;
- simulation code contains no React, DOM, persistence, network, or `Math.random` usage; and
- strict checking, tests, lint, and build pass.

## Phase 5 — Standings and season statistics

Work:

- fold immutable completed games into standings;
- implement deterministic tiebreakers;
- fold player box scores into season totals;
- derive per-game values and nullable percentages;
- simulate fixed full-season fixtures; and
- verify cached or displayed values by recomputation.

Exit gate:

- wins plus losses match games played;
- total league wins equal completed games and total league losses;
- standings match every completed result;
- season player totals match game rows;
- zero-attempt percentages never become `NaN`; and
- strict checking, tests, lint, and build pass.

## Phase 6 — Versioned local persistence

Work:

- define save envelope version 1 and structured validation errors;
- implement whole-season semantic validation;
- implement IndexedDB autosave-revision, autosave-head, and named-manual-save stores;
- autosave at approved state boundaries;
- atomically retain the newest 20 autosave revisions and prune only older autosaves;
- retain every named manual save until explicit confirmed deletion;
- implement staged JSON export/import;
- implement collision-safe “keep both” behavior;
- establish the migration registry and version-1 fixtures; and
- test 19/20/21-autosave retention boundaries, named-manual-save survival, failed writes, quota errors, 50 MiB import boundaries, corrupt JSON, invalid references, future versions, and round trips.

The active-league schema foundation is a deliberately smaller prerequisite to
this phase. V1 remains the league-only snapshot; V2 is a strict JSON-safe DTO
containing the regular-season foundation and creation metadata. Its parser
validates exact shape, domain entities, references, stored schedule invariants,
exact supported rule-set versions, and JSON round trips without regeneration.
The pure V1-to-V2 migration requires explicit season inputs and performs no
storage operation itself. The active-league repository now composes it with a
single IndexedDB transaction: V1 remains at `current`, V2 is written at
`current-v2`, V2 has authoritative read precedence, and reread validation must
pass before commit. Managed-team updates and clearing use the V2 revision for
stale-write protection, while new leagues are constructed directly as V2 from
explicit season inputs. A separately confirmed corrupt-storage recovery purge
can delete both active versioned records without parsing malformed data; it is
not the normal clear path. This bridge still does not implement autosave-history
retention, named manual saves, full-season envelopes, or import/export, so it
does not by itself satisfy the Phase 6 exit gate.

Exit gate:

- a failed save/import cannot alter the prior head;
- no retained autosave revision is overwritten;
- only autosaves outside the newest-20 window are pruned;
- no named manual save is overwritten or deleted without explicit confirmation;
- storage quota failures preserve prior state and are reported clearly;
- valid round trips preserve domain state;
- corrupt or unsupported files are rejected with actionable errors;
- the app remains fully local and offline at runtime; and
- strict checking, tests, lint, and build pass.

## Phase 7 — React application screens

Integrate already tested domain commands and selectors:

1. new season and team selection;
2. application shell/navigation and autosave status;
3. roster;
4. depth chart and 240-minute rotation editor;
5. schedule and game-day advancement;
6. game result and box score;
7. standings;
8. season player statistics; and
9. save management, export, import preview, and confirmations.

React components dispatch application commands. They do not contain possession formulas, directly mutate season state, or reinterpret statistical rules.

Exit gate:

- the complete core player loop works from new season through game day 28;
- invalid rotations and invalid imports are visibly blocked;
- every completed game remains inspectable;
- autosave state and failures are visible;
- keyboard and semantic-table/form checks pass; and
- strict checking, tests, lint, and build pass.

## Phase 8 — Milestone 1 stabilization

Work:

- run deterministic full-season suites over fixed seed sets;
- tune only versioned simulation constants within documented broad guardrails;
- test storage quota and interrupted-write behavior;
- test export/import across fresh browser storage;
- verify no runtime request leaves the app;
- audit generated team/player names, initials/CSS marks, colors, and component data for fictional/local-only compliance and avoidance of real professional team identities;
- audit accessible labels, focus order, validation messages, and responsive tables; and
- remove starter-only assets/content that are no longer used.

Release gate:

- all Milestone 1 acceptance criteria in `GAME_DESIGN.md` pass;
- every invariant in `DATA_MODEL.md` passes;
- automated tests, strict TypeScript checking, linting, and production build pass from a clean checkout with already installed dependencies;
- known limitations are documented; and
- deployment and publishing remain outside the task.

## Test matrix

| Area | Unit | Forced branch | Seed loop/property | Full integration |
| --- | --- | --- | --- | --- |
| IDs/data/rotations | yes | invalid ownership | generated invalid cases | league load |
| RNG | golden vectors | boundary values | many seeds/ranges | replay |
| Schedule | round construction | malformed teams | many seeds | full season |
| Possessions | formulas/events | every result branch | thousands of games | game result |
| Minutes/substitutions | lineup solver | foul-out/emergency | extreme rotations | full game |
| Box scores | event builder | every stat event | all simulations | season fold |
| Standings/stats | tiebreak/percentages | zero games/attempts | result permutations | full season |
| Saves | validators/migrations | corruption/quota/collision | JSON round trips | fresh import |
| React | selectors/forms | invalid rotation/import | not applicable | core player loop |

Tests use fixed seeds and print replay information on failure. Statistical calibration uses broad fixed-seed bands; exact accounting uses hard assertions.

## Risks and unresolved details

| Item | Risk | Proposed handling |
| --- | --- | --- |
| Generated league identities | a generated combination could resemble a real professional identity | use deliberately fictional local components, deterministic uniqueness checks, and a content audit |
| Rotation plan versus actual minutes | users may expect exact individual minutes | label values “planned”; show actual box-score seconds/minutes |
| Autosave retention and quota | 20 autosaves plus unlimited named manual saves can consume browser quota | atomically prune only autosaves beyond 20, never prune manual saves, and report quota errors clearly |
| Browser storage availability | private modes or policies may restrict IndexedDB | detect failure before relying on autosave and prominently offer JSON export |
| Simulation balance | deterministic formulas can be correct but unfun | use fixed-seed distribution reports and version constants intentionally |
| Test runtime | thousands of games may slow the normal loop | separate fast required tests from a deterministic extended simulation suite |
| Vitest setup | adding a runner expands development tooling | add Vitest only as a development dependency and keep production output independent of it |
| Overtime/foul guards | rare continuation behavior is a product rule | approve and test explicit deterministic guards |
| Save evolution | future formula changes cannot reproduce old results automatically | preserve completed results and record all engine/data versions |
| Import safety | structurally valid JSON can still be semantically corrupt | stage as `unknown`, validate whole-season invariants, then write atomically |

## Smallest proposed implementation task

Enable `"strict": true` in the existing app and Node TypeScript configurations, add a standalone no-emit `typecheck` package script, and run type checking, linting, and the production build without changing application behavior or adding dependencies.

This is intentionally smaller than creating domain entities or installing the already selected Vitest runner. It closes the known configuration gap and gives every later type a strict baseline.
