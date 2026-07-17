# ADR 0008: Detailed player-ratings taxonomy (16 categories, 65 sub-ratings)

- Status: Accepted
- Date: 2026-07-17

This ADR is roadmap §8B step R1, **approved 2026-07-17** with the review
decisions recorded at the end of §2. The category and sub-rating names and
structure are now locked; the weights remain a V1 starting definition and will
be calibrated against the simulation before they are frozen.

## Context

Today the 16 skill categories are themselves the stored numbers
(`src/domain/ratings.ts`): each player stores 16 integers and the UI maps each to
a letter grade. There are no genuine sub-ratings. The intended experience is a
two-level model: scan 16 large letter grades, click any grade to reveal the
authoritative numeric abilities beneath it. That requires deciding, once, where
truth lives and what the exact taxonomy is — otherwise the sim, generation,
persistence, and UI each invent their own answer.

## Decision

### 1. Sub-ratings are the single source of truth

Store the 67 numeric sub-ratings (integers, 0–100). Derive everything else:

> Stored sub-ratings → derived category score → derived letter grade.

Never store both a category and its children (they could disagree). Category
scores, letter grades, offense/defense summaries, position fit, and **Overall**
are all **derived, never stored**. **Overall is display-only** (cards, quick
view) — never persisted, never read by the simulation. **Potential is removed
entirely**: not stored, not shown, not a rating.

### 2. The taxonomy — 18 categories, 67 sub-ratings

Each category's sub-rating weights total 100%. Weights are stored as basis
points / validated integer shares (never floating-point config).

**Scoring**
- *Inside Scoring* — Standing Finish 15, Driving Layup 25, Contact Finishing 25, Dunking 15, Post Finishing 20
- *Mid-Range Shooting* — Catch-and-Shoot Mid 25, Pull-Up Mid 30, Contested Mid 25, Post Fadeaway 20
- *Three-Point Shooting* — Catch-and-Shoot Three 30, Pull-Up Three 25, Movement Three 20, Contested Three 25
- *Free-Throw Shooting* — Free-Throw Accuracy 70, Free-Throw Consistency 20, Pressure Free Throws 10

**Creation**
- *Passing* — Pass Accuracy 35, Court Vision 40, Pass Timing 25
- *Ball Handling* — Dribble Control 25, Ball Security 30, Change of Direction 20, Pressure Handling 25

**Rebounding**
- *Offensive Rebounding* — Offensive Positioning 30, Rebound Pursuit 25, Rebound Reading† 25, Second Jump 20
- *Defensive Rebounding* — Defensive Positioning 25, Box-Out Technique 30, Rebound Reading† 20, Rebound Security 25

† **Rebound Reading** (reading the carom off the rim) is one skill: a single
stored field weighted into both rebounding category scores. It is the sole
documented exception to "one sub-rating, one category."

**Defense**
- *Perimeter Defense* — On-Ball Containment 30, Lateral Recovery 25, Screen Navigation 20, Closeout Control 25
- *Interior Defense* — Post Containment 25, Rim Deterrence 30, Help Rotation 25, Paint Positioning 20
- *Stealing* — On-Ball Steal 25, Passing-Lane Anticipation 30, Deflection Timing 25, Strip Technique 20
- *Blocking* — Block Timing 30, Vertical Contest 25, Help-Side Blocking 25, Recovery Blocking 20

**Physical**
- *Speed* — Acceleration 30, Top Speed 25, Lateral Quickness 25, Agility 20
- *Strength* — Lower-Body Strength 25, Upper-Body Strength 20, Contact Balance 30, Physical Leverage 25
- *Endurance* — Stamina 40, Recovery Rate 25, Workload Capacity 20, Late-Game Conditioning 15
- *Durability* — Injury Resistance 60, Load Durability 40 *(feeds the future injury system, never shot-making)*

**Mental**
- *Basketball IQ* — Offensive Awareness 35, Defensive Awareness 35, Decision-Making 30
- *Intangibles* — Competitiveness 30, Coachability 25, Composure 25, Work Ethic 20 *(feeds development, coach-fit, and morale/clutch — never the base shot/pass/rebound events)*

Total: **18 categories, 67 stored sub-ratings** (Rebound Reading is shared across
the two rebounding categories, so there are 68 display slots). Every sub-rating
belongs to exactly one category except the shared Rebound Reading; no category
references an unknown key.

**Review decisions (2026-07-17, R1 approval).** Dropped Pass Versatility and the
Mental soft traits Situational Awareness + Adaptability (no possession event
consumed them); merged Rebound Timing + Tracking into the shared **Rebound
Reading**; added a **Durability** category (injury-system-facing) and an
**Intangibles** category under Mental (development / coach-fit / morale-facing,
never shot-making). Free-Throw Consistency was kept. The two new categories are
derived and graded like the rest, but the simulation's possession events never
read Durability or Intangibles — they feed only the systems they describe, per
the "each sub-rating enters only its own situations" rule. Weights are V1
starting values pending simulation calibration.

### 3. Category score and letter grade are derived

`category score = Σ(sub-rating × weight) ÷ Σ(weight)`, computed at full
precision. The letter grade is taken from the **unrounded** score using the
existing boundaries (unchanged, from `ratings.ts`): A+ 95–100, A 90–<95, A-
85–<90, B+ 80–<85, B 75–<80, B- 70–<75, C+ 65–<70, C 60–<65, C- 55–<60, D+
50–<55, D 45–<50, D- 40–<45, F <40. Never round the score and then grade the
rounded value.

### 4. Simulation uses sub-ratings, never grades

The sim reads sub-ratings through **versioned event selectors** (driving finish,
standing finish, post attempt, catch-and-shoot three, pull-up three, pass,
turnover, rebound, fatigue, …). It never uses the letter grade and never uses the
category weighted score as a universal shortcut. **Display-category weights and
simulation-event weights have separate version numbers** — changing a UI weight
must not change a game outcome.

### 5. Deterministic generation (§8B R3)

Labeled seed hierarchy so adding a future field shifts nothing existing:
`player-quality/v1/{PlayerId}`, `player-category/v1/{PlayerId}/{CategoryKey}`,
`player-skill/v1/{PlayerId}/{SubRatingKey}`. Generated value = player-quality
baseline + category aptitude + primary-position bias (+ optional archetype bias)
+ field-specific variation, clamped to a 0–100 integer. Primary position biases
generation only, never legality. Starting calibration ranges are tuning inputs,
not frozen constants.

### 6. Archetypes are derived labels

Archetype (Floor General, Three-and-D Wing, Rim Protector, …) is a derived label
from the detailed profile, never an authoritative rating and never a simulation
shortcut.

## Compatibility and consequences

- **Snapshot bump, clean version break.** Replacing the stored 16 macro ratings
  with 65 sub-ratings changes the authoritative shape → monotonic snapshot
  version bump. Per §7 there is no migration before 1.0: old records are refused
  and a new league is generated from the detailed generator. We do not pretend
  old macro values contain detail they never had.
- The save stores: detailed skill-schema version, skill-generation version, every
  authoritative micro-rating, tendencies, identity, and the category-definition
  version. The save stores **no** grades, category scores, overall, potential,
  archetypes, or UI state.
- Restore parses the exact sub-rating record (reject missing/extra/non-integer/
  NaN/∞/out-of-range), resolves the definition version, and never regenerates.
- Grades remain presentation data, exactly as today.

## Non-goals

- Simulation event formulas (§9) and their calibration — this ADR fixes the
  taxonomy they will read, not the formulas.
- Development (§12), scouting, and template import are separate layers; this ADR
  only forbids them from becoming a second source of truth.
- No Overall-as-stored-field, no Potential rating, no real-world player data
  (the fictional-only rule stands).
