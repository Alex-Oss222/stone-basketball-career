# Repository Instructions

These instructions apply to the entire repository.

## Scope and repository safety

- Work only inside this repository.
- Never edit files outside this repository.
- Never deploy or publish the project.
- Never create Git commits unless the user explicitly requests one.

## TypeScript and architecture

- Explicitly set `"strict": true` in every TypeScript configuration.
- Keep basketball simulation logic independent from React.
- Simulation code must never import React.
- Use an injected seeded random-number generator.
- Do not use `Math.random` inside simulation code.

## Product boundaries

- Do not add a backend, accounts, authentication, analytics, telemetry, advertising, cloud storage, or runtime internet requirements.
- Use only fictional teams, players, names, logos, and data.

## Saves and user data

- Save game state locally.
- Use IndexedDB for local persistence.
- Version and validate all save files.
- Never silently overwrite a save.
- Retain the latest 20 autosave revisions.
- Delete autosave revisions only under the disclosed 20-revision retention policy.
- Retain every named manual save until the user explicitly deletes it.
- Never silently delete a named manual save.
- Report storage quota failures clearly.

## Quality

- Add automated tests for simulation rules.
- Use Vitest as the test runner; add it only as a development dependency when implementation begins.
- Explain why before adding a production dependency.
- After future implementation tasks, run automated tests, TypeScript checking, linting, and the production build.

## Task handoff

At the end of every task, report:

- changed files;
- commands run;
- test results;
- known limitations; and
- the recommended next task.
