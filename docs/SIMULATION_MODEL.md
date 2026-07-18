# Stone Basketball GM — Simulation Model

> ## ⚠ Nothing in this document is implemented.
>
> **This is a design spec, not a description of the code.** There is no
> `src/simulation/` directory. No `simulateGame`, `GameResult`, `BoxScore`,
> `RotationPlan`, or `LeagueRulesV1` exists anywhere in the tree.
>
> It is written in the present tense throughout ("The simulation is…",
> "Finalization rejects…"). **Read every such sentence as "will".** That framing
> is the single most misleading thing in these docs, and it is why this banner
> exists.
>
> What actually exists today, and is safe to rely on:
> - `RandomSource` (`src/random/randomSource.ts`) — matches the interface below
>   exactly.
> - `xoshiro128**` (`RANDOM_SOURCE_VERSION = 'xoshiro128ss-v1'`) and labeled seed
>   derivation.
> - The schedule generator described under "Schedule generation".
>
> Building this is [`ROADMAP.md`](ROADMAP.md) §9 (the kernel) and §14 (depth).
> **Keep the first version simple** — §9 is a walking skeleton behind the box
> score interface, not the engine described here. The roadmap decides what gets
> built and when; this file only describes the target.
>
> **The result contract is frozen** — decided by the §6 screens on 2026-07-17
> and recorded in "Frozen result contract" below. The kernel implements
> exactly `src/domain/gameResult.ts`; this document does not get to invent a
> different shape.

## §8B R8 — frozen rating reads (IMPLEMENTED, 2026-07-18)

Unlike the rest of this document, this section describes **shipping code**:
`SIM_RATING_READ_VERSION = 1` in `src/domain/simulationReads.ts`. The
simulation may read player sub-ratings **only** through these versioned event
selectors — never letter grades, derived category scores, the display
Overall, rotation ability, or the raw stored record. A test
(`tests/domain/simulationReadsAndAbility.test.ts`) keeps this table and the
registry in exact agreement, and an architecture guard forbids
`src/simulation/` from importing the rating domain directly.

Rules, frozen at R8:

- **Durability and Intangibles never enter possession events** (ADR 0008
  review decisions). `injuryResistance` and `loadDurability` feed only the
  future injury system; `competitiveness`, `coachability`, `composure`, and
  `workEthic` feed only development, coach-fit, and morale/clutch systems.
- Display weights (`CATEGORY_DEFINITION_VERSION`, `OVERALL_MODEL_VERSION`),
  planning weights (`ROTATION_ABILITY_VERSION`), and these simulation reads
  (`SIM_RATING_READ_VERSION`) are **independent version axes** — changing one
  can never change the others' outputs.
- The v1 factor per event is the **unweighted mean** of its dependency list at
  full precision. Per-dependency weighting inside an event is a §9 formula
  decision and bumps `SIM_RATING_READ_VERSION`.
- Changing any dependency list bumps the version and requires new golden
  simulations (§9).

### Event → sub-rating dependency table

| Event | Sub-ratings read |
| --- | --- |
| `shotSelection` | `decisionMaking`, `offensiveAwareness` |
| `rimShotResolution` | `standingFinish`, `drivingLayup`, `contactFinishing`, `dunking`, `postFinishing` |
| `midRangeShotResolution` | `catchAndShootMid`, `pullUpMid`, `contestedMid`, `postFadeaway` |
| `threePointShotResolution` | `catchAndShootThree`, `pullUpThree`, `movementThree`, `contestedThree` |
| `freeThrowResolution` | `freeThrowAccuracy`, `freeThrowConsistency`, `pressureFreeThrows` |
| `passResolution` | `passAccuracy`, `courtVision`, `passTiming` |
| `turnoverResolution` | `ballSecurity`, `pressureHandling`, `dribbleControl`, `changeOfDirection`, `decisionMaking` |
| `stealResolution` | `onBallSteal`, `passingLaneAnticipation`, `deflectionTiming`, `stripTechnique` |
| `blockResolution` | `blockTiming`, `verticalContest`, `helpSideBlocking`, `recoveryBlocking` |
| `offensiveReboundResolution` | `offensivePositioning`, `reboundPursuit`, `reboundReading`, `secondJump` |
| `defensiveReboundResolution` | `defensivePositioning`, `boxOutTechnique`, `reboundReading`, `reboundSecurity` |
| `interiorDefenseResolution` | `postContainment`, `rimDeterrence`, `helpRotation`, `paintPositioning` |
| `perimeterDefenseResolution` | `onBallContainment`, `lateralRecovery`, `screenNavigation`, `closeoutControl` |
| `fatigueResolution` | `stamina`, `recoveryRate`, `workloadCapacity`, `lateGameConditioning` |
| `physicalMatchup` | `acceleration`, `topSpeed`, `lateralQuickness`, `agility`, `lowerBodyStrength`, `upperBodyStrength`, `contactBalance`, `physicalLeverage` |
| `defensiveAwarenessRead` | `defensiveAwareness` |

Coverage: the sixteen events read exactly the 61 possession-relevant
sub-ratings (67 stored minus the six forbidden), each at least once. The
tendency-normalization formula and game-seed derivation remain §9 decisions,
recorded here when the kernel lands.

## Frozen result contract (decided by the §6 screens, 2026-07-17)

The source of truth is **`src/domain/gameResult.ts`** — the §9 kernel must
produce these types verbatim, and `assertValidGameResult` is its finalization
gate. Summary of what was frozen:

- `GameResult`: `gameId`, `seasonId`, `homeTeamId`, `awayTeamId`,
  `overtimePeriods`, `home` / `away` (`TeamPeriodScoring`), `winnerTeamId`,
  `playerLines`.
- `TeamPeriodScoring`: `teamId`, `periodPoints[]` (4 regulation entries plus
  one per overtime), `totalPoints`.
- `PlayerBoxScoreLine`: `playerId`, `teamId`, `started`, `secondsPlayed`
  (integer seconds), `fieldGoalsMade/Attempted`,
  `threePointersMade/Attempted`, `freeThrowsMade/Attempted`,
  `offensiveRebounds`, `defensiveRebounds`, `assists`, `steals`, `blocks`,
  `turnovers`, `personalFouls`, `plusMinus`, `points`, `dnpReason`
  (`'coachs_decision' | 'injury' | 'inactive' | null`; non-null exactly when
  the player did not play).
- Derived, never stored: total rebounds (OREB + DREB), shooting percentages
  (null at zero attempts, never NaN), team stat totals, four factors, top
  performers, minutes display.
- Enforced invariants (see `collectGameResultIssues`): points arithmetic per
  line; team points = player points = period points; player seconds sum to
  exactly 14,400 per team plus 1,500 per overtime; makes ≤ attempts; threes ⊆
  field goals; exactly five starters; plus/minus sums to five times the
  margin; one winner, no ties; DNP lines carry no activity.
- Reproducibility metadata (`SIMULATION_VERSION`, RNG version, derived game
  seed, input fingerprint) is **not** part of the frozen §6 shape — the §9
  kernel adds it when it exists, per the Determinism section.

Where the screens still show slots the contract cannot fill (game flow, key
moments, play-by-play, game info), those need the §14 event log or later
systems — tracked by `DEFERRED(…)` tags and the roadmap ledger, not by
widening this contract early.

The rule pack the kernel consumes is `src/domain/leagueRules.ts`
(`MILESTONE_1_LEAGUE_RULES`, `LEAGUE_RULES_VERSION = 1`), a nested contract:
4×720s quarters; 300s unlimited overtime with the 20-OT termination guard;
24-second shot clock, 14 after an offensive rebound, 8-second backcourt; 6
personal fouls, unlimited re-entry; team-foul penalty on the 5th regulation /
4th overtime team foul plus the final-2:00 single-foul rule, offensive fouls
never counting toward the bonus; shooting-foul free throws 2/3/1 and 2 in the
penalty; substitutions at dead balls only. Regulation player-minutes are
derived from the pack (`deriveRegulationTeamSeconds` = 240 minutes), never
stored. The pack defines only legality — coaching intent lives in
`RotationPlan` (§8) and actual behavior in the live rotation engine here.

## Simulation contract

The simulation is a pure TypeScript domain subsystem. It accepts validated immutable inputs plus an injected seeded random-number generator and returns a new immutable result.

```ts
interface SimulateGameInput {
  readonly game: ScheduledGame
  readonly rules: LeagueRulesV1
  readonly homeTeam: Team
  readonly awayTeam: Team
  readonly homePlayers: readonly Player[]
  readonly awayPlayers: readonly Player[]
  readonly homeRotation: RotationPlan
  readonly awayRotation: RotationPlan
}

function simulateGame(
  input: SimulateGameInput,
  random: RandomSource,
): GameResult
```

It does not read React state, the DOM, browser storage, the network, wall-clock time, locale settings, or mutable global state. It does not persist its result. The application layer validates and commits a completed result in a separate atomic operation.

The simulation directory may import domain types and the shared random module only. It must never import React. `Math.random` is forbidden anywhere under `src/simulation/`, `src/generation/`, and `src/random/`.

## Determinism

Determinism means that deeply equal validated inputs, the same simulation version, the same RNG version, and the same seed produce deeply equal domain results. Presentation timestamps, save IDs, and UI sort state are outside this contract.

Determinism depends on the following rules:

- iterate maps and records through explicitly sorted stable IDs, never incidental object-key order;
- use integer seconds for clocks and player time;
- use integer counters for statistics;
- use an integer energy scale for fatigue;
- use versioned formulas and clamp every probability;
- resolve tied choices with a stable ID before consuming randomness unless a random choice is intentional;
- derive independent labeled seeds for scheduling and each game; and
- record an input fingerprint, simulation version, RNG version, and derived game seed with every result.

Changing a formula, random call order, seed derivation, or RNG algorithm requires a new simulation or RNG version and new golden tests.

## Seeded random-number generation

### Interface

```ts
interface RandomSource {
  nextUint32(): number
  nextFloat(): number
  nextInt(maxExclusive: number): number
  chance(probability: number): boolean
  pickWeighted<T>(
    choices: readonly T[],
    weight: (choice: T) => number,
  ): T
}
```

All league-generation and simulation randomness flows through this injected interface. Tests can inject a fixed sequence to force generated-data boundaries, turnovers, fouls, misses, offensive rebounds, overtime, and other branches.

### Proposed implementation

Milestone 1 uses a versioned `xoshiro128**` implementation identified as `xoshiro128ss-v1`:

- four unsigned 32-bit state words;
- a documented versioned UTF-8 string-to-state hash;
- rejection of the all-zero state;
- `nextUint32()` as the primitive;
- `nextFloat()` equal to `nextUint32() / 2^32`, producing `[0, 1)`;
- `nextInt(maxExclusive)` using rejection sampling to avoid modulo bias; and
- weighted choice rejecting empty lists, negative/non-finite weights, and an all-zero weight set.

JavaScript bitwise operations and `Math.imul` provide consistent 32-bit behavior. `Math.random` is not used as a seed source.

The visible new-season seed is a normalized non-empty string. Independent seed labels prevent an unrelated change in schedule generation from shifting every game:

```text
league seed   = derive(rootSeed, "league/v1")
schedule seed = derive(rootSeed, "schedule/v1")
game seed     = derive(rootSeed, "game/v1/" + stableGameId)
```

Initial teams and players are generated once from the league stream and then persisted in full; save loading never regenerates them. Game simulation is atomic, so no mid-game RNG state needs to be persisted. The exact derived seed will be stored **with the result**.

> **Correction.** An earlier version of this line claimed the derived seed "is stored with the scheduled game and result." It is not: `ScheduledGame` (`src/domain/schedule.ts:359`) has no seed field, and no result type exists yet. Per [ADR 0005](adr/0005-scheduled-game-vs-game-result.md) the seed belongs to the `GameResult` aggregate, never to `ScheduledGame`. The game seed derives on demand via `deriveSeed(rootSeed, 'game/v1/<gameId>')`.

Golden-vector tests pin seed normalization, derived seeds, the first outputs of `nextUint32`, floating range, integer range, and weighted choices.

## Schedule generation

The schedule generator is pure and receives a season ID, eight validated team
IDs, a versioned rule set, a schedule seed, a timezone-free starting
`LocalDate`, and whole-calendar-day spacing. The complete generic model and
date-certainty rules are defined in `SEASON_AND_SCHEDULING.md`.

1. Sort IDs and construct the 28 canonical opponent requirements without dates.
2. Apply a seeded Fisher–Yates team permutation from its own derived label.
3. Use the circle method to produce seven base rounds of four games. Every team appears once per round and every pairing appears once.
4. Produce four cycles and reverse paired cycle orientations, giving every matchup two home games per team.
5. Vary cycle and round ordering through separately derived labeled streams.
6. Assign game days 1–28 and calendar dates from the configured spacing.
7. Derive stable schedule, game-day, and game IDs without using final array indexes as game identity.
8. Validate the complete schedule and all detectable violations before returning it.

Required output properties:

- 112 unique games;
- 28 games per team;
- exactly four games for each unordered pair;
- exactly two home and two away games per team against each opponent;
- no self-matchups;
- no team appearing twice on one game day; and
- every reference resolving to one of the eight teams.

Schedule generation consumes no browser date, wall clock, locale, or timezone.
`LocalDate` is a pure `YYYY-MM-DD` calendar value, and a game-day sequence
number remains a separate league ordering concept. Real professional-league
dates and formulas are not embedded in the engine.

## Pregame setup

Before tipoff:

1. validate teams, 12-player ownership, rules, rotations, schedule identity, and seed;
2. copy ratings/tendencies into internal immutable lookup tables;
3. place the five declared starters on court;
4. initialize every player's energy to 10,000 units and fouls/stats to zero;
5. confirm valid persisted player IDs, names, ages, positions, ratings, and team assignments;
6. initialize four regulation periods, team-foul counters, and possession state; and
7. choose the opening possession using the game RNG, with later regulation periods alternating the starting team.

If any input is invalid, simulation returns no partial game. It reports structured validation errors to the application layer.

## Time model

- All time is an integer number of seconds.
- Each live-ball segment samples a duration within rule-appropriate bounds and clamps it to the period time remaining.
- The same elapsed seconds are added to each of the five players currently on court for that team.
- Free throws and dead-ball substitutions consume no game-clock seconds in Milestone 1.
- A shot or turnover can resolve at the horn when the sampled duration equals the remaining period time.
- Team regulation player-seconds therefore equal `5 × 4 × 720 = 14,400`.
- Each overtime contributes `5 × 300 = 1,500` player-seconds per team.

Player minutes are stored as seconds and converted only for display. Rounding displayed minutes must not be used in invariant checks.

## Possession-resolution phases

Each offensive sequence advances through explicit phases. An offensive rebound or non-shooting defensive foul may loop to a new segment for the same offense; every loop has a clock, foul-count, or bounded-event progression.

### 1. Establish context

- Confirm five eligible players on each side.
- Build deterministic positional matchups from primary/secondary positions and stable-ID tie breaks.
- Read score margin, period, time remaining, team fouls, player foul trouble, energy, and current rotation deficits.
- Calculate effective ratings after fatigue; persisted ratings never change.

### 2. Select initiator and action

Select an offensive initiator using normalized weights from usage, ball handling, passing, position, and fatigue. The initiator either creates a shot for themself or passes to a teammate. Passing weights consider the initiator's pass tendency/rating and teammate shot opportunity.

At most one passer can receive an assist on a made field goal. Free throws do not receive assists.

### 3. Consume live-ball time

Sample a possession segment, normally 6–24 seconds. Late-period context permits quicker attempts. After an offensive rebound, use a maximum of 14 seconds. Clamp to the exact period remainder and credit all ten active players with the elapsed time before resolving the event.

### 4. Resolve pre-shot turnover or non-shooting foul

The turnover check occurs before shot resolution. If no turnover occurs, a bounded non-shooting foul check may interrupt the action. A defensive foul below the bonus restarts the offense at a fresh segment; a bonus foul awards two free throws. An offensive foul records a personal foul and turnover and ends the possession.

### 5. Select shot

Choose shooter and one of three shot zones: rim, midrange, or three-point. Zone weights begin with player tendencies and are adjusted for:

- the canonical zone rating (`insideScoring`, `midRangeShooting`, or `threePointShooting`);
- position and role;
- creator passing quality;
- lineup spacing;
- matched and help defense;
- fatigue;
- score and clock context; and
- a small minimum weight so a legal option is not impossible unless explicitly disabled.

Weights are normalized only after all modifiers. A player with no valid positive shot weight triggers an invariant error rather than an arbitrary fallback.

### 6. Resolve shooting foul and make/miss

Calculate a bounded shooting-foul probability. If fouled:

- a made two- or three-point shot counts and produces one additional free throw;
- a missed rim or midrange shot produces two free throws;
- a missed three-pointer produces three free throws.

Otherwise calculate make probability and draw exactly one random value for make/miss. A proposed starting calibration is:

```text
make probability =
  zone base
  + scoring-skill adjustment
  + creation/spacing adjustment
  - matchup/help-defense adjustment
  - fatigue adjustment
  + late-game context adjustment
```

Proposed zone bases are 0.56 at the rim, 0.41 from midrange, and 0.34 from three. Skill adjustments begin near `(rating - 60) × 0.004`; defense uses a smaller opposing coefficient. Final probabilities are clamped to plausible fictional-league bounds per zone. These constants are tuning inputs under `simulationVersion: 1`, not hidden player data.

On a missed field goal, block attribution is checked against the matched/help defender's `blocking` rating and the shot zone. A block is an attribution on an already missed attempt, not a second independent way to subtract a made basket.

### 7. Resolve free throws

Free-throw probability uses the shooter's `freeThrowShooting` rating and fatigue and is clamped to `[0.35, 0.97]`. Each attempt consumes one random outcome.

- Made free throws add one point to the shooter and team.
- A miss on the final free throw is reboundable.
- Earlier misses in a multi-shot trip are dead balls.
- The final made free throw changes possession.

### 8. Resolve rebound or possession change

A missed field goal or reboundable final free throw enters rebound resolution. First determine offense versus defense from lineup rebound strength, shot zone, and fatigue. Then select exactly one eligible rebounder using player-level weights.

- Offensive rebounding uses `offensiveRebounding`, position, proximity, and energy.
- Defensive rebounding uses `defensiveRebounding`, box-out help, position, and energy.
- An offensive rebound retains possession and starts a segment with a 14-second maximum.
- A defensive rebound changes possession.

Milestone 1 attributes every reboundable miss to one player; it has no separate team-rebound statistic.

### 9. Apply event, fatigue, and substitutions

Apply all stats through a box-score builder that accepts typed events. Direct arbitrary mutation of counters is not allowed. Update team fouls and foul-out status, drain/recover energy for elapsed time, then evaluate substitutions at the dead ball.

After each applied event, cheap local assertions check finite/non-negative counters and legal made/attempt relationships. Full game invariants run at period end and finalization.

## Defensive effects

Defense is represented through observable player skills rather than a single hidden team modifier:

- perimeter defense reduces three-point and perimeter-creation quality;
- interior defense reduces rim quality and increases difficult midrange outcomes;
- stealing raises live-ball turnover and steal attribution probability;
- `blocking` raises block attribution on eligible misses;
- defensive rebounding controls possession completion; and
- no separate foul-discipline rating is stored; foul likelihood remains a versioned simulation rule rather than player data.

Matchups favor natural position coverage. Help defense is a weighted contribution from the best relevant non-matched defenders, reduced when the offensive lineup has strong three-point spacing. This creates a tradeoff between rim help and leaving shooters without introducing chemistry or coaching systems.

All effects are clamped. No rating can create a negative probability or a probability above one.

## Turnovers

Turnover probability begins at a proposed 0.12 and is adjusted by:

- initiator ball handling and passing;
- offensive spacing;
- opponent perimeter defense and stealing;
- initiator fatigue;
- late-clock pressure; and
- pass versus self-created action.

The final live-ball/violation turnover probability is clamped to `[0.05, 0.26]`. A turnover is credited to exactly one offensive player.

Some turnovers are steals; others are violations, bad passes without a defender credit, or offensive fouls. A steal is credited to at most one defender and only when the opponent records a turnover. Offensive fouls also add a personal foul to the offender.

## Fouls and free throws

The foul model tracks personal fouls and defensive team fouls by period.

- Shooting-foul chance depends on shot zone, shooter draw-foul tendency, fatigue, and a versioned simulation rule; no stored foul-discipline rating is used.
- Non-shooting defensive fouls below the bonus retain possession.
- Beginning with the fifth defensive team foul in a regulation quarter, a non-shooting defensive foul produces two free throws.
- Offensive fouls are turnovers and do not count toward the defensive bonus.
- A sixth personal foul makes a player ineligible and triggers a substitution.
- Team-foul counters reset at each regulation or overtime period.
- Overtime uses the same fifth-foul bonus threshold unless a later approved rules revision says otherwise.

With 12 players, fewer than five eligible players should be unreachable under normal calibration. The approved continuation guard applies if foul disqualifications would leave fewer than five: the most recently disqualified player remains eligible, their later fouls still count, and a diagnostic flag is recorded. This avoids an invalid lineup while keeping the game deterministic.

## Substitutions and rotation minutes

Substitutions occur at dead balls. Regulation lineup selection:

1. excludes fouled-out players;
2. normally excludes zero-minute players unless an emergency substitute is required;
3. computes each player's cumulative target from planned minutes and regulation time elapsed;
4. favors players furthest below target;
5. enforces a feasible five-role positional assignment;
6. accounts for foul trouble and severe fatigue;
7. favors lineup continuity when choices are otherwise close; and
8. resolves final ties with bench priority and stable player ID.

A small deterministic assignment search is practical with only 12 players. It scores candidate five-player lineups and position assignments rather than assuming the first five array entries are valid.

The declared starters always begin regulation. Individual actual seconds may deviate from targets because changes occur only at dead balls and foul-outs take precedence. In the fourth quarter, remaining-target deficit receives extra weight so healthy players finish near their plan. The validation guarantee is the team total of 240 regulation minutes, not exact realization of every individual target.

Overtime has no editable minute allocation. It begins with the best eligible lineup based on regulation plan, bench priority, energy, foul status, and position coverage; normal dead-ball substitution checks continue.

## Fatigue

Fatigue uses integer energy units to avoid drift:

- every player starts at 10,000;
- active players lose a deterministic amount based on elapsed seconds and `endurance`;
- bench players recover a deterministic amount over the same elapsed seconds;
- period breaks add a small fixed recovery, with a larger halftime recovery;
- energy is clamped to `[0, 10_000]`; and
- effective-rating penalties begin below 7,500 and are capped.

A proposed active drain is `round(seconds × (140 - endurance) / 80)`; a proposed bench recovery is `round(seconds × 1.25)`. The effective-rating penalty is at most 12 points. Tuning tests should verify that normal rotations matter without turning late games into implausible collapse.

Fatigue resets before each game in Milestone 1. There is no cross-game condition or injury model.

## Overtime and winner guarantee

If regulation is tied, simulate complete five-minute overtime periods until one ends with different scores. Each period:

- contributes exactly 1,500 player-seconds per team;
- resets its team-foul count;
- uses eligible overtime lineups; and
- appends a period score to the box score.

To make termination a software guarantee, the engine permits at most 20 tied full overtime periods. If the twentieth is still tied, the approved deterministic emergency tiebreak event uses the injected RNG to choose an eligible free-throw shooter and resolve a recorded sudden-death free throw; if it misses, bounded attempts continue and the final bounded attempt is forced made. The made free throw belongs to a player, so team/player point equality still holds. This guard should be unreachable in normal play and must be covered by a forced-RNG test.

A game is marked completed only after final validation proves that exactly one of home or away has more points.

## Box scores and aggregation

The event builder maintains these relationships continuously:

- every made field goal also increments its attempt;
- every made three also increments three-point attempt, field-goal make, and field-goal attempt;
- every free-throw make also increments its attempt;
- player points are assigned at the same time as the scoring event;
- team points are derived by summing player points;
- a reboundable miss creates exactly one player rebound;
- an assist is attached only to a made field goal;
- a steal is attached only to an opponent turnover; and
- a block is attached only to an opponent missed field goal.

Quarter and overtime team scores are accumulated from the same scoring events. Final team scores, period totals, and player totals must agree before a result can be committed.

Season statistics are a pure fold over immutable completed box scores. Re-running aggregation does not consume randomness. Standings are a separate pure fold over the same results.

## Statistical invariants

Finalization rejects a result unless all required repository invariants hold:

- regulation player time totals exactly 240 minutes per team;
- overtime player time is exact for every overtime period;
- team points equal summed player points and period points;
- made shots never exceed attempts;
- no statistic is negative, fractional where integral, infinite, or `NaN`;
- the game has exactly one winner;
- every player line belongs to one of the two teams and every player belongs to exactly one league team;
- starters and lineups contain distinct eligible players;
- schedule references are valid; and
- a replay with identical inputs and seed is deeply equal.

Season-level validation additionally proves standings and player totals against all completed games.

## Automated testing strategy

Vitest is the primary test runner. It **is already installed** as a dev-only dependency (`vitest ^4.1.10`) with `"test": "vitest run"`; 1124 tests pass today. It is not a production dependency. Node's built-in test runner is not the plan.

Still to add when the simulation lands: a **separate** script for the longer fixed-seed simulation runs, kept out of the fast required suite so the normal loop stays quick.

### Unit tests

- RNG golden vectors, ranges, invalid arguments, and weighted selection.
- Seed normalization and labeled stream independence.
- Deterministic fictional team/player generation, age/rating/position bounds, uniqueness, and persisted-snapshot reload behavior.
- Rating, roster, rotation, and box-score validators.
- Circle schedule properties and stable game IDs.
- Shot-choice normalization and probability clamps.
- Turnover/steal, foul/free-throw, block, and rebound event accounting.
- Fatigue drain/recovery bounds.
- Lineup eligibility, positional assignment, targets, and foul-outs.
- Standings tiebreakers and season-stat zero-denominator behavior.
- Save envelope validation and each migration fixture.

### Forced-path tests

Inject a scripted `RandomSource` to force:

- made and missed twos and threes;
- assisted and unassisted makes;
- and-one, two-shot, three-shot, and bonus trips;
- offensive foul, stolen turnover, and uncredited turnover;
- block plus defensive rebound;
- offensive rebound and 14-second continuation;
- foul-out substitution and emergency eligibility;
- buzzer event, tied regulation, repeated overtime, and termination guard.

Each test asserts both the event and all affected counter relationships.

### Generative invariant tests

Using deterministic seed loops rather than unseeded property generators:

- simulate thousands of games across deliberately extreme valid rosters;
- deep-compare two runs for every input/seed pair;
- assert all per-game statistical and minute invariants;
- generate schedules for many seeds and assert the complete schedule properties;
- simulate full seasons and recompute standings/player totals from scratch; and
- serialize, parse, validate, and deep-compare save round trips.

Failures print the root seed, game ID, simulation/RNG versions, and minimal input fingerprint so they are reproducible.

### Statistical calibration tests

Fixed large seed sets can enforce broad non-flaky guardrails for fictional-league pace, scoring, shooting mix, turnovers, fouls, rebounds, and starter minutes. These are balance alarms, not substitutes for exact invariants. Bounds must be intentionally wide and updated only with a documented simulation-version decision.

### Architecture and static checks

- Fail if any file under `src/simulation/`, `src/generation/`, or `src/random/` imports `react`, `react-dom`, UI, app state, persistence, or browser modules.
- Fail if `Math.random` appears under `src/simulation/`, `src/generation/`, or `src/random/`.
- Type-check all simulation and test code with `"strict": true` explicitly enabled.
- Run automated tests, TypeScript checking, linting, and the production build after each future implementation task.
