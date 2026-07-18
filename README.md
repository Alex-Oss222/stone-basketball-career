# Stone Basketball GM

Stone Basketball GM is a work-in-progress, browser-only basketball management
game built with React and TypeScript. It generates a fictional eight-team league
deterministically from a visible seed and presents the league through roster,
player, team, schedule, and calendar views.

The game is being built UI first, and several management and simulation systems
are intentionally unfinished. [`docs/ROADMAP.md`](docs/ROADMAP.md) is the
authoritative source for the current status and next milestone.

## Local development

You need Node.js and npm versions compatible with the checked-in
`package-lock.json`.

```sh
npm ci
npm run dev
```

Vite prints the local development URL. The application has no backend or
account setup.

## Scripts

| Command | Purpose |
| --- | --- |
| `npm run dev` | Start the Vite development server |
| `npm run build` | Type-check all TypeScript projects and create a production bundle in `dist/` |
| `npm run preview` | Preview the production bundle locally |
| `npm run lint` | Run Oxlint across the repository |
| `npm run typecheck` | Type-check the app, tooling, and tests without emitting files |
| `npm test` | Run the Vitest suite once |

## Architecture

- `src/domain/` contains framework-independent types, invariants, rules, and
  validation.
- `src/generation/` builds deterministic fictional league and schedule data.
- `src/random/` provides the injected, seeded random source used by generation.
- `src/app/` contains commands, adapters, and presentation-oriented view models.
- `src/persistence/` owns the versioned snapshot format, runtime validation,
  repository behavior, and IndexedDB adapter.
- `src/ui/` and `src/App.tsx` contain the React interface and browser
  coordination.
- `tests/` mirrors those boundaries with domain, generation, persistence, app,
  and UI coverage.

Domain and generation code must stay independent from React, the DOM,
persistence, and network APIs. Deterministic code receives a seeded random
source; it must not call `Math.random`.

All teams, players, names, marks, and league data are fictional and bundled
with the application.

## Local saves

The application runs without a runtime internet requirement and stores its
current active-league snapshot in the browser's IndexedDB. Snapshots are
versioned and validated when they cross the persistence boundary. A snapshot
from an incompatible build is refused rather than silently rewritten, and the
interface offers the user an explicit way to start a new league.

The current persistence layer is a single-active-snapshot foundation. Autosave
history, named manual saves, and JSON import/export are later roadmap work; see
§17 of the roadmap. Clearing this site's browser data removes the local league,
and no save is synced to another browser or device.

## Documentation

- [`docs/ROADMAP.md`](docs/ROADMAP.md) — authoritative implementation status and
  sequence.
- [`docs/GAME_DESIGN.md`](docs/GAME_DESIGN.md) — milestone product design and
  acceptance criteria.
- [`docs/DATA_MODEL.md`](docs/DATA_MODEL.md) — data-model reference; some
  sections describe planned rather than shipped behavior.
- [`docs/SEASON_AND_SCHEDULING.md`](docs/SEASON_AND_SCHEDULING.md) — season,
  calendar, and schedule architecture.
- [`docs/SIMULATION_MODEL.md`](docs/SIMULATION_MODEL.md) — intended simulation
  contract and possession model.
- [`docs/NBA_SCALE_PLAN.md`](docs/NBA_SCALE_PLAN.md) — deferred 30-team scaling
  plan.
- [`docs/adr/`](docs/adr/) — accepted architecture decisions.
- [`docs/archive/`](docs/archive/) — superseded historical plans, not current
  guidance.

When documentation and implementation disagree about current behavior, the
code wins; when documents disagree about status or sequencing, the roadmap
wins.

## Validation

Run the complete local quality gate after implementation work:

```sh
npm run lint
npm run typecheck
npm test
npm run build
```
