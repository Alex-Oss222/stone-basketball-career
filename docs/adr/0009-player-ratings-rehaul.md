# ADR 0009: Player-ratings rehaul (26 categories, 91 base ratings, 4-pillar OVR, measurements, derived layer, potential reinstated)

- Status: Accepted
- Date: 2026-07-19
- **Supersedes ADR 0008** (the 18-category / 67-sub-rating taxonomy **and** its
  "Potential is removed entirely" decision). ADR 0008 is superseded, never
  edited.

This is roadmap **§8C** (a redo of §8B), decided 2026-07-19. It must land
**before** the §8 rotation half and §9, because the two versioned consumers the
rotation generator and the sim read — `rotationAbility.ts` and
`simulationReads.ts` — are built on the old taxonomy and must be re-derived on
the new one first.

## Context

ADR 0008 stored 67 sub-ratings in 18 derived categories. Alex has since authored
a deeper, implementation-ready player model (`docs/reference/RATINGS_REHAUL.md`)
and a coded attribute dictionary (`docs/reference/staff_profiles.reference.json`
→ the *Attribute Framework* sheet: 110 coded attribute definitions). The rehaul
is a **six-layer** model — Measurements, Base ratings, Derived ratings,
Tendencies, Hidden traits, Summary outputs — and it re-architects OVR. We do this
now, before the sim reads ratings, because changing the rating model *after* the
engine exists would mean re-pinning every simulated game.

**Fictional-only.** The Attribute Framework's codes and profile names are an
independent system. The Excel's "Research Crosswalk" (mapping to NBA 2K labels)
is internal-only and **never ships** — consistent with the standing
fictional-only rule; verified again at the §19 content audit.

## Decision

### 1. Six layers; base ratings remain the single source of truth
`Stored base ratings → derived category score → derived letter grade` (unchanged
from 0008). Category scores, grades, offense/defense summaries, position fit,
Overall, Availability, and Potential are all **derived, never stored**. **Never
store a base rating and its derived rating in the same OVR** (double-counting).

### 2. Taxonomy — 26 categories in 4 pillars, 91 base ratings
Offense 10 categories / 37 ratings, Defense 6 / 20 (unique; Rebound Reading
shared), Physical 6 / 17, Mental 4 / 17. The exhaustive category/sub-rating
weights are in `docs/reference/RATINGS_REHAUL.md` and the Attribute Framework
(V2 **starting** weights, pending simulation calibration — not frozen). **Rebound
Reading stays one stored field** shared across both rebounding categories (91
unique keys, 92 display slots).

**Attribute codes are the canonical stable identity** (`OFF_RIM_STANDING_FINISH`,
`DEF_PERIM_ONBALL_CONTAINMENT`, …) — the thing docs and the future role profiles
threshold on. In code, keep **camelCase keys** as the persisted record keys and
the `SubRatingKey` union, with a registry `code` field enforcing a camelCase↔code
bijection (a test asserts it). Do **not** use SCREAMING_SNAKE strings as object
keys.

### 3. Five stored fields become derived; two move
`pressureFreeThrows`, `pressureHandling`, `rimDeterrence`, `physicalLeverage`,
`lateGameConditioning` leave the stored set and become **derived selectors** (per
RATINGS_REHAUL §6/§13), joined by the rest of the derived catalog (Speed-with-Ball,
Shot Creation, Passing-Lane Threat, Off/Def Rebound Impact, Transition Off/Def).
`helpRotation` and `passingLaneAnticipation` move into **Defensive IQ**.

### 4. Measurements are a separate stored layer
Store 5 raw integer measurements (Height, Weight, Wingspan, Standing Reach, Hand
Size). **Functional Size** is derived from z-scored measurements using **fixed
reference means/SDs** (a versioned constant set, never recomputed per season).
Measurements are soft fit only — never a hard gate, never averaged into Strength.

### 5. OVR re-architected — 4 pillars, per-role max
`sub-ratings → 26 category scores → position-adjusted Offense/Defense/Physical/
Mental pillar scores (Physical includes derived Functional Size, excludes
Durability) → per-role pillar-weighted OVR → OVR = round(max over eligible
roles)`. OVR stays **display-only, never read by the sim**. **Durability leaves
OVR** and becomes a separate **Availability** grade = 0.55·InjuryResistance +
0.45·LoadTolerance, shown but never in OVR.

### 6. Tendencies expand to 16 families
From today's 6 to the 16 families (RATINGS_REHAUL §7). Tendencies **never raise
OVR** and are never read as rating factors. `rim / midrange / threePoint` stay
independent 0–100 values (they do not sum to 100) — they are the §9
tendency-normalization inputs. `drawFoul` is renamed to the **Contact Seeking**
family.

### 7. Reserved layers — generated later, not now
Generate **now**: the 91 base ratings, the 5 measurements, the 16 tendencies.
**Reserve** (added by a later monotonic bump, when their systems exist): the 5
hidden Development traits (Work Ethic, Coachability, Adaptability, Learning
Capacity, Professionalism → §12 development), the 8 hidden Health values → the
medical system, and per-rating hidden ceilings → Potential. The labeled
seed-hierarchy guarantees adding these later shifts no existing draw.

### 8. Potential reinstated (reverses ADR 0008 §1)
Potential is a **derived, scouted, display-only** estimate = the **68th
percentile** of peak OVR over ~300 simulated careers (Alex's tuning: 68th, not
75th). It is **not stored, not shown, and not computed** until the
development/career-sim system exists (§12+). When it arrives it is shown as a
grade + confidence band (true + scouting error), never the hidden true number,
and it **never drives development**.

### 9. Foul Drawing split into ability + tendency
Add **Foul Drawing** as a base rating under Rim Finishing (how *well*); keep a
frequency **Contact Seeking** tendency (how *often*, the renamed `drawFoul`).

### 10. Simulation reads re-frozen over the 91 keys
Re-derive the event selectors for the new taxonomy. Offensive IQ and Defensive IQ
sub-ratings **do** enter possession events. New events for Off-Ball Offense,
Screening, Post Scoring, Off-Ball Defense, Foul Drawing, Shot Selection. New
`FORBIDDEN_SIM_SUB_RATINGS` = Durability (→ Availability only), the hidden
Development traits (now outside the 91), and the Team & Leadership / development-
facing Competitive Makeup ratings that feed morale/development, not shot-making.
Tendencies stay outside the rating reads. Display-weight versions and the
sim-read version stay independent (a UI reweight can never change a game).

### 11. Role/profile matching engine deferred
The ~138-profile role-matching system (the Excel's Profile Thresholds) is a
**derived label layer**, deferred **past the first sim** (§9). Archetype/role
stays a pure function of the profile, never stored, never a sim shortcut
(unchanged from ADR 0008 §6). When built it thresholds on the attribute codes.

## Version bumps (one coordinated change)
- `DETAILED_RATINGS_SCHEMA_VERSION` 1 → 2 (stored shape 67 → 91 + new layers)
- `CATEGORY_DEFINITION_VERSION` 1 → 2 (18 → 26 categories, 6 → 4 groups, weights)
- `DETAILED_RATING_GENERATION_VERSION` 1 → 2 (key set, seed labels v1→v2, RNG order, new generated layers)
- `OVERALL_MODEL_VERSION` 1 → 2 (4-pillar per-role-max)
- `ROTATION_ABILITY_VERSION` 1 → 2 (group weights rekeyed 6 → 4 pillars, endurance→conditioning)
- `SIM_RATING_READ_VERSION` 1 → 2 (event lists renamed/added; forbidden set + coverage count change)
- `LEAGUE_GENERATOR_VERSION` 1 → 2 (tendencies 6 → 16 + measurements/reserved-stream generation)
- `LEAGUE_SNAPSHOT_VERSION` 4 → 5 (monotonic, clean break, coordinate with §8's planned 5 / §10's 6)

## Compatibility and consequences
- **Clean version break, no migration** (§7). Old v4 records are refused and offer
  "start a new league." We do not pretend old values contain the new detail.
- The save stores the 91 base ratings, measurements, 16 tendencies, identity, and
  the schema/definition/generation versions. It stores **no** grades, category
  scores, overall, availability, potential, archetypes, derived ratings, or UI
  state. Reserved hidden layers are added by a future bump, not stored as nulls
  (the closed parser rejects extra keys).
- Every golden vector and the independent taxonomy manifest are regenerated.

## Non-goals
- §9 simulation formulas and the authored **Model Pack** coefficients — the sim
  environment must be *authored*, not statistically fit (fictional-only, no real
  data). This ADR fixes the taxonomy the sim reads, not its math.
- Development (§12), injury/medical, scouting, personality/morale, and the
  role-matching engine — separate later layers; this ADR only reserves their data
  and forbids them from becoming a second source of truth.
