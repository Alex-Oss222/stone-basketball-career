# Stone Basketball GM — Milestone 1 Game Design

## Status

This document defines only Milestone 1. The product and league decisions recorded here are approved unless a detail is explicitly labeled **proposed** for later tuning.

## Product goal

Milestone 1 is a small, deterministic, single-player basketball season that runs entirely in the browser. The player chooses one of eight fictional teams, sets a starting lineup and rotation, simulates games possession by possession, and follows box scores, standings, and season statistics.

The experience should make three things immediately legible:

1. who is on the team and what each player is good at;
2. how the user's rotation changes who plays; and
3. why a game and season produced their results.

There is no server or runtime network dependency. Game state, autosaves, exports, imports, team art, names, and league data are local.

## Milestone 1 league

### Fictional league generation

A new season deterministically generates exactly eight fictional team records from the visible league seed. Team cities, names, abbreviations, and color combinations come from bundled fictional placeholder vocabularies and palettes. Generation must avoid real professional team identities. The generated values are persisted in the save, so opening an existing season never reruns generation or changes an identity.

Team IDs are derived from the league seed fingerprint and stable team ordinal, not from the display name. Milestone 1 uses text initials or simple CSS-based marks made from the saved abbreviation and colors. Finished logo assets are not required.

Each generated team receives exactly 12 generated fictional players, for 96 league players. Initial player IDs, names, ages, positions, team assignments, and tendencies are produced deterministically from a dedicated league-generation RNG stream. Every stored rating instead uses an independent field-specific stream derived from the league seed, player ID, rating-generation version, and canonical rating key, so adding a future rating cannot shift existing values. All generated player data is persisted in full. Reloading reads the saved snapshot; it does not regenerate the roster. Names are constructed from bundled fictional components and do not use real-world or scraped data.

### Proposed league rules

| Rule | Milestone 1 decision |
| --- | --- |
| Regulation | four 12-minute quarters |
| Players on court | five per team |
| Starters | exactly five distinct players |
| Regulation rotation | integer planned minutes from 0–48 per player, totaling exactly 240 |
| Shot clock | 24 seconds; 14-second reset after an offensive rebound |
| Personal-foul limit | six |
| Defensive bonus | fifth team foul in a quarter and later produces two free throws on a non-shooting foul |
| Overtime | repeated five-minute periods until the score is not tied |
| Regular season | four games against every opponent, two home and two away |
| Games per team | 28 |
| Total league games | 112 across 28 game days |

Overtime minutes are not part of the 240-minute regulation rotation plan. The simulation selects overtime lineups from eligible players using the approved rotation order, current fatigue, and foul status.

## Core player loop

1. Start a new season and choose one team.
2. Review the 12-player roster and ratings.
3. Select five starters and edit the regulation rotation until it totals 240 minutes.
4. Advance to the next scheduled game.
5. Simulate the game from a frozen pregame snapshot and view its team and player box scores.
6. Review updated standings and season player statistics.
7. Repeat through the 28-game regular season.
8. Continue viewing the completed season or export the save.

The user manages only the selected team. Other teams use deterministic default starters and rotations stored with league data. No excluded management systems are implied by the roster screen.

## Screens

### New season and team selection

- Accept or generate a visible season seed.
- Generate the eight-team, 96-player fictional league deterministically from that seed.
- Show all eight teams with saved fictional name, colors, initials/CSS mark, and short style summary.
- Create nothing until the user confirms a team.
- Explain that the seed controls initial league generation, schedule generation, and simulation randomness.

### Team roster

- Show 12 players with their persisted fictional names, ages, primary and secondary positions, ratings, and season counting/per-game statistics.
- Allow sorting without changing simulation state.
- Make rating scale and abbreviations discoverable.
- Link each player to a simple detail view or expandable row; a separate complex player system is not required.

### Depth chart and rotation

- Choose exactly five distinct starters.
- Edit whole planned regulation minutes for all 12 players.
- Show a live total, remaining/excess minutes, and inline validation.
- Disable game simulation while the plan is invalid.
- Require every starter to have at least one planned minute.
- Show zero-minute players as out of the planned rotation, while keeping them eligible as emergency substitutes after foul-outs.
- Preserve the accepted plan in a new autosave revision.

The 240 figure describes team regulation court time: five players multiplied by 48 minutes. Individual actual minutes may differ from planned minutes because substitutions occur at dead balls, players can foul out, and overtime is extra. Exact player seconds must still sum to 14,400 regulation player-seconds for each team.

### Schedule

- Show 28 game days and all league games.
- Clearly distinguish upcoming and completed games and the user's team.
- Allow simulation only in chronological game-day order for Milestone 1.
- Simulate non-user games deterministically when their game day is advanced.
- Open the box score for every completed game.

The domain foundation behind this screen is specified in
`SEASON_AND_SCHEDULING.md`. The current fictional league uses an explicit
versioned rule pack and a pre-date opponent matrix. Scheduled, original,
postponed, actual, and TBA dates remain distinct. Future NBA-style or custom
rule packs, Cup windows, Play-In dates, playoff dates, venues, travel, and
showcase preferences are extension points only; none of their behavior or
real-world dates is active in Milestone 1.

### Game result and box score

- Show final score, quarter and overtime scoring, winner, and game seed/replay metadata.
- Show player minutes, field goals, three-pointers, free throws, offensive and defensive rebounds, total rebounds, assists, steals, blocks, turnovers, personal fouls, and points.
- Show team totals derived from player rows.
- Display shooting percentages as an em dash when attempts are zero; never display `NaN`.
- A possession log is not required for Milestone 1, but the engine may expose an optional debug trace for tests.

### Standings

- Show games played, wins, losses, winning percentage, points for, points against, and point differential.
- Apply deterministic tiebreakers defined in the data model.
- Derive standings from completed games rather than treating a mutable standings table as the source of truth.

### Season player statistics

- Show games, games started, exact accumulated minutes rendered to one decimal place, counting totals, per-game values, and shooting percentages.
- Support league and team filters plus simple column sorting.
- Derive rate statistics at display time so a zero denominator renders as unavailable rather than `NaN`.

### Save management

- Autosave after new-season creation, acceptance of a valid rotation, completion of each game day, and successful import/migration.
- Show save name, last-saved time, revision number, format version, and autosave health.
- Retain the latest 20 autosave revisions for each season. After a successful new autosave, prune only autosave revisions older than that window.
- Allow named manual saves and retain every named manual save until the user explicitly deletes it.
- Never overwrite or delete a named manual save implicitly. A same-name collision keeps both unless the user explicitly chooses and confirms another action.
- Export a selected autosave revision or named manual save as JSON.
- Import into a staging area first; parse, migrate, and validate before changing the current session.
- On an ID collision, default to **keep both**. Replacing or deleting anything requires a specific user choice and confirmation.
- Reject JSON files larger than 50 MiB before parsing.
- If browser storage is full, preserve the last confirmed state and report the quota failure clearly. Offer export and explicit manual-save management; never silently delete a named manual save to make space.

## Product behavior and boundaries

- The app works after its static assets load, with no calls required to external services.
- Browser storage is the primary persistence mechanism; JSON is the portable backup.
- A game result becomes immutable after it is committed. Autosave-window pruning may remove an old snapshot, but it never rewrites the result inside a retained autosave or manual save. Milestone 1 does not include an ordinary “resimulate result” action.
- Simulation inputs are frozen at tipoff and recorded sufficiently to reproduce the result with the same simulation and RNG versions.
- All league content is fictional and bundled locally.
- Accessibility basics are part of each screen: keyboard access, semantic tables/forms, visible validation, and color-independent status cues.

The following are outside Milestone 1 and receive no design or placeholder systems here: contracts, salary cap, trades, drafts, free agency, scouting, injuries, personalities, chemistry, staff, playoffs, multiplayer, real-world data, AI APIs, and desktop packaging.

## Milestone 1 acceptance criteria

- A user can create a season with one of exactly eight teams and see exactly 12 players on every roster.
- A valid depth chart has five starters and a 240-minute regulation plan; invalid plans cannot start a game.
- The generated schedule gives every team 28 games, every opponent pairing four games, and balanced home/away assignments.
- Every scheduled game can be simulated to one winner and produces valid player and team box scores.
- Standings and season player statistics agree with completed game box scores.
- The same frozen inputs and seeds produce byte-equivalent domain results, excluding presentation timestamps.
- A season autosaves locally, retains its latest 20 autosave revisions, and retains all named manual saves until explicit deletion.
- A valid exported JSON save can be imported into a clean session.
- Invalid, unsupported, or corrupt imports are rejected without changing any existing save.
- The full season can be completed without runtime internet access.

## Approved implementation baseline

Milestone 1 uses:

1. eight deterministically generated fictional placeholder teams with initials/CSS marks;
2. 12 deterministically generated and persisted fictional players per team;
3. a 28-game four-round-robin schedule with balanced home/away games;
4. four 12-minute quarters, 24/14-second clocks, a six-personal-foul limit, and five-minute overtime;
5. whole-minute rotation editing with exact simulation time tracked internally in seconds;
6. chronological game-day advancement;
7. IndexedDB local persistence;
8. a 20-revision autosave window plus retained named manual saves;
9. a 50 MiB JSON import ceiling; and
10. deterministic continuation rules for extreme overtime and insufficient eligible players.
