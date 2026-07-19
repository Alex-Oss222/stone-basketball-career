# Stone Basketball GM — Design Overview & Pick-Up Map

> **Status: reference / design intent + execution map.** Not the plan
> (`../ROADMAP.md` is) and not a frozen contract (code wins). This ties together
> the design corpus Alex authored (2026-07-19), records the locked decisions, and
> gives a turnkey change-list so a fresh session can pick up cold. When this
> disagrees with code, the code wins.

## 1. The corpus (all in `docs/reference/`)

| File | What it is | Key caveat |
| --- | --- | --- |
| `AI_STAFF_MASTER_SPEC.md` | Full per-team organization design: owners, GMs, head coaches (7-layer), medical, development, scouting; delegation modes; formulas | The **example people** (24 coaches, 30 GMs, …) are ILLUSTRATIVE. The reference is the *type system* (archetypes / five-axis scales / tendencies / traits / biases). Staff will be **generated** from it, not hand-authored. |
| `staff_profiles.reference.json` | The example profiles + rating scales (machine-readable) | Illustrative; "recs not end-all." Also holds the **Attribute Framework** sheet = the coded 110-attribute dictionary for the ratings rehaul. |
| `RATINGS_REHAUL.md` | The six-layer player model: measurements, 91 base ratings (26 categories), derived ratings, 16 tendencies, hidden traits, summary outputs (OVR/Potential/Availability) | The "now" work — see ADR 0009. Only the healthy structure is buildable pre-sim. |
| `SIM_ENGINE_SPEC.md` *(pending copy — engine.txt on Alex's Desktop)* | The engine design: deterministic, shot-clock-conditioned, hierarchical **semi-Markov** event simulator with competing-risk hazards, nested softmax decisions, logistic outcomes, a versioned **Model Pack**, integer/fixed-point determinism | The one true "can't": we **author** the Model Pack, we cannot statistically fit it (fictional-only, no real data). Validate against self-authored bands + relationship/metamorphic tests. |
| The player-profiles Excel (`Basketball_GM_Independent_Player_Profiles_Threshold_Draft.xlsx`, on Desktop; parsed CSVs in scratchpad) | ~138 end-state role archetypes × positions matched to the rating vector by a soft, classless, no-hard-gate threshold formula; plus the Attribute Framework | Its "Research Crosswalk" maps to NBA 2K labels → **internal only, never ships.** The role-matching engine is **deferred past the first sim**. |

## 2. The big picture (honest sequencing)

The corpus roughly triples scope beyond `ROADMAP.md` (which covers only through
the 8-team sim loop). Dependency-true order to a playable game:

1. **Ratings rehaul** (ADR 0009 / roadmap §8C) — *now*. The sim reads ratings.
2. **Rotation plans + editor** (§8/§8A, unified with the master spec's §10). The
   missing sim input. Rotation design is already complete across three docs;
   don't re-spec — unify at build (drop the wall-clock `savedAt`, integer
   seconds, one name for the planning/runtime split).
3. **Sim engine — walking skeleton** (§9) → first simulated games.
4. **Then backfill**, each its own section, almost all *downstream of* the sim +
   season loop: development/aging, injuries + medical dept, **Potential** (now
   computable), GM + front office, staff/departments, scouting, personality/
   morale, the role-matching engine, tactical scheme depth (§14).

Building the org/staff/depth first would push simming far out. Lock ratings →
build rotations → reach a game → then layer the organization.

## 3. Locked decisions (2026-07-19)

- **Full replacement**, not incremental: 18/67 → 26/91 in one **ADR 0009** that
  supersedes ADR 0008.
- **Adopt the Attribute Framework codes** as canonical identity; camelCase stays
  the code key (registry `code` field + bijection test).
- **Reserve** hidden development, hidden health, and per-rating ceilings; generate
  now only the 91 base ratings + 5 measurements + 16 tendencies.
- **Potential** reinstated as derived/scouted/display-only = **68th percentile**
  of simulated peak (Alex's tuning), *not computed until the career-sim exists*.
- **Expand tendencies to 16** now (`drawFoul` → Contact Seeking).
- **Foul Drawing** becomes a base rating *and* a tendency (ability vs frequency).
- **OVR** → 4-pillar, per-role max; **Durability → Availability** (out of OVR).
- **Defer the role-matching engine** past §9; archetype stays a derived label.
- **Versioning:** bump the 8 constants below; snapshot **4 → 5**, no migration.

## 4. Ratings rehaul — turnkey change-list

**Version bumps (one coordinated change):** `DETAILED_RATINGS_SCHEMA_VERSION`
1→2, `CATEGORY_DEFINITION_VERSION` 1→2, `DETAILED_RATING_GENERATION_VERSION`
1→2, `OVERALL_MODEL_VERSION` 1→2, `ROTATION_ABILITY_VERSION` 1→2,
`SIM_RATING_READ_VERSION` 1→2, `LEAGUE_GENERATOR_VERSION` 1→2,
`LEAGUE_SNAPSHOT_VERSION` 4→5. Seed labels `player-*/v1` → `/v2` (they
interpolate the generation version) + new labeled streams for measurements and
the reserved layers.

**Files (what changes):**
- `src/domain/detailedRatings.ts` — rewrite the registry: `SUB_RATING_KEYS`
  67→91, `DETAILED_CATEGORY_KEYS` 18→26, `DETAILED_CATEGORY_GROUPS` 6→4 pillars,
  new weights; keep shared `reboundReading`; remove the 5 now-derived keys; move
  `helpRotation`/`passingLaneAnticipation` to Defensive IQ; rename
  `loadDurability→loadTolerance`, `verticalContest→verticality`,
  `recoveryBlocking→recoveryChaseDownBlocking`; add a `code` field per sub-rating;
  add a derived-category concept for Functional Size + the derived-rating catalog.
- `src/domain/playerDerivations.ts` — rebuild OVR into the 5-step 4-pillar
  per-role-max model; add `deriveAvailability`; consume measurements → derived
  Functional Size via fixed reference μ/σ (new versioned constants).
- `src/generation/generateDetailedRatings.ts` — `POSITION_CATEGORY_BIASES` 18→26
  rows; new labeled streams for measurements / hidden dev / hidden health /
  ceilings; regenerate goldens.
- `src/domain/rotationAbility.ts` — rekey group weights 6→4 pillars; endurance→
  conditioning.
- `src/domain/simulationReads.ts` — re-derive all 16 event lists over the 91 keys;
  new events (Off-Ball Offense, Screening, Post Scoring, Off-Ball Defense, Foul
  Drawing, Shot Selection); new `FORBIDDEN_SIM_SUB_RATINGS`; re-count coverage.
- `src/domain/league.ts` — `Player` gains `measurements`, reserved hidden blocks
  (added later), and the 16-family `PlayerTendencies`.
- `src/generation/generateLeague.ts` — `createTendencies` 6→16; generate
  measurements; RNG order changes → generator version bump.
- `src/domain/leagueValidation.ts` — new closed-key/range blocks for measurements
  + widened tendencies (auto-follows the 91 keys otherwise).
- `src/persistence/leagueSnapshotTypes.ts` + `leagueSnapshot.ts` — snapshot 4→5;
  DTO + closed key lists (`PLAYER_KEYS`, `TENDENCY_KEYS`) gain measurements +
  16 tendencies; version literals → 2.
- UI: `playerPage.tsx` (26 category rows; fill measurements bio slot; add
  Potential/Availability display — the Potential *reversal*), `leagueViewModel.ts`
  (26 rows, 4-pillar grouping), `playerQuickView.tsx`/`playerSections.tsx`/
  `dashboardPages.tsx`/`rosterDepthChart.tsx`/`teamRosterFacts.ts` (consume the
  new OVR — mostly automatic).
- Docs: `docs/SIMULATION_MODEL.md` R8 table + version line → 2; **ADR 0009**
  (written); **ROADMAP.md** (§8C + Status).

**Tests to regenerate:** the detailedRatings taxonomy manifest, all
generateDetailedRatings golden vectors + distribution locks, generateLeague
goldens, playerDerivations OVR tests, simulationReadsAndAbility (selectors +
coverage + doc-agreement + architecture guard), leagueValidation, the snapshot
parse/round-trip tests. The three dev-fixture **absence tripwires must stay
green**.

## 5. Engine "freeze-before-coding" readiness

Already frozen in code: the rules pack (`leagueRules.ts`), the result contract
(`gameResult.ts` + invariants), the RNG + labeled-seed derivation
(`randomSource.ts`/`seed.ts`), and — after the rehaul — the **attribute
dictionary**. Still open (author before writing the engine): the **Model Pack**
schema + authored coefficients, the internal game/possession state-machine
schema, the atomic event alphabet + reducer, the full rules-transition graph,
lineup roles + responsibility-capacity, the intra-game event-addressed RNG
protocol, the fixed-point probability protocol, the authored calibration/target-
band spec, and the in-flight invariants. **The Model Pack + calibration are
authored, not fitted** (fictional-only).

## 6. Deferred, so nothing is lost

Development/aging (§12) · injuries + chronic health + medical dept · Potential
(derived, P68, needs the career-sim) · GM + front office · staff & departments +
the Staff-under-Teams UI · scouting (fog-of-war) · personality/morale · the
~138-profile role-matching engine · tactical scheme depth (§14) · dynamic GM/
department growth + league competitive-balance math · new person/staff entity
types. **Draft page UI: replicate `Draft page for player.png` bar-for-bar
(later).** UI refs for the rehaul: `Player page.png`, `Player Ratings 1.png`.

## 6b. Measurement generation ranges (barefoot height, by position)

Generated barefoot height stays within these per-position ranges, capped at the
top of each range (no taller). Wingspan / standing reach / weight scale from
height. These are the generation targets to retune `generateMeasurements` to
(currently keyed on position with narrower bases).

| Position | Height range |
| --- | --- |
| PG | 5'11"–6'6" (71–78") |
| SG | 6'2"–6'7" (74–79") |
| SF | 6'5"–6'9" (77–81") |
| PF | 6'7"–6'11" (79–83") |
| C | 6'9"–7'2" (81–86") |

## 6c. Position → approved-profile matching (deferred role engine, §11-ish)

The soft, classless role-matching logic (part of the deferred ~138-profile
engine — NOT built now). Captured so it isn't lost:
- Test every plausible position for the player (a 6'8" player is scored at SG /
  SF / PF); the same profile has different thresholds per position.
- Per required attribute: `progress = clamp((rating − rookieLow) / (primeTarget
  − rookieLow), 0, 1)`. Requirement weights: **Core 1.00, Support 0.60,
  Counterbalance 0.35** → weighted profile-match score.
- Soft position modifier (never a hard reject): primary position ×1.00, listed
  eligible ×0.97, adjacent compatible ×0.90, outside family ×0.82.
- Stage gates by mature-core count: Raw → Emerging (~30% signals) → Developing →
  Established (~60% mature core) → Advanced (~75%) → Complete (~85%).
- Approved primary = highest-scoring **broad** profile at the applied position
  that also meets the mature-core count (a narrow specialist scores higher on
  fewer requirements but becomes a secondary affinity, not the identity). Top
  two within 5 points → display `Transitional: A / B`. Height narrows the pool;
  ratings decide the profile.

## 6d. OVR architecture — Role Fit vs impact-based Headline OVR (Path A / Path B)

**Confirmed 2026-07-19 (Alex) — the OVR direction is settled. Three decisions:**

1. **Path A (impact-based) is *the* Headline OVR target.** The choice of path is
   closed — no longer an open "which path". The future Headline OVR is the
   with-vs-without-a-fixed-replacement impact number (below), promoted to the
   headline the moment the sim can produce it (§9 kernel; §14 depth before the
   numbers are trustworthy). Reward-peaks is then demoted to Path B.
2. **Reward-peaks is FROZEN as a *cosmetic* interim.** Before the sim, the
   headline OVR is decoration — nothing reads it (no trade, rotation, or sim
   outcome), so its imperfection costs nothing today. Leave it exactly as shipped
   (`OVERALL_MODEL_VERSION 3`, `PEAK_BLEND 0.35`). Do not re-open it.
3. **No hand-tuning to fake the target.** Do NOT add synergy/interaction bonuses
   or fudge factors to make reward-peaks reproduce the intended board before the
   sim exists. That is throwaway work the impact model deletes, and it is exactly
   the "guess the weights by feel" trap the impact approach exists to escape. If
   the interim's wrongness ever bothers us, the honest move is to show the four
   pillars + Role Fit and *hide* a single headline number — never fabricate one.

**Evidence (why the interim can't simply be tuned).** Running the shipped v3
formula on six calibrated star profiles — Shai / Jokić / Luka / Giannis /
Brunson / Cade, intended OVRs **99 / 99 / 98 / 97 / 95 / 93** — returns
reward-peaks **93 / 92 / 89 / 94 / 88 / 89**. It compresses the whole top tier
into an ~88–94 band (targets span 93–99) *and* reorders it: Giannis climbs to #1,
while Luka (intended #2) drops to 89 — level with Cade, the intended #6. The
failure is structural to pillar-averaging, not a weight that can be nudged. This
is the Bam-over-LeBron/Durant diagnosis at six-player scale; only the impact
system fixes it.

**Decided direction 2026-07-19.** The current position-weighted 4-pillar Overall
(`playerDerivations.ts`) is really a **Role Fit** score — "how well does this
player satisfy the attributes we value *at this position*" — not a cross-position
team-impact rating. It grades positions on different scales and double-counts
physical/mental (a big's defense is credited via Interior/Perimeter Defense *and*
again via Agility/Strength *and* again via Defensive IQ). That is why a balanced
two-way big (Adebayo) out-ranks lopsided-elite stars (LeBron/Durant) — a real
diagnosis, not a bug.

- **Rename the current formula → `Role Fit`.** Keep it (best position, archetype,
  system fit, positional strengths/weaknesses); do NOT use it for cross-position
  rankings.
- **Headline OVR (target, "Path A" once it works) = impact-based.** Simulate the
  player in neutral lineups with-vs-without a fixed reference player (same
  teammates/opponents/seed); `Impact = ΔOffRtg + ΔDefRtg` in **points per 100
  possessions**; `OVR = clamp(round(75 + 8·z), 0, 99)` where `z` uses a **fixed
  reference μ/σ** (never recomputed per season — same discipline as Functional
  Size). Physical/mental enter only through possession outcomes, never as separate
  pillars → no double-count. **REQUIRES the simulation** (§9 kernel; realistically
  §14 depth before the numbers are trustworthy).
- **Path A *now* = reward-peaks interim.** Until the sim exists, derive Headline
  OVR by rewarding a player's peak categories over pure averaging (stars rise,
  elite specialists beat balanced-good). It is an **interim** inside the pillar
  frame — it does NOT fix cross-position comparability or double-counting; only
  the impact system does. When impact-OVR proves out, it becomes Path A and
  reward-peaks is demoted to **Path B**.
- **Metric separation** (all distinct displays): Current / Season / Peak / Prime /
  **Potential = P68 of future simulated peak** (Alex's tuning) / **Availability**
  (already separate, out of OVR) / **Season Value = Impact × expected
  possessions**. Availability never enters Headline OVR.
- **Impact-OVR validation targets** (current ratings; sanity ranges, NEVER
  hardcoded — the ratings must *produce* them): Durant ~91, LeBron ~88, Bam ~86;
  peaks: Peak-LeBron 99, Peak-Durant ~98, Peak-Bam ~90. Current ordering:
  **Durant > LeBron > Bam** (the intended fix).
- **Functional Size display:** never a raw letter (its 50 = "average" collides
  with the letter scale's 50 = D+). Show an index + word ("53.5 — Above Average")
  or a proficiency-scale `75 + 0.8·(index − 50)` (→ LeBron 77.8, Durant 83.8, Bam
  77.6); long-term, feed height/reach/wingspan straight into the sim rather than a
  separate OVR chunk.

**Queued near-term fixes (need Alex's go — parked at checkpoint):** rename OVR →
Role Fit + add the reward-peaks interim Headline OVR (regenerate goldens);
Functional Size display fix; quick-view pin at **3s** (was 5s) with Health &
Development tabs **always present** (not pin-gated) and stickiness that holds
while the cursor stays within the player's row/section (name → stats); rename
"Trade Center" → "Trade Player".

## 7. Pick up here (next concrete step)

Begin the rehaul at its foundation: **rewrite `src/domain/detailedRatings.ts`**
to the 91-rating coded model (registry + weights + `code` field + parser +
version bumps), then work outward file-by-file per §4, regenerating each golden
as you go, keeping all four gates green. ADR 0009 is the decision of record; this
file is the map.
