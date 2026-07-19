# Basketball GM AI Master Specification

## Purpose

This document is the authoritative, game-ready specification for a basketball general-manager simulation. It replaces the original research-heavy draft with enforceable rules, structured systems, formulas, generation libraries, and preserved fictional profiles.

Use the companion `basketball_gm_profiles.json` when the simulation needs machine-readable profile data.

## 1. Non-negotiable AI rules

1. **Never reduce a coach, executive, scout, doctor, or developer to one overall rating.** Use separate abilities, tendencies, specialties, relationships, history, and contextual fit.
2. **Ability and preference are different.** A person may strongly prefer a system they are only average at teaching or executing.
3. **Fit is contextual.** The same staff member can be excellent for one roster and poor for another.
4. **Staff influence decisions and execution; they do not give magical flat bonuses.** A coach changes pace, actions, coverages, roles, lineups, and teaching. A scout changes information quality. A doctor changes assessment and rehabilitation quality. A GM changes decisions.
5. **Player talent remains the strongest on-court force.** Great staff can improve usage, fit, preparation, availability, and development but cannot routinely make a weak roster superior to an elite roster.
6. **Development and health outcomes remain probabilistic.** Staff alter expected outcomes and avoidable errors; they never guarantee growth or recovery.
7. **The human and AI use the same rules.** AI teams do not see true ratings, true potential, future progression, exact health outcomes, or private user information.
8. **Important information contains uncertainty.** Show ranges, confidence, disagreement, freshness, and reasons.
9. **Every strong strategy must have a cost, counter, personnel requirement, or relationship risk.**
10. **AI decisions must be explainable.** Every major performance change, hire, firing, draft pick, trade, medical restriction, and development outcome needs a readable reason.
11. **Depth is optional.** Each major responsibility supports `AUTO`, `RECOMMEND`, or `MANUAL`.
12. **User-saved rotation plans are protected.** Coach personality may organize stints and lineups but may not silently rewrite a valid user plan.

## 2. Organization and authority

```text
OWNER / GOVERNOR
Sets budget, patience, expectations, and organizational pressure

GENERAL MANAGER / PRESIDENT
Acquires and retains players; hires department leaders; controls contracts,
drafts, trades, free agency, roster construction, and organizational direction

SCOUTING DEPARTMENT
Finds, evaluates, projects, and reports under uncertainty

HEAD COACH
Controls tactics, roles, lineups, rotations, substitutions, and game plans

COACHING & PLAYER DEVELOPMENT DEPARTMENT
Teaches skills, decisions, roles, and game transfer

MEDICAL / HEALTH & PERFORMANCE DEPARTMENT
Diagnoses, treats, rehabilitates, sets medical restrictions, and clears participation
```

### Hard authority rules

| Decision | Primary authority | Hard rule |
|---|---|---|
| Diagnose injury | Medical department | Coach and GM cannot change the diagnosis |
| Clear practice or games | Medical department | An uncleared player cannot participate in authentic mode |
| Set maximum workload/minutes | Medical department | Coach may use less, never more |
| Select active roster and actual minutes | Coach/GM | Must remain within medical limits |
| Design rehabilitation | Medical/rehabilitation staff | Coaching supplies basketball context |
| Set development focus | Development department with player and coach input | Must respect medical restrictions |
| Assign tactical role and game opportunities | Head coach | Development staff cannot force game usage |
| Draft, trade, sign, waive, extend | GM | Uses scouting, analytics, coaching, development, and medical input |
| Clinical mental-health treatment | Licensed clinician | Private information is protected |
| Opponent report | Advance scouting | Coaching staff chooses the counter |

## 3. Complexity and delegation

| Mode | Staff depth | User burden |
|---|---|---|
| **Off** | Neutral league-standard staff effects | Pure roster simulation |
| **Lite** | One leader per department | Hire leaders and set broad priorities |
| **Standard — default** | Head coach; offensive/defensive/development leads; medical director/trainer/rehab/science; scouting directors | A few meaningful offseason and exception decisions |
| **Full** | Position coaches, analysts, specialists, regional scouts, wellness, nutrition, affiliate staff, assistant executives | Detailed department management |

Every responsibility can be set to:

```text
AUTO       Staff handles it
RECOMMEND  Staff proposes; user approves
MANUAL     User controls it
```

## 4. Shared modeling framework

### 4.1 Internal and public ratings

Internal abilities use `0–100`. The normal interface uses bands:

```text
Poor
Below Average
Average
Good
Excellent
Elite
```

Scouted or unfamiliar staff and players appear as ranges, such as `Good–Excellent`, plus confidence. Exact values are reserved for commissioner/editor mode.

### 4.2 Separate layers

Every staff profile should independently contain:

```text
Identity and career history
Core abilities
Tendencies and philosophy
Adaptability
Leadership / communication
Specialties and traits
Relationships
Contract and job preferences
Reputation, ambition, loyalty, ego, burnout risk
Contextual fit
```

### 4.3 Relationships and cohesion

Track two-way relationships among:

```text
Owner ↔ GM
GM ↔ Head Coach
GM ↔ Department Leaders
Head Coach ↔ Assistants
Coach ↔ Player
Medical Staff ↔ Player
Development Staff ↔ Player
Staff ↔ Staff
GM ↔ Other GMs / Agents
```

Staff cohesion comes from tactical agreement, communication, role clarity, prior relationships, ambition, ego, loyalty, and promotion history. Cohesion should affect installation, coordination, and retention only within tight bounds.

### 4.4 Familiarity

Track familiarity separately for:

```text
Offensive system
Defensive system
Rotation structure
Player role
Specific lineup
Coach-player relationship
Staff cohesion
```

Familiarity rises through stable practice, games, training camp, returning personnel, and prior experience. It falls through staff changes, system changes, roster turnover, injuries, and repeated role changes.

### 4.5 Context-adjusted evaluation

Do not judge staff only by raw wins, injuries, shooting percentages, or prospect outcomes. Compare actual outcomes with roster talent, age, health, role, opportunity, inherited assets, schedule, uncertainty, and reasonable expectations.

### 4.6 Required explanation trace

For any material AI decision, store an internal trace:

```text
Current organizational state
Relevant evidence and confidence
Options considered
Fit and relationship effects
Short-, near-, and long-term consequences
Financial / health / workload effects
Alternative offers or candidates
Bias and personality adjustments
Final reason
```

The user sees a concise version; developers can inspect the full trace.


## 5. Head-coach system

### 5.1 Public pillars

| Pillar | Meaning |
|---|---|
| **Tactics** | Offensive and defensive design, planning, adjustments, rotations, endgame decisions |
| **Teaching** | Skill, role, practice, and concept instruction |
| **Leadership** | Communication, motivation, accountability, trust, and conflict management |
| **Adaptability** | Changing systems, roles, and plans without losing effectiveness |
| **Organization** | Preparation, delegation, staff management, workload, and long-term planning |

Do not average these into an overall coach score.

### 5.2 Required coach attributes

```text
Tactical:
offensiveDesign, defensiveDesign, gamePlanning, inGameAdjustments,
rotationManagement, endgameManagement, opponentScoutingUse, riskJudgment

Teaching:
offensiveTeaching, defensiveTeaching, skillDevelopment, roleConversion,
youthDevelopment, veteranMaintenance, feedbackQuality, talentEvaluation

Leadership:
communication, motivation, accountability, relationshipManagement,
starManagement, benchManagement, conflictResolution, mediaHandling

Organization:
staffManagement, preparation, workEthic, composure, adaptability,
innovation, resourceManagement
```

### 5.3 Coach profile structure

```json
{
  "identity": {},
  "abilities": {},
  "offense": {},
  "defense": {},
  "rotation": {},
  "leadership": {},
  "development": {},
  "traits": [],
  "hidden": {},
  "career": {},
  "contract": {}
}
```

The profile must contain machine-readable values. Biography text explains the values but never drives the simulation directly.

### 5.4 Philosophy and trait libraries


Each package should modify **decisions and tendencies**, not hand out a blanket offense bonus.

| Offensive identity                  | Core behavior                                                                                    | Ideal personnel                                                     | Built-in cost                                                                        |
| ----------------------------------- | ------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| **1. Five-Out Read-and-React**      | Pulls all five defenders away from the rim; emphasizes reads, drives, kicks, and quick decisions | Five credible shooters, mobile center, multiple passers             | Weak offensive rebounding, difficult fit for non-shooting bigs, high learning demand |
| **2. Pace-and-Space Accelerator**   | Runs after makes and misses, takes early threes, attacks before defenses organize                | Athletic guards, depth, shooting, fast decision-makers              | Turnovers, fatigue, defensive-balance problems, high game-to-game variance           |
| **3. Pick-and-Roll Engine**         | Heavy high-screen usage with specialized ball-handler, roller, and weak-side spacing roles       | Elite creator, strong screener, shooting around the action          | Can become predictable; vulnerable to traps, switches, and poor secondary creation   |
| **4. Motion and Handoff Offense**   | Cuts, dribble handoffs, screening chains, and player movement                                    | High-IQ passers, versatile wings, mobile bigs                       | Slow installation; turnovers rise when decision-making is weak                       |
| **5. Heliocentric Star System**     | Concentrates creation and possessions around one elite player                                    | Durable superstar creator and low-usage complementary players       | Star fatigue and injury dependence; role-player morale and development can suffer    |
| **6. Elbow Hub / Princeton**        | Uses a passing big or forward at the elbow with cuts, backdoors, and split actions               | Passing center, smart cutters, patient guards                       | Can become slow and cramped without shooting; requires strong awareness              |
| **7. Post Hub Traditionalist**      | Establishes deep post position, forces doubles, uses split cuts and inside-out passing           | Skilled post scorer, shooting, offensive rebounders                 | Lower pace and three-point rate; poor post players waste possessions                 |
| **8. Rim Pressure Attack**          | Drives, cuts, transition attacks, and aggressive closeout exploitation                           | Fast guards, finishers, vertical threats                            | Spacing dependency, blocked shots, offensive fouls, physical fatigue                 |
| **9. Bombs-Away Perimeter Offense** | Maximizes three-point attempts and rapid drive-and-kick decisions                                | High-volume shooters and offensive rebounding support               | High variance; poor shooters become destructive; weak foul generation                |
| **10. Midrange Matchup Artist**     | Hunts mismatches and comfortable pull-up areas, especially late in games                         | Skilled shot creators and screening versatility                     | Lower average shot value; can devolve into stagnant isolation                        |
| **11. Offensive Glass Pressure**    | Sends multiple players to the boards and creates second chances                                  | Size, strength, rebounding wings, energetic bench                   | Exposes transition defense and increases fatigue                                     |
| **12. Bench-Wave Tempo**            | Uses frequent substitutions and full-speed second units                                          | Ten or eleven playable players with varied skills                   | Fewer minutes for stars; lineup continuity and role satisfaction can suffer          |
| **13. Deliberate Control Offense**  | Reduces possessions, protects the ball, executes organized half-court sets                       | Experienced ball handlers, half-court creators, disciplined players | Harder to erase deficits; opponents face fewer possessions but so does the user      |
| **14. Balanced Adaptive Offense**   | Uses the strongest actions available to the current roster                                       | Versatile roster and adaptable players                              | Lower maximum system mastery; no singular overwhelming identity                      |

---

| Defensive identity               | Core behavior                                                                   | Ideal personnel                                       | Built-in cost                                                            |
| -------------------------------- | ------------------------------------------------------------------------------- | ----------------------------------------------------- | ------------------------------------------------------------------------ |
| **1. Switch Everything**         | Switches most screens and keeps the ball in front                               | Versatile wings, mobile centers, strong rebounders    | Size mismatches, offensive rebounds, post seals, foul risk               |
| **2. Drop-Coverage Fortress**    | Keeps the big near the rim while guards chase over screens                      | Elite rim protector and strong point-of-attack guards | Pull-up jumpers, pick-and-pop bigs, and skilled pocket passers           |
| **3. Blitz and Recover**         | Traps ball handlers and rotates aggressively behind the play                    | Speed, length, anticipation, deep rotation            | Short-roll playmaking, corner threes, fouls, and broken rotations        |
| **4. No-Middle Defense**         | Forces ball handlers toward sidelines and baseline help                         | Disciplined wings and coordinated back-line help      | Baseline cuts, corner spacing, and unfamiliarity penalties               |
| **5. Perimeter Denial**          | Top-locks shooters, fights over screens, and prioritizes three-point prevention | Quick guards and mobile bigs                          | Backcuts, rim attempts, and fatigue                                      |
| **6. Paint Pack**                | Shrinks the floor and dares weaker shooters                                     | Size, defensive rebounding, strong closeouts          | Open threes when scouting or rotations are poor                          |
| **7. Zone Shape-Shifter**        | Changes between zone structures and disguised matchups                          | Length, communication, strong defensive IQ            | Offensive rebounds, overloads, shooter identification, installation time |
| **8. Turnover Hunt**             | Aggressive passing-lane attacks, digs, doubles, and ball pressure               | Fast guards, depth, transition finishers              | Fouls, gambling mistakes, open rim attempts, high variance               |
| **9. Conservative Contain**      | Limits fouls, transition chances, and defensive breakdowns                      | Solid positional defenders and rebounders             | Generates few turnovers and may allow comfortable shot creation          |
| **10. Small-Ball Scramble**      | Uses speed, switches, stunts, and rapid recovery                                | Athletic wings and a strong team rebound concept      | Rim protection and defensive rebounding                                  |
| **11. Big Front Wall**           | Uses size to control the rim, glass, and post                                   | Two mobile bigs or oversized forwards                 | Transition speed, perimeter coverage, and floor-spacing matchups         |
| **12. Matchup Adaptive Defense** | Selects coverages according to opponent and lineup                              | Versatile defenders and excellent scouting            | Lower base familiarity and more communication demands                    |

---

| Rotation style                   | Behavior                                                  | Strength                                | Cost                                                   |
| -------------------------------- | --------------------------------------------------------- | --------------------------------------- | ------------------------------------------------------ |
| **Short-Leash Playoff Rotation** | Eight or nine players; heavy starter minutes              | Maximizes best-player time              | Fatigue, injury exposure, bench dissatisfaction        |
| **Deep-Wave Rotation**           | Ten or eleven players with frequent substitutions         | Pace, energy, development opportunities | Less star time and weaker lineup continuity            |
| **Continuity Loyalist**          | Stable roles and predictable substitutions                | Cohesion and role clarity               | Slow reactions to declining or mismatched players      |
| **Matchup Chess**                | Changes starters, closing groups, and minutes by opponent | High tactical ceiling                   | Uncertainty, morale problems, lower familiarity        |
| **Hot-Hand Manager**             | Extends productive stretches and shortens poor ones       | Responsive to games                     | Can overreact to random shooting variance              |
| **Youth Trial Rotation**         | Gives prospects meaningful developmental minutes          | Accelerates evaluation and experience   | Sacrifices some immediate wins                         |
| **Load Manager**                 | Protects players from fatigue and accumulated workload    | Better long-term availability           | Fewer star minutes and possible player/fan frustration |
| **Star Staggerer**               | Ensures at least one primary creator is usually on court  | Stabilizes bench offense                | Complex rotations and potential star-minute imbalance  |

---

Leadership should create compatibility—not a universal morale bonus.

| Leadership identity          | Positive behavior                                                    | Failure mode                                                    |
| ---------------------------- | -------------------------------------------------------------------- | --------------------------------------------------------------- |
| **Players’ Coach**           | Builds trust, protects players publicly, and maintains morale        | May delay discipline or avoid difficult role changes            |
| **Accountability Hardliner** | Demands execution, effort, punctuality, and role discipline          | Fragile, low-autonomy, or veteran stars may rebel               |
| **Teacher-Explainer**        | Gives reasons, clear expectations, and detailed feedback             | Can overload players and spend too long installing concepts     |
| **Star Whisperer**           | Handles status, usage, public pressure, and ego effectively          | Bench and developmental players may feel secondary              |
| **Democratic Collaborator**  | Seeks player input and allows veteran ownership                      | Slow decisions and weaker control during conflict               |
| **CEO Delegator**            | Empowers assistants and organizes responsibilities well              | Performance depends heavily on assistant quality                |
| **Calm Stabilizer**          | Prevents panic during slumps and reduces emotional volatility        | May lack urgency or competitive edge                            |
| **Culture Rebuilder**        | Establishes standards and reshapes a damaged locker room             | Initial resistance, turnover, and slower short-term performance |
| **Competitive Firebrand**    | Raises intensity, edge, and emotional engagement                     | Burnout, technical fouls, public conflict, and volatility       |
| **Scheme Evangelist**        | Creates strong commitment and rapid mastery among compatible players | Poor fit players become alienated; tactical rigidity increases  |

The autonomy–competence–relatedness framework is useful here. For example, a democratic coach supports autonomy; a teacher supports competence; a players’ coach supports relatedness. Different players can need different combinations rather than one leadership style being universally superior.

---

| Development identity    | Best use                                                               | Limitation                                         |
| ----------------------- | ---------------------------------------------------------------------- | -------------------------------------------------- |
| **Youth Accelerator**   | Broad development of inexperienced players                             | Less useful to veteran contenders                  |
| **Guard Guru**          | Ball handling, passing, pull-up shooting, pick-and-roll reads          | Limited effect on big-man skills                   |
| **Wing Laboratory**     | Shooting, secondary playmaking, cutting, switch defense                | Slow results for highly specialized players        |
| **Big Builder**         | Screening, finishing, rebounding, post defense, passing hubs           | Less value to small-ball rosters                   |
| **Shooting Laboratory** | Mechanics, shot selection, footwork, and role confidence               | Does not turn every poor shooter into a good one   |
| **Defensive Academy**   | Positioning, rotations, screen navigation, and communication           | Offensive growth receives less attention           |
| **Role Converter**      | Changes positions and turns mismatched players into useful specialists | Higher bust risk and temporary performance decline |
| **Veteran Maintainer**  | Preserves execution, conditioning habits, and role acceptance          | Limited ceiling growth                             |
| **Floor Raiser**        | Converts raw players into dependable rotation pieces                   | Fewer dramatic superstar leaps                     |
| **Ceiling Chaser**      | Takes difficult developmental bets and expands player responsibilities | More failed experiments and volatile outcomes      |

---

Background should influence reputation, contacts, knowledge, and initial opportunity—not automatically determine coaching ability.

| Background                        | Likely initial qualities                                         | Possible weakness                                   |
| --------------------------------- | ---------------------------------------------------------------- | --------------------------------------------------- |
| **Former Superstar**              | Immediate respect, star relationships, media reputation          | Entitlement, limited patience with marginal players |
| **Former Role Player**            | Role empathy, locker-room understanding, practical teaching      | Lower initial reputation                            |
| **Video Coordinator / Analyst**   | Game planning, scouting, tactical innovation                     | Limited leadership or public presence               |
| **Player Development Specialist** | Teaching, patience, individualized plans                         | Inexperienced endgame management                    |
| **International Tactician**       | Varied schemes, adaptability, player-role creativity             | Cultural or league-adjustment period                |
| **Defensive Assistant**           | Coverage detail, accountability, preparation                     | Limited offensive design experience                 |
| **College Teacher**               | Development, recruitment-style relationships, system instruction | Adjustment to professional star power               |
| **Executive / CEO Coach**         | Staff construction, delegation, organizational alignment         | Relies heavily on coordinators for tactics          |

With 14 offensive packages, 12 defenses, eight rotation policies, ten leadership types, ten development specialties, and eight backgrounds, the system already supports **1,075,200 base combinations** before ratings, traits, ages, histories, ambitions, and relationships are generated.

---

Traits should be scarce. Most coaches should have two to four. Every strong trait should create a cost, condition, or behavioral commitment.

| Trait                       | Benefit                                                        | Cost or condition                                       |
| --------------------------- | -------------------------------------------------------------- | ------------------------------------------------------- |
| **After-Timeout Designer**  | Better quality of first possession after a timeout             | Small situational impact; consumes preparation focus    |
| **Playoff Tinkerer**        | Learns opponent patterns faster across a series                | Experiments more during the regular season              |
| **Rotation Loyalist**       | Strong role clarity and lineup familiarity                     | Keeps struggling veterans in roles too long             |
| **Quick Hook**              | Removes poor performers rapidly                                | Players become anxious about mistakes                   |
| **Rookie Trust**            | Gives young players meaningful responsibility                  | More short-term errors                                  |
| **Veteran Trust**           | Experienced players respond positively                         | Prospects struggle to earn minutes                      |
| **Small-Lineup Architect**  | Improves spacing, switching, and tempo with small groups       | Rebounding and rim defense suffer                       |
| **Twin-Tower Believer**     | Maximizes interior size and rebounding                         | Vulnerable to speed and spacing                         |
| **Corner-Three Hunter**     | Creates additional corner attempts                             | More predictable weak-side positioning                  |
| **Rim Protector Whisperer** | Improves positioning and scheme fit for defensive centers      | Defense becomes dependent on one anchor                 |
| **Foul Discipline**         | Reduces unnecessary fouls                                      | Less aggressive turnover pressure                       |
| **Comeback Gambler**        | Uses pressing, trapping, and high-variance offense when behind | Can turn small deficits into blowouts                   |
| **Lead Protector**          | Slows pace and protects possessions with a late lead           | Can become overly passive                               |
| **Public Shield**           | Protects player morale during criticism                        | Ownership may believe the coach avoids accountability   |
| **Tough Love**              | High-work-ethic players improve accountability                 | Sensitive or low-trust players deteriorate              |
| **Assistant Incubator**     | Assistants develop faster and become head-coach candidates     | Staff is frequently hired away                          |
| **Scheme Converter**        | Changes player roles more successfully                         | Early performance drops while conversions are learned   |
| **Film-Room Obsessive**     | Better opponent preparation and recognition                    | Practice intensity or player freshness may decline      |
| **Practice Minimalist**     | Preserves energy and player goodwill                           | Young-player teaching and system installation slow down |
| **Health Conservative**     | Reduces return-to-play and fatigue risks                       | More rest games and lower short-term availability       |
| **Experimentalist**         | Finds unusual lineups and counters                             | Greater variance and lower initial familiarity          |
| **Contract Recruiter**      | Helps attract or retain compatible players                     | May promise roles the roster cannot sustain             |
| **Emotional Thermostat**    | Stabilizes team morale during streaks                          | Less capable of producing sudden emotional surges       |
| **Pressure Cooker**         | Raises urgency in important games                              | Burnout and conflict increase over long seasons         |

---

### 5.5 How coaches affect games

The largest coach effect is **decision selection**, not direct rating inflation.

**Possession and action selection**

- Pace and transition rate.
- Shot-location distribution.
- Pick-and-roll, handoff, post, isolation, cutting, and screening frequency.
- Offensive initiator and star-usage concentration.
- Offensive-rebound commitment and passing risk.
- Defensive coverage, help, switching, zone, double teams, foul and turnover risk.
- Lineups, substitutions, staggering, and closing groups.

**Execution**

- Spacing accuracy.
- Screen and cut timing.
- Defensive rotation and communication.
- Set-play execution.
- Adjustment speed.
- Late-game organization.

**Development and relationships**

- Direction and probability of improvement.
- Role learning and system installation.
- Feedback quality.
- Trust, role acceptance, retention, trade requests, and free-agent attraction.

A coach does not directly add shooting points to a player.

### 5.6 Core coaching formulas

Use these as tuning baselines, not real-world effect claims.

```text
n(x) = (x - 50) / 50
```

**Scheme adherence**

```text
adherence =
  clamp(0.15, 0.90,
    0.45
    + 0.15*n(coachLeadership)
    + 0.15*n(teamFamiliarity)
    + 0.15*n(avgPlayerRelationship)
    + 0.10*n(staffCohesion)
  )

executedTendency =
  rosterNaturalTendency
  + adherence * (coachTargetTendency - rosterNaturalTendency)
```

**Bounded direct execution effect**

```text
executionPPP =
  clamp(-0.025, +0.025,
    0.008*n(gamePlanning)
    + 0.007*n(inGameAdjustments)
    + 0.005*n(relevantTeaching)
    + 0.007*n(rosterFit)
    + 0.004*n(staffCohesion)
    - 0.004*n(fatigueMismatch)
  )
```

The extreme cap equals ±2.5 points per 100 possessions. Most effects should be far smaller.

**Development multiplier**

```text
growthMultiplier =
  clamp(0.88, 1.12,
    1.00
    + 0.05*n(coachTeaching)
    + 0.04*n(specialtyFit)
    + 0.03*n(playerRelationship)
    - 0.04*n(coachingInstability)
  )
```

Apply this to expected development, not directly to ratings.

**Staff responsibility weights**

```text
Offensive planning:
Head coach 55%
Lead offensive assistant 30%
Other assistants 15%

Defensive planning:
Head coach 55%
Lead defensive assistant 30%
Other assistants 15%

Development:
Development director 45%
Relevant specialist 30%
Head coach 15%
Other staff 10%
```

Use diminishing returns when specialties overlap.

### 5.7 Roster fit

Calculate separate offensive, defensive, personality, timeline, and staff-support fit.

```text
Offense:
shooting, decision-making, primary/secondary creation, screening,
roll/pop skill, frontcourt passing, transition speed, finishing,
offensive rebounding, versatility, turnover resistance

Defense:
point-of-attack defense, screen navigation, rim protection,
switchability, recovery speed, awareness, rebounding, size,
foul discipline, communication, stamina

Personality:
autonomy preference, criticism response, role clarity need,
competitive intensity, ego/status, work ethic, patience,
learning preference, loyalty, veteran/prospect status
```

Show a label and reasons, not only a number:

```text
Moderate Fit
Supports: four shooters; mobile center; two secondary passers
Conflicts: weak switch defender; turnover-prone bench; two veterans dislike variable roles
Installation: offense 35–50 games; defense 20–35 games
Early volatility: High
```

### 5.8 In-game adjustment behavior

The coach must observe evidence before changing strategy. Model:

```text
adjustmentThreshold
evidenceRequired
riskTolerance
changeMagnitude
reversalTolerance
matchupFocus
starTargeting
timeoutIntervention
```

Adjustment ability controls detection speed, causal diagnosis, counter quality, disruption to familiarity, and whether the coach abandons the change too quickly. Adjustments must visibly alter coverages, matchups, pace, shot emphasis, rotation, initiator, or closing lineup—never provide a mysterious fourth-quarter boost.

### 5.9 Career, hiring, and firing

Track prior teams, roles, mentors, assistants, protégés, records, expected-versus-actual results, style by season, player-development successes, awards, firings, and reasons.

Coaches improve from responsibilities actually performed, mentors, repetitions, playoff exposure, successes, mistakes, work ethic, ambition, age, and burnout. Former players may enter coaching, but playing ability does not equal coaching ability.

Hiring considers:

```text
rosterFit, timelineFit, tacticalNeed, leadershipFit, developmentFit,
staffNetwork, reputation, ownerPreference, affordability, autonomy demands
```

Firing considers expectation gap, trend, playoffs, locker room, development, owner/GM relationships, reputation, tenure, buyout, and injury context. Avoid random short-term churn.

### 5.10 Coach profile library


#### C01. Elias Mercer — Five-Out Systems Architect

**Age 44 · TAC 89 · TEA 70 · LDR 63 · ADP 54 · ORG 82**

**Build:** Five-Out Read-and-React / Switch Everything / Short Rotation / Scheme Evangelist / Shooting Laboratory

Mercer creates excellent spacing, high three-point volume, and decisive closeout attacks. His teams can become tactically dominant once familiarity is high. He prefers centers who shoot, pass, and defend in space.

His weakness is rigidity. Non-shooting bigs lose minutes, traditional post players become unhappy, and inexperienced decision-makers commit turnovers. When the offense stalls, Mercer tends to demand better execution rather than changing the structure.

**Best roster:** Multiple ball handlers, five shooters, switchable forwards.
**Bad fit:** Post-heavy roster with slow centers and weak perimeter defenders.
**AI behavior:** Aggressively trades traditional bigs and prioritizes shooting over nominal position.

---

#### C02. Sofia Navarro — Motion Development Teacher

**Age 39 · TAC 79 · TEA 91 · LDR 82 · ADP 86 · ORG 74**

**Build:** Motion/Handoff / Matchup Adaptive Defense / Youth Trial / Teacher-Explainer / Role Converter

Navarro is a long-term program builder. She teaches cutting, passing, secondary creation, and defensive versatility. Young wings and undersized playmakers often find new roles under her.

The system takes time to learn, and her patience can cost early-season games. She is not yet an elite late-game tactician and can leave developing players in difficult situations longer than a win-now coach would.

**Best roster:** Young, intelligent, versatile players without fixed roles.
**Bad fit:** Veteran contender demanding immediate results and simple roles.
**AI behavior:** Values IQ, passing, adaptability, and development runway.

---

#### C03. Darnell Price — Pressure-to-Pace Enforcer

**Age 51 · TAC 76 · TEA 68 · LDR 88 · ADP 48 · ORG 80**

**Build:** Pace-and-Space / Turnover Hunt / Deep Waves / Accountability Hardliner / Defensive Academy

Price wants relentless pressure. His defense attacks passing lanes, his bench plays fast, and poor effort is punished immediately. High-work-ethic players often love him.

The system produces fouls, fatigue, and occasional defensive disasters. Low-confidence players can deteriorate under his direct criticism. Price rarely slows down even when the roster is not suited to his style.

**Best roster:** Athletic depth, competitive personalities, transition finishers.
**Bad fit:** Thin rotation, older roster, foul-prone defenders.
**AI behavior:** Prefers ten playable athletes over a top-heavy roster.

---

#### C04. Ren Ito — Pick-and-Roll Engineer

**Age 46 · TAC 87 · TEA 77 · LDR 72 · ADP 69 · ORG 78**

**Build:** Pick-and-Roll Engine / Drop Fortress / Star Stagger / Calm Stabilizer / Guard Guru

Ito carefully organizes the offense around a primary creator and a screening big. He is excellent at staggering creators and developing guards’ reads.

Aggressive switching and trapping can disrupt his preferred structure. Defensively, pull-up shooters can punish his drop coverage. Ito adapts, but usually one or two games later than an elite playoff tactician.

**Best roster:** Lead guard, rim-running or popping big, reliable point-of-attack defenders.
**Bad fit:** No primary creator or no competent screen-setting big.
**AI behavior:** Invests heavily in guards, screeners, and low-turnover role players.

---

#### C05. Amara Okafor — Switch-and-Scramble Innovator

**Age 41 · TAC 84 · TEA 80 · LDR 74 · ADP 92 · ORG 65**

**Build:** Balanced Adaptive Offense / Small-Ball Scramble / Matchup Chess / Democratic Collaborator / Wing Laboratory

Okafor is comfortable changing lineups, coverages, and roles. She can convert oversized guards and undersized forwards into interchangeable two-way players.

Her teams sometimes lack a stable identity. Frequent changes reduce familiarity, and assistants may struggle to keep pace with her ideas. Players who prefer rigid roles can become frustrated.

**Best roster:** Switchable wings, flexible lineups, high-IQ defenders.
**Bad fit:** Specialists who can perform only one narrow assignment.
**AI behavior:** Drafts positional size and versatility, then experiments aggressively.

---

#### C06. Tomas Varga — Elbow-Hub Traditionalist

**Age 58 · TAC 81 · TEA 86 · LDR 70 · ADP 42 · ORG 85**

**Build:** Elbow Hub / Conservative Contain / Continuity Loyalist / Teacher-Explainer / Big Builder

Varga creates organized offense through passing bigs, split cuts, and patient execution. His teams tend to protect the ball and understand their assignments.

He is slow to abandon his system. Without a skilled hub, the offense becomes stagnant. He gives trusted veterans a long leash and may underuse athletic but tactically raw prospects.

**Best roster:** Passing center, cutters, intelligent veterans, stable rotation.
**Bad fit:** Young transition roster with no interior passer.
**AI behavior:** Prioritizes skill and decision-making over raw athleticism.

---

#### C07. Claire Beaumont — Adaptive CEO

**Age 48 · TAC 83 · TEA 72 · LDR 84 · ADP 90 · ORG 88**

**Build:** Balanced Adaptive / Matchup Adaptive Defense / Matchup Chess / CEO Delegator / Floor Raiser

Beaumont builds excellent staffs and changes strategy according to personnel. She rarely creates a disastrous fit and is especially effective when supplied with strong assistants.

Her own systems do not deliver the highest possible peak. When assistants are hired away, performance can fall sharply. She can also appear indecisive because the team changes style across seasons.

**Best roster:** Any balanced roster with a strong staff budget.
**Bad fit:** Organization unwilling to invest in assistants.
**AI behavior:** Recruits specialists to cover weaknesses and grants them substantial control.

---

#### C08. Marcus Bell — Paint Fortress Veteran

**Age 62 · TAC 74 · TEA 67 · LDR 85 · ADP 35 · ORG 91**

**Build:** Post Hub / Big Front Wall / Short Rotation / Veteran Trust / Veteran Maintainer

Bell controls the paint, values physical rebounding, and keeps experienced teams organized. Veterans understand their roles and rarely panic.

Space-heavy opponents can expose his large lineups. Bell is reluctant to play inexperienced guards and may remain loyal to declining veterans. His offense can struggle to generate enough threes.

**Best roster:** Veteran contender with size and interior skill.
**Bad fit:** Young rebuilding team built around speed and perimeter creation.
**AI behavior:** Signs experienced bigs and values playoff experience heavily.

---

#### C09. Nia Reynolds — Youth Laboratory Rebuilder

**Age 35 · TAC 68 · TEA 93 · LDR 79 · ADP 88 · ORG 61**

**Build:** Motion/Handoff / Zone Shape-Shifter / Youth Trial / Democratic Collaborator / Youth Accelerator

Reynolds gives prospects real responsibilities and develops broad basketball skills. Her flexible zone structures protect some young defenders while they learn.

She is inexperienced with veteran locker rooms and late-game management. Her teams can lose winnable games because development goals outweigh immediate optimization.

**Best roster:** Rebuild with several high-upside prospects.
**Bad fit:** Championship favorite with little patience.
**AI behavior:** Accepts short-term losses and resists trading young players for marginal upgrades.

---

#### C10. Javier Mendoza — Rim-and-Three Optimizer

**Age 43 · TAC 86 · TEA 73 · LDR 67 · ADP 75 · ORG 76**

**Build:** Rim Pressure plus Bombs Away / Perimeter Denial / Star Stagger / Scheme Evangelist / Guard Guru

Mendoza removes low-value offensive actions. His teams attack the rim, take threes, and avoid passive possessions. Defensively, he chases opponents away from preferred perimeter locations.

The approach can become predictable, and poor shooting creates extreme variance. Players who thrive in the midrange may feel misused even when they remain efficient there.

**Best roster:** Rim-attacking guards, shooters, mobile defensive center.
**Bad fit:** Midrange-heavy creators and non-shooting wings.
**AI behavior:** Acquires shooting and rim pressure even at the expense of traditional positional balance.

---

#### C11. Andre Kessler — Superstar Conductor

**Age 55 · TAC 82 · TEA 64 · LDR 94 · ADP 57 · ORG 83**

**Build:** Heliocentric Star / Conservative Contain / Short Rotation / Star Whisperer / Veteran Maintainer

Kessler is exceptional at managing elite players, media pressure, and championship expectations. He creates clear complementary roles around a superstar.

The organization can become dependent on one player. Bench development slows, secondary creators receive fewer opportunities, and the offense drops sharply when the star is unavailable.

**Best roster:** Established superstar and experienced supporting cast.
**Bad fit:** Egalitarian rebuild with several developing creators.
**AI behavior:** Pushes management to consolidate assets for proven veterans.

---

#### C12. Keisha Grant — Deep-Bench Culture Builder

**Age 47 · TAC 71 · TEA 84 · LDR 93 · ADP 78 · ORG 79**

**Build:** Bench-Wave Tempo / Zone Shape-Shifter / Deep Waves / Players’ Coach / Floor Raiser

Grant keeps twelve-player rosters engaged and finds productive roles for overlooked players. Her teams survive injuries better than most.

She can be too generous with minutes and hesitant to shorten the rotation. Elite players may resent losing minutes to depth, particularly during close games.

**Best roster:** Deep, inexpensive roster without one dominant star.
**Bad fit:** Top-heavy contender whose best players must play heavy minutes.
**AI behavior:** Values depth, personality, and role acceptance.

---

#### C13. Luka Petrovic — Zone and Elbow Strategist

**Age 50 · TAC 88 · TEA 75 · LDR 62 · ADP 83 · ORG 71**

**Build:** Elbow Hub / Zone Shape-Shifter / Matchup Chess / Competitive Firebrand / Big Builder

Petrovic produces unusual tactical problems. His offense works through skilled frontcourt passers, while his defense changes structures between possessions.

His communication can be abrupt, and players may not understand why their roles change. Poor defensive IQ leads to ugly breakdowns.

**Best roster:** Long, intelligent, tactically versatile frontcourt.
**Bad fit:** Simple-role athletes with weak communication skills.
**AI behavior:** Chooses unusual high-IQ prospects other teams may undervalue.

---

#### C14. Malik Carter — No-Middle Accountability Coach

**Age 45 · TAC 80 · TEA 79 · LDR 87 · ADP 55 · ORG 81**

**Build:** Deliberate Control / No-Middle Defense / Continuity Loyalist / Accountability Hardliner / Defensive Academy

Carter establishes defensive standards quickly. Roles are clear, effort is consistent, and opponents are pushed toward uncomfortable areas.

His offense can be overly conservative. Players who dislike strict responsibilities may clash with him, and he can wait too long before changing defensive rules.

**Best roster:** Disciplined defenders, strong culture, reliable half-court creator.
**Bad fit:** Free-form offensive players and low-accountability personalities.
**AI behavior:** Trades talented but repeatedly undisciplined players.

---

#### C15. Hannah Cho — Health and Continuity Director

**Age 52 · TAC 72 · TEA 82 · LDR 89 · ADP 81 · ORG 94**

**Build:** Balanced Adaptive / Conservative Contain / Load Manager / Calm Stabilizer / Veteran Maintainer

Cho produces organized, sustainable seasons. She collaborates well with performance staff and protects players from accumulating excessive fatigue.

She can be too conservative in must-win games and may rest players more than ownership or fans prefer. Her teams generate relatively few turnovers and offensive rebounds.

**Best roster:** Older contender or injury-sensitive stars.
**Bad fit:** Young team that needs maximum tempo and experimentation.
**AI behavior:** Prioritizes availability, depth, and long-term health.

---

#### C16. Isaiah Boone — Offensive-Glass Chaos Coach

**Age 40 · TAC 78 · TEA 69 · LDR 76 · ADP 63 · ORG 72**

**Build:** Offensive Glass Pressure / Blitz and Recover / Hot-Hand Manager / Competitive Firebrand / Big Builder

Boone creates extra possessions through rebounding and turnovers. His teams can overwhelm passive opponents with physical energy.

Transition defense is vulnerable, and his hot-hand decisions sometimes chase random short-term results. Fatigue accumulates rapidly without depth.

**Best roster:** Strong rebounders, energetic wings, deep frontcourt.
**Bad fit:** Small roster with slow recovery defenders.
**AI behavior:** Values motor, strength, and rebounding more than conventional efficiency models do.

---

#### C17. Leila Haddad — Perimeter Motion Teacher

**Age 42 · TAC 85 · TEA 87 · LDR 80 · ADP 84 · ORG 68**

**Build:** Motion/Handoff / Perimeter Denial / Star Stagger / Teacher-Explainer / Wing Laboratory

Haddad develops complete wings and builds movement-heavy offenses. Defensively, her teams make shooters work for every catch.

Her preparation can become too complex, and she needs a strong organizational assistant. Backcuts and physical interior teams can exploit her perimeter focus.

**Best roster:** Mobile wings, passing guards, active off-ball players.
**Bad fit:** Slow interior roster with limited passing.
**AI behavior:** Prioritizes wings who can shoot, pass, and defend rather than one-dimensional scorers.

---

#### C18. Devon Brooks — Underdog Simplifier

**Age 60 · TAC 75 · TEA 80 · LDR 91 · ADP 72 · ORG 87**

**Build:** Deliberate Control / Conservative Contain / Continuity Loyalist / Calm Stabilizer / Floor Raiser

Brooks reduces mistakes, protects weak players, and gives limited rosters a stable identity. His teams often meet or slightly exceed low expectations.

He rarely creates a championship-level ceiling. Strong opponents can solve his conservative schemes, and he does not generate many easy possessions.

**Best roster:** Low-talent team needing competence and stability.
**Bad fit:** Elite roster requiring tactical aggression.
**AI behavior:** Signs reliable veterans and avoids volatile developmental bets.

---

#### C19. Camille Laurent — Playoff Matchup Tinkerer

**Age 49 · TAC 93 · TEA 65 · LDR 69 · ADP 94 · ORG 70**

**Build:** Midrange Matchup Artist / Matchup Adaptive Defense / Matchup Chess / Experimentalist / Role Converter

Laurent is designed for long playoff series. She identifies weak defenders, changes coverage, and constructs specialized closing lineups.

The regular season can look unstable. Players receive inconsistent roles, young-player development is ordinary, and over-tinkering sometimes creates self-inflicted problems.

**Best roster:** Experienced, versatile contender with multiple lineup options.
**Bad fit:** Young roster requiring consistency and clear roles.
**AI behavior:** Accepts regular-season experimentation to prepare for postseason matchups.

---

#### C20. Raymond Cole — Veteran Post Stabilizer

**Age 57 · TAC 76 · TEA 74 · LDR 92 · ADP 40 · ORG 86**

**Build:** Post Hub / Drop Fortress / Continuity Loyalist / Players’ Coach / Veteran Maintainer

Cole establishes trust, feeds interior scorers, and maintains a stable locker room. His teams rarely collapse emotionally.

He is reluctant to modernize his offense or bench trusted veterans. Dynamic pull-up guards can exploit his defense, and developmental guards may lack freedom.

**Best roster:** Experienced interior scorer, rim protector, veteran guards.
**Bad fit:** Young five-out roster.
**AI behavior:** Seeks familiar veterans and rarely makes major midseason tactical changes.

---

#### C21. Amina Yusuf — Shooting Development Prospect

**Age 37 · TAC 74 · TEA 95 · LDR 77 · ADP 82 · ORG 60**

**Build:** Five-Out / Perimeter Denial / Youth Trial / Teacher-Explainer / Shooting Laboratory

Yusuf can improve shooting readiness, footwork, relocation habits, and confidence. She is especially useful for a rebuilding team with athletic non-shooters.

Her endgame management and staff organization are still developing. She may be a better lead assistant than head coach at the beginning of a save.

**Best roster:** Young athletes needing offensive skill development.
**Bad fit:** Veteran team with no patience for a first-time head coach.
**AI behavior:** Accepts rebuilding opportunities that provide job security.

---

#### C22. Mateo Silva — Transition-Wave Firebrand

**Age 44 · TAC 82 · TEA 75 · LDR 86 · ADP 71 · ORG 73**

**Build:** Pace-and-Space / Small-Ball Scramble / Deep Waves / Competitive Firebrand / Youth Accelerator

Silva plays quickly, uses athletic bench groups, and gives young players opportunities. His teams are dangerous after turnovers and missed shots.

The schedule can wear them down. Emotional volatility and constant pace create slumps when shooting declines or injuries reduce depth.

**Best roster:** Young, athletic, deep team.
**Bad fit:** Older or top-heavy roster.
**AI behavior:** Drafts speed, stamina, and open-floor skill.

---

#### C23. Jordan Kim — Data-Driven Shot Architect

**Age 46 · TAC 90 · TEA 71 · LDR 65 · ADP 87 · ORG 90**

**Build:** Bombs-Away / Matchup Adaptive Defense / Matchup Chess / CEO Delegator / Floor Raiser

Kim uses lineup data, shot quality, and opponent tendencies aggressively. The team’s decision profile is highly rational and difficult to exploit structurally.

Players may feel reduced to models and roles. Kim can underappreciate confidence, relationships, and individual shot-making comfort.

**Best roster:** Organization with strong analytics and versatile personnel.
**Bad fit:** Star-led locker room demanding personal freedom.
**AI behavior:** Searches for undervalued role players whose skills fit specific lineup needs.

---

#### C24. Priya Desai — Staff-Building Executive Coach

**Age 53 · TAC 70 · TEA 78 · LDR 88 · ADP 76 · ORG 97**

**Build:** Balanced Adaptive / Matchup Adaptive Defense / Continuity Loyalist / CEO Delegator / Assistant Incubator

Desai creates outstanding coaching staffs, clearly divides responsibilities, and develops future head coaches. Her organization remains functional through injuries and staff turnover.

She is not an elite direct tactician. A poor assistant hire can expose her, and successful assistants are frequently poached by other teams.

**Best roster:** Stable organization willing to invest in staff.
**Bad fit:** Low-budget team expecting one coach to perform every responsibility.
**AI behavior:** Hires specialists, promotes internally, and negotiates for substantial staff control.

---

## 6. Medical and health-performance system

### 6.1 Public pillars

| Pillar | Meaning |
|---|---|
| **Clinical Care** | Assessment, diagnosis, treatment, illness care, medical judgment |
| **Rehabilitation** | Functional recovery, reconditioning, and setback prevention |
| **Prevention** | Screening, early intervention, movement risk, preventive programming |
| **Performance Science** | Workload, fatigue, conditioning, recovery, and data interpretation |
| **Trust & Operations** | Communication, confidentiality, records, collaboration, and management |

### 6.2 Required medical attributes

```text
Clinical:
clinicalAssessment, diagnosticAccuracy, prognosisAccuracy, acuteInjuryCare,
illnessManagement, specialistJudgment, medicalExaminations,
complicationDetection, returnToPlayJudgment, emergencyPreparedness

Rehabilitation:
rehabilitationPlanning, therapeuticSkill, functionalTesting, reconditioning,
returnToPerformance, setbackPrevention, planIndividualization,
painManagement, longTermConditionManagement

Prevention and science:
injuryPrevention, loadMonitoring, fatigueAssessment, recoveryPlanning,
conditioningIntegration, movementScreening, travelManagement,
dataInterpretation, riskCalibration

Trust and operations:
playerTrust, communication, medicalIntegrity, collaboration, confidentiality,
documentation, departmentManagement, availability, secondOpinionManagement,
culturalCompetence
```

### 6.3 Medical tendencies


Ability determines **how well** someone performs a job. Tendencies determine **how they prefer to perform it**.

| Tendency                              | Low end                                      | High end                                              |
| ------------------------------------- | -------------------------------------------- | ----------------------------------------------------- |
| **Return Risk Tolerance**             | Requires extensive evidence before clearance | Clears players closer to minimum acceptable readiness |
| **Testing Frequency**                 | Relies on examination and observation        | Frequently uses imaging, testing, and monitoring      |
| **Preventive Intervention Threshold** | Intervenes only after symptoms               | Acts on small warning signs                           |
| **Player Autonomy**                   | Highly directive treatment                   | Strong player input and shared decisions              |
| **Second-Opinion Openness**           | Protects internal process                    | Encourages outside consultation                       |
| **Workload Conservatism**             | Tolerates high workload                      | Recommends rest quickly                               |
| **Treatment Innovation**              | Established methods                          | Willing to use new methods                            |
| **Communication Detail**              | Gives simple availability information        | Provides extensive explanations                       |
| **Privacy Strictness**                | Shares broadly within organization           | Shares only functionally necessary information        |
| **Rest Preference**                   | Prefers modified activity                    | Prefers full removal from activity                    |
| **Surgery Preference**                | Favors conservative management               | Refers to surgical solutions more readily             |
| **Performance Priority**              | Focuses on basic safe return                 | Focuses heavily on restoring previous performance     |

None of these should be universally superior.

A conservative medical director may produce:

* Longer average absences.
* Fewer early setbacks.
* More conflict with an impatient coach.
* Higher trust among cautious players.
* Frustration from stars who want to return quickly.

An aggressive availability specialist may produce:

* More games played in the short term.
* More “available with restriction” statuses.
* Higher accumulated wear.
* Greater setback variance.
* Strong relationships with players who prioritize participation.

---

### 6.4 Medical specialties


Each medical employee should have zero to three genuine specialties.

```text
Knee and ACL Rehabilitation
Foot and Ankle
Back and Spine
Shoulder and Upper Body
Tendon Management
Soft-Tissue Injuries
Concussion and Neurological Care
Postoperative Rehabilitation
Chronic Pain
Illness and Immunology
Cardiac Screening
Nutrition and Energy Availability
Sleep and Travel Recovery
Biomechanics
Return-to-Performance
Veteran Maintenance
Young-Athlete Screening
Mental Health and Wellness
Emergency Medicine
```

Specialties should improve quality and confidence only when relevant. A knee-rehabilitation expert should not automatically improve flu recovery or concussion assessment.

---

### 6.5 Department identities


Individual staff create the department identity, but teams can also receive a summary description.

| Department identity                   | Strength                                                           | Cost                                                  |
| ------------------------------------- | ------------------------------------------------------------------ | ----------------------------------------------------- |
| **Health-First Institution**          | Strong independence, trust, low premature-return risk              | More conservative availability                        |
| **Availability Optimizer**            | More games played with controlled restrictions                     | Higher setback variance                               |
| **Diagnostics Network**               | Accurate complex diagnoses and second opinions                     | Expensive and occasionally slower                     |
| **Rehabilitation Laboratory**         | Excellent function and return-to-performance                       | Less emphasis on daily prevention                     |
| **Load Science Unit**                 | Strong fatigue and workload management                             | Requires player and coach cooperation                 |
| **Player-Trust Clinic**               | Early symptom reporting and strong adherence                       | Less authoritative with confrontational personalities |
| **Traditional Treatment Room**        | Stable, inexpensive, trusted care                                  | Weak data and risk calibration                        |
| **Integrated Performance Department** | Medical, conditioning, nutrition, and development communicate well | Expensive and vulnerable to role conflict             |
| **Specialist Collection**             | Elite knowledge across injury types                                | Coordination and ego problems                         |
| **Budget Generalists**                | Adequate coverage at low cost                                      | Wide prognosis ranges and weaker specialties          |

---

### 6.6 Health-state engine

A player does not jump directly from injured to healthy.

```text
Healthy
Elevated Load
Symptomatic
Evaluation Pending
Diagnosed Injury
Rehabilitation
Return to Participation
Return to Sport
Return to Performance
Chronic Management
```

For each condition store a **true state** and an **observed state**. Initial diagnosis and prognosis can be wrong or broad. Strong staff narrow uncertainty, detect complications, select appropriate treatment, improve adherence, restore function, and avoid preventable setbacks. They only modestly change biological healing time.

Every health report should include:

```text
Participation status
Known condition and diagnosis confidence
Medical restrictions
Coach-selected workload
Return windows for individual work, practice, game clearance, and prior performance
Previous related injuries
Principal risk factors
Treatment adherence
Medical recommendation
Next evaluation
```

Do not show a false-precision injury probability. Use labels and confidence, such as `Elevated lower-body risk — Moderate confidence`, plus the reasons.

### 6.7 Medical formulas

**Workload stress**

```text
workloadStress =
  0.30*recentGameExposure
  + 0.20*recentPracticeExposure
  + 0.15*movementIntensity
  + 0.10*travelStress
  + 0.10*recoveryDebt
  + 0.10*reportedSoreness
  + 0.05*nonBasketballStress
```

**Modifiable noncontact risk**

```text
nonContactHazard =
  baseExposureHazard
  * bodyRegionSusceptibility
  * priorInjuryMultiplier
  * fatigueMultiplier
  * loadChangeMultiplier
  * conditioningMultiplier
  * preventionMultiplier

preventionMultiplier =
  clamp(0.85, 1.05,
    1.00
    - 0.05*n(injuryPrevention)
    - 0.04*n(loadMonitoring)
    - 0.03*n(playerTrust)
    - 0.03*n(conditioningIntegration)
  )
```

Apply staff modifiers only to the modifiable portion. Staff should have little effect on unpredictable contact injuries.

**Prognosis uncertainty**

```text
prognosisWindowWidth =
  baseWindowWidth
  * clamp(0.55, 1.40,
      1.00
      - 0.20*n(diagnosticAccuracy)
      - 0.12*n(prognosisAccuracy)
      - 0.08*n(specialistAccess)
      - 0.08*n(facilityQuality)
    )
```

**Healing and functional recovery**

```text
biologicalHealing =
  injuryBaseHealing
  * playerBiologicalFactors
  * treatmentAppropriateness

functionalRecovery =
  baseFunctionalGain
  * rehabilitationQuality
  * playerAdherence
  * recoveryQuality
  * workloadMatch
  * confidenceFactor
```

**Setback risk**

```text
setbackRisk =
  baseSetbackRisk
  * reinjurySusceptibility
  * workloadExcess
  * movementDemand
  * incompleteFunction
  * planDeviation
  * staffSetbackModifier

staffSetbackModifier =
  clamp(0.70, 1.25,
    1.00
    - 0.10*n(setbackPrevention)
    - 0.08*n(functionalTesting)
    - 0.05*n(playerTrust)
  )
```

**Binding workload**

```text
finalPermittedLoad =
  min(medicalClearanceLimit,
      rehabilitationStageLimit,
      playerFunctionalLimit,
      leagueRuleLimit)

actualAssignedLoad =
  min(finalPermittedLoad,
      coachRequestedLoad,
      playerAcceptedLoad)
```

### 6.8 Trust, reporting, and privacy

Symptom reporting depends on medical trust, coach pressure, contract status, playoff importance, personality, prior treatment, role fear, communication, and team culture. Outcomes can include early reporting, delay, partial reporting, hidden symptoms, frequent cautious reporting, or outside consultation.

Clinical mental-health support is confidential. It affects access, adherence, wellbeing, burnout, recovery, and availability—not shooting or clutch ratings. The normal GM screen sees only functional availability information.

### 6.9 Medical AI and evaluation

AI hiring prioritizes roster health needs, clinical quality, rehabilitation fit, prevention, performance science, trust, collaboration, autonomy compatibility, and cost.

Evaluate departments by diagnostic calibration, avoidable setbacks, availability versus expectation, rehabilitation efficiency, return-to-performance quality, early reporting, communication errors, examination quality, player trust, and continuity—not raw injury count.

### 6.10 Medical profile library


#### M01. Dr. Maya Chen — Independent Gatekeeper

**Age 48 · Team Physician**
**CLN 95 · REH 82 · PRE 84 · SCI 87 · TRU 79**

Chen is highly accurate, resistant to organizational pressure, and cautious about competitive clearance. Her return windows narrow quickly after proper testing.

Her players miss slightly more time during early return stages, but premature-return setbacks are uncommon. Aggressive coaches may have a poor relationship with her.

**Traits:** Conservative Clearance, Complication Hawk, Second-Opinion Friendly
**Best use:** Older contender, high-value stars, complicated injury history
**Weakness:** Can frustrate players who prioritize immediate availability

---

#### M02. Dr. Lucas Ferreira — Availability-Focused Physician

**Age 44 · Team Physician**
**CLN 87 · REH 83 · PRE 77 · SCI 74 · TRU 91**

Ferreira uses collaborative decision-making and is comfortable clearing players with clearly defined restrictions. Players appreciate that he explains acceptable risks rather than giving automatic refusals.

He produces more limited-availability games and slightly higher setback variance than Chen.

**Traits:** Shared Decision Maker, Restriction Specialist, Player Advocate
**Best use:** Competitive team with experienced players
**Weakness:** Requires disciplined coaches who follow restrictions

---

#### M03. Renee Watkins — Player-Trust Athletic Trainer

**Age 41 · Head Athletic Trainer**
**CLN 83 · REH 91 · PRE 85 · SCI 76 · TRU 97**

Watkins develops exceptionally strong player relationships. Players report soreness earlier and adhere closely to treatment plans.

She is not an elite specialist diagnostician, so the department needs a strong physician or referral network for complex cases.

**Traits:** Open Door, Early Reporting, Travel Care
**Best use:** Teams with young players or previous medical distrust
**Weakness:** Complex diagnostic work

---

#### M04. Priya Nandakumar — Load Science Director

**Age 38 · Sports Scientist**
**CLN 69 · REH 74 · PRE 95 · SCI 98 · TRU 73**

Nandakumar excels at identifying workload spikes, recovery debt, and declining movement capacity. Her recommendations reduce avoidable overload problems when coaches cooperate.

Some veterans dislike frequent monitoring, and she is not qualified to make final diagnoses or medical clearances.

**Traits:** Trend Analyst, Fatigue Calibration, Data Intensive
**Best use:** Fast-paced team, dense rotation, deep player-monitoring system
**Weakness:** Player acceptance and clinical care

---

#### M05. Eli Rosen — Return-to-Performance Specialist

**Age 45 · Rehabilitation Director**
**CLN 76 · REH 98 · PRE 84 · SCI 87 · TRU 89**

Rosen is excellent at restoring strength, movement, confidence, and basketball-specific function after serious injury. His players are less likely to remain technically cleared but physically ineffective for months.

His process is expensive and sometimes slows initial reactivation because he emphasizes performance restoration.

**Traits:** Functional Testing, Movement Restoration, Reinjury Prevention
**Best use:** Teams protecting stars after major injuries
**Weakness:** Routine illness and acute diagnosis

---

#### M06. Carmen Duarte — Soft-Tissue Specialist

**Age 36 · Physical Therapist**
**CLN 80 · REH 96 · PRE 92 · SCI 79 · TRU 86**

Duarte specializes in muscular, tendon, and recurring lower-body conditions. She is highly effective with players whose repeated small injuries have become chronic availability problems.

Her value is lower for fractures, neurological conditions, or general illness.

**Traits:** Soft-Tissue Specialist, Tendon Management, Individualized Rehab
**Best use:** Athletic roster with recurring hamstring, calf, or tendon issues
**Weakness:** Narrow specialty

---

#### M07. Dr. Harold Kim — Specialist Network Director

**Age 55 · Chief Medical Officer**
**CLN 94 · REH 78 · PRE 81 · SCI 90 · TRU 84**

Kim knows when internal staff has reached its limit and maintains an elite external referral network. Difficult diagnoses become clearer and second opinions are well coordinated.

His department is expensive, and multi-specialist cases can produce slower administrative decisions.

**Traits:** Specialist Connector, Complex Diagnosis, Medical Records
**Best use:** Wealthy organization with high-value assets
**Weakness:** Cost and speed

---

#### M08. Nadia Bell — Recovery and Nutrition Director

**Age 40 · Performance Dietitian**
**CLN 65 · REH 83 · PRE 93 · SCI 90 · TRU 95**

Bell improves recovery habits, nutritional adherence, travel routines, and general player availability. She is particularly useful during dense schedules.

She does not diagnose orthopedic injuries and must not be treated as a replacement for medical or rehabilitation staff.

**Traits:** Travel Recovery, Nutrition Adherence, Illness Prevention
**Best use:** Older teams, heavy travel, conditioning-intensive systems
**Weakness:** Clinical diagnosis

---

#### M09. Thomas Venn — Traditional Treatment-Room Generalist

**Age 59 · Head Athletic Trainer**
**CLN 77 · REH 86 · PRE 69 · SCI 46 · TRU 94**

Venn is experienced, trusted, and excellent at day-to-day care. He communicates clearly with players and rarely loses the locker room.

His department relies heavily on observation and established routines. It can miss workload trends that a modern sports-science unit would identify.

**Traits:** Veteran Trust, Hands-On Treatment, Low Technology
**Best use:** Budget organization or veteran roster
**Weakness:** Monitoring and innovation

---

#### M10. Talia Brooks — Mental Health and Wellness Clinician

**Age 43 · Licensed Clinical Specialist**
**CLN 73 · REH 72 · PRE 81 · SCI 75 · TRU 99**

Brooks supports players dealing with stress, injury-related fear, personal difficulties, burnout, and emotional adjustment. Her presence improves help-seeking and continuity of care.

Her information remains confidential, and she does not directly improve shooting, decision-making, or tactical composure.

**Traits:** Confidential Support, Crisis Care, Injury Psychology
**Best use:** Any full-depth organization
**Weakness:** No orthopedic or tactical role

---

## 7. Coaching and player-development system

### 7.1 Department roles


| Role                               | Primary responsibility                                                           |
| ---------------------------------- | -------------------------------------------------------------------------------- |
| **Associate Head Coach**           | Staff coordination, head-coach support, broad tactical and player oversight      |
| **Lead Offensive Assistant**       | Offensive teaching, game-plan preparation, offensive skill translation           |
| **Lead Defensive Assistant**       | Defensive habits, coverage teaching, matchup preparation                         |
| **Director of Player Development** | Individual-plan creation, assignments, reviews, and long-term coordination       |
| **Shooting Coach**                 | Mechanics, footwork, preparation, shot selection, and role-specific shooting     |
| **Guard Coach**                    | Ball handling, passing, pick-and-roll reads, pace, and decision-making           |
| **Wing Coach**                     | Cutting, shooting, secondary creation, defensive versatility, role conversion    |
| **Big Coach**                      | Screening, finishing, rebounding, post defense, rim protection, interior passing |
| **Defensive Skills Coach**         | Technique, positioning, screen navigation, closeouts, rotations                  |
| **Video Coordinator**              | Film preparation, tagging, opponent examples, and player feedback                |
| **Development Analyst**            | Progress measurement, plan evaluation, and game-transfer analysis                |
| **Affiliate Coordinator**          | Aligns reserve-team minutes, roles, and teaching with the parent team            |
| **Mental Performance Coach**       | Nonclinical focus, routine, confidence, and performance preparation              |
| **Practice Coordinator**           | Practice structure, repetition quality, and staff assignment                     |

A mental-performance coach is not a therapist and should not provide clinical treatment.

---

### 7.2 Public pillars

| Pillar | Meaning |
|---|---|
| **Skill Teaching** | Technical instruction and correction |
| **Decision Teaching** | Reads, timing, awareness, and tactical understanding |
| **Individualization** | Adapting plans to the specific player |
| **Game Transfer** | Converting practice gains into competitive performance |
| **Coordination** | Planning, communication, workload, and staff alignment |

### 7.3 Required development attributes

```text
Teaching:
skillDiagnosis, technicalTeaching, decisionTeaching, tacticalTeaching,
demonstrationQuality, feedbackAccuracy, practiceDesign, gameTransfer,
roleConversion, habitCorrection

Planning:
playerEvaluation, planDesign, individualization, progressionTiming,
goalSetting, workloadAwareness, longTermPlanning, dataInterpretation,
planAdjustment, staffDelegation

Relationships:
communication, patience, playerTrust, motivation, accountability,
confidenceManagement, youthCommunication, veteranCommunication,
culturalAdaptability, conflictResolution

Operations:
organization, videoPreparation, collaboration, capacityManagement,
innovation, affiliateCoordination, reporting, talentIdentification
```

### 7.4 Development philosophies


| Philosophy                      | Main approach                                      | Cost                                                |
| ------------------------------- | -------------------------------------------------- | --------------------------------------------------- |
| **Fundamentals First**          | Builds stable base technique before advanced work  | Slow early visible results                          |
| **Game-Transfer First**         | Uses live and decision-based repetitions           | Technical flaws may persist                         |
| **Mechanical Rebuilder**        | Reconstructs shooting or movement technique        | Temporary performance decline                       |
| **Decision-First Teaching**     | Prioritizes reads, timing, and processing          | Raw technique grows more slowly                     |
| **Role Converter**              | Creates new positions and responsibilities         | Higher failure variance                             |
| **Floor Raiser**                | Builds reliable rotation players                   | Fewer dramatic ceiling outcomes                     |
| **Ceiling Chaser**              | Expands difficult skills and responsibilities      | More failed experiments                             |
| **Confidence Builder**          | Protects confidence and encourages experimentation | May delay difficult corrections                     |
| **Accountability Instructor**   | Demands precise execution and repetition           | Can damage relationships                            |
| **Competitive Repetition**      | Uses live drills and pressure                      | Greater fatigue and less mechanical isolation       |
| **Video Classroom**             | Teaches through film and concept recognition       | Less useful to players who need physical repetition |
| **Low-Volume Personalization**  | Gives a few players exceptional attention          | Limited department capacity                         |
| **High-Volume Standardization** | Serves many players through shared programs        | Less individualization                              |
| **Veteran Maintenance**         | Preserves skills and adjusts roles                 | Limited youth ceiling development                   |
| **Affiliate Pipeline**          | Coordinates reserve-team roles and minutes         | Less direct attention to current stars              |

---

### 7.5 Department identities


| Department identity              | Staffing emphasis                                          | Strength                                       | Cost                                        |
| -------------------------------- | ---------------------------------------------------------- | ---------------------------------------------- | ------------------------------------------- |
| **Rebuild Academy**              | Development director, shooting, role conversion, affiliate | Broad young-player growth                      | Short-term losses and high workload         |
| **Guard Creation Laboratory**    | Guard coach, shooting coach, video coordinator             | Creates ball handlers and decision-makers      | Limited big development                     |
| **Two-Way Wing Factory**         | Wing coach, shooting coach, defensive instructor           | Produces versatile wings                       | Expensive and slow                          |
| **Big Development Center**       | Big coach, strength support, video                         | Screening, defense, passing, finishing         | Less guard specialization                   |
| **Contender Optimization Unit**  | Veteran coach, video, role specialist                      | Improves role clarity and marginal performance | Limited ceiling growth                      |
| **Affiliate Pipeline**           | Affiliate coordinator, generalist teachers                 | Better prospect-role continuity                | Less attention for active roster            |
| **Mechanical Skills Laboratory** | Shooting and technical specialists                         | Strong technical change                        | Weak decision and tactical development      |
| **Game-Transfer Department**     | Competitive coach, lead assistants, video                  | Practice improvements appear in games          | More fatigue and fewer isolated corrections |
| **Floor-Raising Program**        | Fundamentals and defensive coaches                         | Produces dependable rotation players           | Fewer star outcomes                         |
| **Ceiling-Chasing Program**      | Role converters and creative teachers                      | Larger upside outcomes                         | More failed plans and instability           |

---

### 7.6 Individual development plan

Every meaningful player can have one primary objective, one secondary objective, a target role, assigned coaches, a current phase, workload allocation, medical constraints, game-application targets, success criteria, and temporary costs.

```text
Assessment
Foundation
Controlled Repetition
Variable Repetition
Competitive Application
Game Introduction
Stabilization
Expansion
Maintenance
```

Different coaches can specialize in different stages.

### 7.7 Staff capacity

Each plan consumes complexity points. Example costs:

| Plan | Cost |
|---|---:|
| Maintenance | 4 |
| Simple shooting-volume change | 6 |
| Basic defensive habits | 7 |
| New finishing package | 8 |
| Shooting-mechanics rebuild | 12 |
| Secondary playmaking | 13 |
| Position change | 14 |
| Full role conversion | 18 |
| Post-injury performance reconstruction | 20 |

```text
attentionRatio =
  clamp(0.45, 1.10,
    availableAttentionPoints / assignedComplexityPoints
  )

availableAttentionPoints =
  baseCapacity
  * organizationModifier
  * staffWorkEthicModifier
  * departmentCohesionModifier
```

Overload causes generic plans, late reviews, contradictory instruction, poor adjustment, slow progress, and unequal attention.

### 7.8 Development formulas

```text
planQuality =
  0.20*planDesign
  + 0.16*relevantTeaching
  + 0.14*skillDiagnosis
  + 0.12*individualization
  + 0.10*feedbackAccuracy
  + 0.10*specialtyFit
  + 0.08*playerTrust
  + 0.06*headCoachAlignment
  + 0.04*medicalCoordination

skillAcquisition =
  playerBaseDevelopment
  * planQualityModifier
  * attentionRatio
  * healthAvailability
  * playerWorkEthic
  * instructionFit
  * repetitionQuality
  * randomDevelopmentVariance

gameTransfer =
  acquiredSkill
  * coachGameTransferAbility
  * roleOpportunity
  * competitiveRepetition
  * headCoachBuyIn
  * playerDecisionAbility
  * confidenceFactor

roleProficiencyGain =
  relevantSkillLevel
  * tacticalUnderstanding
  * roleRepetitions
  * decisionTeaching
  * lineupFamiliarity
  * coachRoleClarity

availableDevelopmentDose =
  min(developmentRequestedDose,
      medicalPermittedDose,
      playerRecoveryCapacity)
```

`Skill learned` is not the same as `skill used effectively in games`.

### 7.9 Coach alignment and contradictory instruction

Each plan tracks head-coach support: `Strong`, `Moderate`, `Weak`, or `Opposed`. A player can improve in practice but fail to transfer the skill because the coach never provides the required role or possessions.

Instruction coherence accounts for mechanical, tactical, role, and workload contradictions. Controlled disagreement can improve innovation; unclear authority creates confusion and slower development.

### 7.10 Practice resources

Practice activities trade skill gain against fatigue, injury exposure, staff capacity, and recovery. Standard mode requires only broad settings such as development priority and practice risk. Detailed scheduling belongs in Full mode.

### 7.11 Development AI and evaluation

AI hiring weighs roster timeline, current skill needs, head-coach fit, individualization, game transfer, player relationships, department need, affiliate fit, promotion risk, and cost.

Evaluate staff by improvement over baseline, plan calibration, role proficiency, game transfer, player coverage, capacity use, plan completion, relationships, medical coordination, affiliate continuity, and staff development.

### 7.12 Development profile library


#### D01. Sofia Park — Individual Plan Architect

**Age 40 · Director of Player Development**
**SKL 87 · DEC 85 · IND 97 · XFR 91 · ORG 93**

Park creates excellent individualized plans and is especially effective with players whose eventual role is unclear. She coordinates well with medical and coaching staff.

Her programs are demanding on staff capacity because she resists standardized plans.

**Traits:** Patient Teacher, Role Designer, Long-Term Planner
**Best use:** Rebuilding roster with varied young players
**Weakness:** Limited high-volume capacity

---

#### D02. Jamal Rivers — Guard Creation Coach

**Age 43 · Guard Development Coach**
**SKL 89 · DEC 96 · IND 85 · XFR 95 · ORG 79**

Rivers teaches pace, pick-and-roll reads, passing windows, ball protection, and manipulation of defenders. He is particularly effective with guards who already possess basic handle and vision.

He can overexpand a player’s role and produce a temporary rise in turnovers.

**Traits:** Pick-and-Roll Teacher, Decision Pressure, Creator Expansion
**Best use:** Young guards with playmaking potential
**Weakness:** Big-man development and role simplicity

---

#### D03. Lena Kovacs — Shooting Mechanics Specialist

**Age 37 · Shooting Coach**
**SKL 98 · DEC 77 · IND 92 · XFR 88 · ORG 76**

Kovacs is excellent at diagnosing balance, preparation, footwork, release consistency, and movement shooting.

Major changes can produce a temporary shooting decline. The plan needs enough organizational patience to reach stabilization.

**Traits:** Mechanical Rebuild, Footwork Specialist, Shot Preparation
**Best use:** Young athletes with correctable shooting limitations
**Weakness:** Broader tactical and defensive instruction

---

#### D04. Marcus Osei — Wing Role Converter

**Age 41 · Wing Development Coach**
**SKL 91 · DEC 89 · IND 95 · XFR 92 · ORG 82**

Osei converts narrow wings into cutters, connectors, secondary handlers, or switchable forwards. His plans create valuable multi-skill players.

Role conversions have high variance and can temporarily reduce performance in the player’s established role.

**Traits:** Role Conversion, Secondary Playmaking, Positional Versatility
**Best use:** Versatile rebuilds and positionless systems
**Weakness:** Specialists who need one simple task

---

#### D05. Kenji Sato — Big-Man Decision Teacher

**Age 52 · Big Development Coach**
**SKL 92 · DEC 94 · IND 83 · XFR 90 · ORG 87**

Sato teaches screening angles, short-roll reads, interior passing, rim protection, positioning, and decision-making.

He is less effective at developing high-volume perimeter creation or advanced guard movement.

**Traits:** Screening School, Passing Hub, Interior Positioning
**Best use:** Young centers with intelligence and coordination
**Weakness:** Perimeter-heavy skill plans

---

#### D06. Aaliyah Grant — Defensive Habits Instructor

**Age 39 · Defensive Development Coach**
**SKL 85 · DEC 97 · IND 88 · XFR 93 · ORG 85**

Grant develops closeout discipline, screen navigation, positioning, help recognition, communication, and possession-to-possession consistency.

Her players devote substantial practice time to defense, reducing available offensive-development volume.

**Traits:** Habit Correction, Film-to-Floor, Accountability
**Best use:** Young athletic defenders with poor technique
**Weakness:** Offensive skill expansion

---

#### D07. Pavel Dragan — Video Translator

**Age 34 · Video Coordinator**
**SKL 75 · DEC 95 · IND 81 · XFR 92 · ORG 97**

Dragan turns film and data into understandable basketball examples. He improves recognition of opponent actions, player tendencies, and team concepts.

He is less effective during hands-on mechanical instruction and may struggle with players who resist film work.

**Traits:** Film Classroom, Pattern Recognition, Opponent Examples
**Best use:** Intelligent roster and tactically complex coaching staff
**Weakness:** Physical demonstration and technical correction

---

#### D08. Tori Mendoza — Affiliate Pipeline Director

**Age 45 · Affiliate Development Coordinator**
**SKL 83 · DEC 86 · IND 89 · XFR 87 · ORG 98**

Mendoza aligns affiliate roles, minutes, terminology, and development plans with the parent club. Prospects are less likely to dominate in a reserve role that has no connection to their future NBA role.

She provides less direct one-on-one instruction to active first-team stars.

**Traits:** Role Continuity, Affiliate Alignment, Progress Reporting
**Best use:** Prospect-heavy organization with a developmental affiliate
**Weakness:** Immediate first-team specialization

---

#### D09. Andre Ellis — Veteran Role and Maintenance Coach

**Age 56 · Player Development Coach**
**SKL 80 · DEC 89 · IND 86 · XFR 91 · ORG 93**

Ellis helps veterans adapt to declining athleticism, lower usage, bench roles, and more selective offensive responsibilities.

He raises veteran floors but is not an aggressive ceiling developer for raw prospects.

**Traits:** Role Acceptance, Skill Maintenance, Veteran Trust
**Best use:** Contenders integrating older players
**Weakness:** High-upside youth projects

---

#### D10. Noor Haddad — Confidence and Communication Coach

**Age 38 · Player Development Coach**
**SKL 84 · DEC 83 · IND 96 · XFR 89 · ORG 87**

Haddad excels with players whose performance is being limited by fear of mistakes, role uncertainty, or poor trust. She creates safe progression before increasing pressure.

She can delay hard corrections and may protect players from competitive discomfort for too long.

**Traits:** Confidence Restoration, Autonomy Support, Trust Builder
**Best use:** Young players recovering from failed roles or injuries
**Weakness:** Harsh accountability and rapid technical reconstruction

---

#### D11. Caleb Stone — Competitive Repetition Coach

**Age 46 · Lead Development Assistant**
**SKL 93 · DEC 87 · IND 74 · XFR 98 · ORG 78**

Stone pushes skills quickly into live, pressured situations. Improvements under him tend to transfer into games faster.

His sessions generate fatigue, frustration, and occasional conflict. The medical department must monitor his requested workload carefully.

**Traits:** Live Repetition, Pressure Testing, Fast Transfer
**Best use:** Healthy players close to competitive readiness
**Weakness:** Rehabilitation, fragile confidence, and individualized pacing

---

#### D12. Priya Shah — Data-Informed Development Planner

**Age 35 · Player Development Analyst**
**SKL 88 · DEC 93 · IND 92 · XFR 90 · ORG 96**

Shah measures whether skills are appearing in actual games rather than relying only on practice reports. She identifies plans that look productive but are not transferring.

Her language can feel impersonal, and player buy-in depends on coaches who can translate her findings.

**Traits:** Progress Calibration, Role Evidence, Plan Evaluation
**Best use:** Large development department with strong communicators
**Weakness:** Direct player relationships

---

## 8. General managers and AI front offices

### 8.1 Public pillars

| Pillar | Meaning |
|---|---|
| **Evaluation** | Current talent, projections, role fit, risk, and information synthesis |
| **Deals** | Trades, contracts, leverage, timing, and transaction construction |
| **Roster Building** | Stars, depth, balance, compatibility, and sustainability |
| **Strategy** | Timeline, assets, risk, adaptability, and long-term direction |
| **Operations** | Staff hiring, owner management, collaboration, and relationships |

Style is not quality. A patient rebuilder can be excellent or terrible; an aggressive trader can be disciplined or reckless.

### 8.2 Required GM attributes

```text
Evaluation:
currentTalentEvaluation, futureProjection, draftEvaluation,
professionalPersonnelEvaluation, roleEvaluation, coachFitEvaluation,
developmentFitEvaluation, characterEvaluation, medicalRiskInterpretation,
scoutingSynthesis, uncertaintyCalibration, marketEvaluation

Deals:
tradeValuation, draftPickValuation, contractValuation, negotiation,
tradeConstruction, multiTeamCreativity, timing, leverageRecognition,
salaryDumpJudgment, optionValueJudgment, closingAbility, walkAwayDiscipline

Roster building:
starAcquisition, complementaryTalent, depthConstruction, skillBalance,
ageCurveBalance, lineupCompatibility, roleClarity, injuryContingency,
replacementLevelAwareness, rosterSlotManagement, retentionJudgment,
talentConsolidation

Strategy:
timelineCalibration, longTermPlanning, assetPortfolioManagement,
riskManagement, adaptability, opportunityRecognition, downsidePlanning,
competitiveWindowConversion, rebuildSequencing, retoolSequencing,
scenarioPlanning, strategicPatience

Operations:
headCoachSelection, staffHiring, delegation, ownerManagement,
coachCollaboration, playerRelationships, agentRelationships, gmTradeNetwork,
internalCommunication, accountability, integrity, crisisManagement
```

### 8.3 GM tendencies


Ability determines **how effectively** the GM operates. Tendencies determine **what the GM prefers to do**.

## Strategic tendencies

| Slider                     | Low end                   | High end                               |
| -------------------------- | ------------------------- | -------------------------------------- |
| **Planning Horizon**       | Focuses on this season    | Values four-to-seven-year consequences |
| **Win-Now Pressure**       | Rarely accelerates        | Frequently prioritizes immediate wins  |
| **Rebuild Patience**       | Exits rebuild quickly     | Accepts several development seasons    |
| **Retool Preference**      | Chooses teardown          | Attempts to remain competitive         |
| **Optionality Preference** | Commits resources quickly | Preserves choices and flexibility      |
| **Risk Tolerance**         | Prefers stable outcomes   | Accepts high-variance outcomes         |
| **Certainty Preference**   | Values known veterans     | Values uncertain upside                |
| **Strategic Rigidity**     | Changes plans frequently  | Remains committed to original plan     |

High rigidity is not always bad. Constant plan changes can be worse.

## Acquisition tendencies

| Slider                       | Low end                        | High end                                  |
| ---------------------------- | ------------------------------ | ----------------------------------------- |
| **Trade Frequency**          | Rarely trades                  | Constant market activity                  |
| **Trade Aggression**         | Waits for clear value          | Pushes hard to complete deals             |
| **Draft Reliance**           | Trades picks regularly         | Builds primarily through the draft        |
| **Free-Agent Reliance**      | Avoids major free agency       | Pursues external signings aggressively    |
| **Internal Development**     | Replaces players externally    | Prefers internal improvement              |
| **Second-Draft Activity**    | Ignores castoffs               | Targets young players discarded elsewhere |
| **Pick Liquidity**           | Hoards future picks            | Treats picks as tradable currency         |
| **Star Pursuit**             | Prefers balanced rosters       | Consolidates for elite players            |
| **Deadline Activity**        | Avoids deadline transactions   | Frequently acts near the deadline         |
| **Undrafted/Minimum Mining** | Focuses on established players | Searches heavily for cheap marginal value |

## Roster preferences

| Slider                     | Low end                         | High end                                        |
| -------------------------- | ------------------------------- | ----------------------------------------------- |
| **Stars versus Depth**     | Deep balanced roster            | Concentrated star talent                        |
| **Fit versus Raw Talent**  | Selects strongest talent        | Selects strongest system fit                    |
| **Offense versus Defense** | Defensive value                 | Offensive value                                 |
| **Shooting Priority**      | Accepts limited shooting        | Demands shooting throughout roster              |
| **Size Priority**          | Comfortable playing small       | Values positional size                          |
| **Athleticism Priority**   | Values skill and positioning    | Values speed, explosion, and length             |
| **Basketball-IQ Priority** | Accepts raw ability             | Strongly values decisions and awareness         |
| **Durability Priority**    | Accepts medical risk            | Heavily discounts injury risk                   |
| **Character Priority**     | Tolerates personality issues    | Strongly values reliability and role acceptance |
| **Versatility Priority**   | Prefers specialists             | Prefers multi-role players                      |
| **Creation Priority**      | Builds around one creator       | Seeks several creators                          |
| **Rebounding Priority**    | Sacrifices rebounding for skill | Protects size and rebounding                    |

## Financial and organizational tendencies

| Slider                       | Low end                        | High end                                 |
| ---------------------------- | ------------------------------ | ---------------------------------------- |
| **Tax Aggression**           | Remains under budget limits    | Spends heavily during contention         |
| **Contract-Length Appetite** | Prefers short deals            | Locks in players long term               |
| **Cap-Flexibility Priority** | Uses future space readily      | Protects future flexibility              |
| **Homegrown Loyalty**        | Treats all players equally     | Pays premiums to retain internal players |
| **Veteran Loyalty**          | Moves declining veterans       | Retains established leaders              |
| **Coach Autonomy**           | GM controls roster use closely | Coach receives substantial influence     |
| **Staff Investment**         | Budget-focused departments     | Expensive specialist departments         |
| **Owner Compliance**         | Resists interference           | Closely follows owner preferences        |
| **Media Openness**           | Secretive                      | Publicly explains strategy               |
| **Internal Promotion**       | Hires external names           | Promotes assistants and scouts           |
| **Second-Opinion Openness**  | Protects internal judgments    | Frequently seeks outside input           |
| **Decision Centralization**  | Uses collaborative process     | Personally controls major decisions      |

---

### 8.4 Backgrounds


Background should seed abilities, contacts, reputation, and blind spots. It should not determine final quality.

| Background                            | Likely starting strengths                                       | Common limitation                                |
| ------------------------------------- | --------------------------------------------------------------- | ------------------------------------------------ |
| **Former Scout**                      | Talent evaluation, draft preparation, player comparisons        | Contract and organizational management           |
| **Analytics Executive**               | Projection, valuation, market inefficiencies, scenario planning | Player relationships or overconfidence in models |
| **Salary-Cap Specialist**             | Contract structure, flexibility, legal transaction construction | Basketball evaluation                            |
| **Former Player**                     | Player trust, role understanding, star relationships            | Valuation discipline or staff management         |
| **Former Coach**                      | Coach fit, tactical personnel, staff relationships              | Asset pricing and long-horizon planning          |
| **Development Executive**             | Prospect planning, role conversion, organizational patience     | Win-now acquisition                              |
| **Agent or Negotiator**               | Relationships, leverage, contracts, closing deals               | Internal evaluation systems                      |
| **International Personnel Executive** | Wider talent network and international projection               | Domestic market information                      |
| **Assistant GM Generalist**           | Broad competence and organizational experience                  | Lacks one elite differentiator                   |
| **Business Executive**                | Owner relations, budget management, market strategy             | Basketball personnel judgment                    |

A former player can become an excellent evaluator. An analyst can become an excellent relationship manager. The background only establishes the starting path.

---

### 8.5 Structured biases


Poor decisions should come from recognizable flaws rather than arbitrary random stupidity.

| Bias                           | GM behavior                                                                |
| ------------------------------ | -------------------------------------------------------------------------- |
| **Recency Bias**               | Overweights the previous month or playoff series                           |
| **Pedigree Bias**              | Overvalues famous programs, draft position, or reputation                  |
| **Athleticism Bias**           | Overvalues measurable physical tools                                       |
| **Star Halo**                  | Assumes famous players solve unrelated roster problems                     |
| **Sunk-Cost Attachment**       | Retains players because the GM previously invested heavily                 |
| **Homegrown Attachment**       | Overvalues players drafted by the organization                             |
| **Prospect Mystique**          | Treats uncertain future potential as more valuable than proven production  |
| **Veteran Certainty Bias**     | Pays heavily for known but declining performance                           |
| **Action Bias**                | Makes moves because inactivity feels unacceptable                          |
| **Loss Aversion**              | Refuses useful deals because admitting a previous mistake feels painful    |
| **Coach Capture**              | Builds entirely for the current coach even when the coach may leave        |
| **Owner Capture**              | Follows ownership’s short-term desires without maintaining a coherent plan |
| **Injury Overreaction**        | Avoids medically risky players at any reasonable price                     |
| **Injury Underreaction**       | Treats health uncertainty as irrelevant                                    |
| **Market Glamour Bias**        | Overvalues stars, headlines, and recognizable names                        |
| **Draft-Pick Hoarding**        | Refuses to consolidate picks when the roster is ready                      |
| **Age-Cliff Blindness**        | Projects older players to decline too slowly                               |
| **Development Overconfidence** | Assumes the organization can fix every raw prospect                        |
| **Fit Overconfidence**         | Believes system fit can compensate for insufficient talent                 |
| **Consensus Dependence**       | Rarely disagrees with public or leaguewide opinion                         |

Elite GMs can still have biases. Their biases should usually be milder, better audited, or offset by strong staff.

A dysfunctional GM can possess one elite skill. For example:

```text
Contract Valuation: Elite
Talent Evaluation: Poor
Strategic Planning: Poor
Owner Management: Excellent
```

That executive survives because contracts are clean and ownership likes them, even while the roster remains directionless.

---

### 8.6 Owner influence


A GM should not operate in a vacuum.

| Owner profile               | Pressure placed on GM                                              |
| --------------------------- | ------------------------------------------------------------------ |
| **Patient Builder**         | Accepts a long rebuild with visible progress                       |
| **Impatient Winner**        | Demands immediate playoff or championship results                  |
| **Cost Controller**         | Restricts salary, tax, and department spending                     |
| **Star Marketer**           | Values famous players and public attention                         |
| **Loyal Traditionalist**    | Resists trading longtime players and firing established staff      |
| **Process Investor**        | Funds scouting, analytics, development, and medical infrastructure |
| **Interventionist**         | Frequently pushes particular players, coaches, or transactions     |
| **Unstable Owner**          | Changes priorities after short performance swings                  |
| **Hands-Off Owner**         | Grants executive autonomy but expects final results                |
| **Community-Focused Owner** | Values stability, character, and local attachment                  |

The owner determines:

```text
Budget
Tax willingness
GM authority
Job security
Staff budget
Rebuild tolerance
Star preference
Public expectations
Transaction veto threshold
```

The GM determines how effectively the organization works within those constraints.

---

### 8.7 Competitive phase

Each team maintains scores across:

```text
All-In Contender
Sustainable Contender
Ascending Team
Competitive Retool
Asset Accumulation
Development Rebuild
Transition
Directionless
```

The actual best state and the GM's perceived state can differ. Inputs include team strength, championship probability, star quality, age, health, contracts, cap flexibility, picks, prospects, owner patience, market pressure, staff quality, and available transaction markets.

Use hysteresis: the phase changes only after meaningful evidence, checkpoints, injuries, transactions, playoff outcomes, contracts, or leadership changes. Reactive GMs change too quickly; rigid GMs change too slowly.

### 8.8 Planning horizons

Value every asset across:

```text
NOW  — current season and next postseason
NEAR — next two to three seasons
LONG — four to seven seasons
OPTIONALITY — flexibility and future choices
```

Suggested starting weights:

| Phase | Now | Near | Long | Optionality |
|---|---:|---:|---:|---:|
| All-In Contender | 55% | 25% | 5% | 15% |
| Sustainable Contender | 40% | 30% | 15% | 15% |
| Ascending | 25% | 35% | 25% | 15% |
| Competitive Retool | 30% | 30% | 20% | 20% |
| Asset Accumulation | 10% | 25% | 35% | 30% |
| Development Rebuild | 10% | 30% | 35% | 25% |
| Transition | 25% | 25% | 20% | 30% |

### 8.9 AI decision cycle

```text
1. Observe roster, health, staff, finances, assets, and market
2. Estimate current and future state
3. Set priorities
4. Generate legal options
5. Evaluate scenarios and alternatives
6. Compare against best known alternative
7. Negotiate according to leverage and personality
8. Run organizational and roster audit
9. Execute or walk away
10. Update plans, relationships, and market information
```

Run full reviews at the offseason, draft, free agency, training camp, early season, major injury, midseason, trade deadline, playoff elimination, and major staff departure.

### 8.10 Asset valuation

There is no universal trade value.

```text
teamSpecificAssetValue =
  expectedBasketballValueByHorizon
  + contractSurplus
  + teamControl
  + optionValue
  + rosterFit
  + coachFit
  + skillScarcity
  + ownerMarketValue
  + developmentFit
  - injuryRisk
  - salaryRestriction
  - redundancy
  - opportunityCost
  - transactionFriction

gmPerceivedValue =
  teamSpecificAssetValue
  + philosophyAdjustment
  + structuredBias
  + informationError
  + negotiationAdjustment
```

Information error applies to the uncertain portion of value, not obvious superstar-level differences.

### 8.11 Trade acceptance and anti-exploitation

```text
tradeDelta =
  valueReceived
  - valueSent
  + strategicShiftValue
  + capFlexibilityChange
  + rosterBalanceChange
  - transactionCosts
```

Accept only when:

```text
tradeDelta >= requiredSurplusMargin
AND offerValue >= bestKnownAlternative - searchTolerance
AND transactionIsLegal
AND postTradeRosterIsViable
```

Required margin varies by risk tolerance, leverage, deadline, player request, salary pressure, owner pressure, bidders, confidence, relationships, and asset importance.

Required safeguards:

- Package-level valuation, not item-by-item addition.
- Legal salary, roster, and pick validation before an offer exists.
- AI-to-AI bidding and a best-alternative search.
- Explicit price for cap relief and negative contracts.
- Protected-pick and swap valuation.
- Negotiation memory and private walk-away thresholds.
- Rolling audit against splitting one exploit into several trades.
- Post-trade role, lineup, development, and injury-contingency audit.
- Second-stage review before trading a franchise player, best prospect, unprotected pick, three premium picks, or major long-term salary.

Bad GMs can make poor deals, but repeated button pressing must not turn them into vending machines.

### 8.12 Negotiation styles


Each GM should have a negotiation identity.

| Style                      | Behavior                                                     |
| -------------------------- | ------------------------------------------------------------ |
| **Hardline Valuator**      | Makes firm offers and walks away quickly                     |
| **Patient Auctioneer**     | Shops assets broadly and waits for market development        |
| **Relationship Dealer**    | Values repeat partners and collaborative negotiations        |
| **Aggressive Closer**      | Pushes quickly toward completion                             |
| **Creative Broker**        | Uses protections, swaps, third teams, and complex structures |
| **Quiet Operator**         | Avoids leaks and makes fewer public offers                   |
| **Public Market Maker**    | Uses the trade block to create bidding competition           |
| **Deadline Hunter**        | Waits for leverage to change near deadlines                  |
| **Exploratory Negotiator** | Discusses many possibilities but completes fewer             |
| **Prideful Negotiator**    | Dislikes reversing demands or admitting misvaluation         |

## Negotiation memory

Track:

```text
Fair-deal history
Lowball frequency
Leaked discussions
Broken promises
Abandoned agreements
Previous successful transactions
Relationship between executives
Public criticism
Tampering or trust issues
```

Repeated lowballing should not make the AI surrender. It should make the other GM:

* Stop returning calls temporarily.
* Demand a clearer opening offer.
* Remove certain assets from discussion.
* Shop the player elsewhere.
* Require a small trust premium.
* Leak that the user is making unserious offers.

---

### 8.13 Draft, free agency, and contracts

**Draft**

Each team builds a private board from scouting, analytics, medical, interviews, workouts, role projections, coach fit, development fit, need, risk tolerance, and bias. Use outcome distributions, not a causal potential rating. Draft within talent tiers; compare fit and scarcity inside a tier. Trade up only when conviction and scarcity exceed cost, lost optionality, and downside.

**Free agency**

Player choice considers guaranteed salary, security, role, minutes, contention, market, coach, GM, teammates, development, and stability. GM valuation considers projected value, age, health, role, alternatives, flexibility, tax, owner budget, and player willingness. AI teams submit competing offers, withdraw at excessive prices, and use backup plans.

**Contracts**

Evaluate each season's production, role value, availability, salary cost, cap restriction, retention value, trade option value, and downside. Include guarantees, options, incentives, age decline, health, scarcity, market comparables, rights, re-sign likelihood, and dissatisfaction risk.

### 8.14 Staff hiring

The GM hires the systems defined elsewhere.

```text
Coach score:
tacticalFit + rosterFit + timelineFit + developmentFit + leadershipNeed
+ staffNetwork + ownerPreference + playerReaction + salaryFit
- philosophyConflict

Medical score:
rosterHealthNeed + clinicalQuality + rehabFit + preventionFit
+ playerTrust + independenceFit - departmentCost

Development score:
prospectNeeds + skillDeficits + headCoachAlignment + teaching
+ gameTransfer + capacity + affiliateFit
```

### 8.15 League-quality distributions

At a 30-team league start, generate independently:

```text
GM quality:
5 Elite
5 Strong
10 Competent or Mixed
5 Weak
5 Dysfunctional

Current team state:
5 Contenders
5 Strong Teams
10 Middle or Uncertain Teams
5 Coherent Rebuilds
5 Broken or Bottom Teams
```

Cross the distributions rather than matching them. A poor GM can inherit a contender; an elite GM can inherit a broken team.

After creation, stop enforcing quotas. Careers evolve through promotion, retirement, owner quality, burnout, learning, staff poaching, and hiring mistakes.

### 8.16 Strategic archetypes


A GM should normally combine two archetypes.

| Archetype                     | Core behavior                                                 | Failure mode                             |
| ----------------------------- | ------------------------------------------------------------- | ---------------------------------------- |
| **Portfolio Architect**       | Balances players, picks, contracts, and optionality           | Can delay decisive consolidation         |
| **Patient Asset Compounder**  | Repeatedly converts current value into future value           | Can remain in accumulation too long      |
| **Star Cycle Manager**        | Acquires stars, competes, then recovers value before collapse | Can sacrifice depth and continuity       |
| **Draft-and-Develop Builder** | Builds through drafting and internal teaching                 | Overestimates development system         |
| **Aggressive Retooler**       | Changes supporting cast without full teardown                 | Excessive roster churn                   |
| **Cap Optionality Operator**  | Protects flexibility and exploits salary pressure             | May pass on expensive elite talent       |
| **Second-Draft Miner**        | Targets young players undervalued elsewhere                   | Roster becomes crowded with projects     |
| **Veteran Floor Raiser**      | Uses dependable veterans to stabilize performance             | Produces aging, low-ceiling rosters      |
| **Coach-Centric Constructor** | Acquires players specifically for the coach                   | Becomes trapped by coaching changes      |
| **Talent-First Collector**    | Selects the strongest talent regardless of fit                | Creates role duplication                 |
| **Fit-First Constructor**     | Builds highly coherent lineups and roles                      | Passes on superior raw talent            |
| **Small-Market Compounder**   | Retention, development, controlled contracts, selective risk  | Avoids rare all-in opportunity           |
| **Big-Market Aggressor**      | Uses free agency, star interest, and spending power           | Overpays for reputation                  |
| **Continuity Executive**      | Retains players and staff to build institutional stability    | Maintains declining groups too long      |
| **Deadline Hunter**           | Exploits changing leverage near transaction deadlines         | Waits too long or overreacts late        |
| **Upside Gambler**            | Targets high-ceiling players and distressed assets            | High bust and injury variance            |
| **Certainty Buyer**           | Values established production and stable contracts            | Pays for declining veterans              |
| **Organizational Developer**  | Invests heavily in staff, affiliates, and internal systems    | Immediate roster can remain underpowered |
| **Trade-Network Broker**      | Maintains many active executive relationships                 | Information leaks and overactivity       |
| **Contrarian Valuator**       | Intentionally targets players the market dislikes             | Can become stubbornly wrong              |

With 20 strategic archetypes, 12 roster preference packages, 10 negotiation styles, 10 backgrounds, and 20 possible biases, the game can generate substantial variation without creating hundreds of unrelated hard-coded personalities.

---

### 8.17 Roster preference packages


| Roster identity               | GM preference                                              | Common cost                             |
| ----------------------------- | ---------------------------------------------------------- | --------------------------------------- |
| **Star and Specialists**      | One or two elite creators with narrow role players         | Dependence on stars                     |
| **Multi-Creator Balance**     | Several players who can initiate offense                   | Fewer elite specialists                 |
| **Shooting Everywhere**       | Strong spacing at nearly every position                    | Rebounding and defense may suffer       |
| **Defense and Length**        | Size, switching, rim protection, and disruption            | Half-court creation may be limited      |
| **Positionless Versatility**  | Players who cover several roles                            | Can lack dominant primary skills        |
| **Interior Power**            | Size, rebounding, rim pressure, and post play              | Spacing and transition speed            |
| **Athletic Pressure**         | Speed, vertical ability, and defensive aggression          | Decision-making and shooting variance   |
| **Basketball-IQ Collective**  | Passing, positioning, role understanding, and low mistakes | Lower physical ceiling                  |
| **Deep Rotation**             | Ten or more credible contributors                          | Less top-end concentration              |
| **Durability and Continuity** | Reliable availability and stable roles                     | Misses discounted injury-risk talent    |
| **Young Upside Portfolio**    | Several developmental bets                                 | Role congestion and unstable production |
| **Veteran Execution**         | Experienced players with known roles                       | Aging and limited future value          |

---

### 8.18 GM traits


| Trait                         | Advantage                                          | Cost                                        |
| ----------------------------- | -------------------------------------------------- | ------------------------------------------- |
| **Never Pays Retail**         | Avoids overpaying in trades                        | Misses premium targets                      |
| **Closer**                    | Finishes complicated transactions                  | Sometimes gives the final unnecessary asset |
| **Pick Protector**            | Preserves future draft capital                     | Fails to consolidate during contention      |
| **No Sacred Cows**            | Corrects mistakes and moves popular players        | Damages loyalty and trust                   |
| **Homegrown Premium**         | Retains internal talent and continuity             | Overpays own players                        |
| **Cap Cleaner**               | Escapes bad salary structures                      | Sacrifices picks or useful players          |
| **Second-Draft Specialist**   | Finds undervalued young players                    | Uses too many roster spots on projects      |
| **Star Magnet**               | Strong relationships with elite players and agents | Neglects depth                              |
| **Small-Market Connector**    | Improves retention and trust                       | Less access to glamorous targets            |
| **Coach Shield**              | Creates staff stability                            | Fires failing coaches too slowly            |
| **Quick Trigger**             | Corrects staff mistakes rapidly                    | Organizational instability                  |
| **Medical Conservative**      | Avoids severe health downside                      | Passes on discounted opportunities          |
| **Injury Gambler**            | Buys talented players at reduced prices            | Setback and availability risk               |
| **Staff Incubator**           | Develops assistant executives and coaches          | Staff is frequently hired away              |
| **Owner Whisperer**           | Gains budget and patience                          | Can become too owner-driven                 |
| **Trade Network**             | Receives more market information                   | More leaks and exploratory distractions     |
| **Quiet Operator**            | Protects leverage and confidentiality              | Generates fewer external opportunities      |
| **International Pipeline**    | Finds broader talent sources                       | Greater projection uncertainty              |
| **Deadline Discipline**       | Avoids panic moves                                 | May fail to react to real opportunity       |
| **Public Pressure Resistant** | Maintains plan during criticism                    | Can appear unresponsive                     |
| **Admits Mistakes**           | Exits poor decisions quickly                       | May sell low before recovery                |
| **Conviction Drafter**        | Acts decisively when talent tier changes           | Can overpay to move up                      |
| **Contract Structurer**       | Creates useful options and flexibility             | May lose players demanding simplicity       |
| **Player Advocate**           | Builds trust and retention                         | Occasionally pays relationship premiums     |

---

### 8.19 GM career and evaluation

Executives progress through scouting, analytics, cap, development, personnel, assistant-GM, GM, and president roles. Improvement comes from actual responsibilities and results. Success can create overconfidence; failure can improve accountability or increase defensiveness.

Evaluate a GM by inherited position, asset-value growth, competitive conversion, draft value, trade value, contract efficiency, cap flexibility, roster coherence, staff quality, development alignment, health-risk decisions, strategic coherence, timeline accuracy, owner management, and process versus luck.

### 8.20 GM profile library


Internal ratings are shown in this order:

```text
EVAL / DEALS / BUILD / STRATEGY / OPERATIONS
```

These exact numbers would not normally be visible to the player.

#### Five elite GMs

| GM               | Internal ratings       | Identity                                   | Principal limitation                         |
| ---------------- | ---------------------- | ------------------------------------------ | -------------------------------------------- |
| **Elena Voss**   | 91 / 93 / 90 / 95 / 88 | Portfolio Architect and Patient Auctioneer | Occasionally waits too long to consolidate   |
| **Marcus Hale**  | 87 / 95 / 92 / 89 / 90 | Star Cycle Manager and Aggressive Closer   | Compresses depth and future flexibility      |
| **Priya Raman**  | 96 / 84 / 91 / 94 / 93 | Draft-and-Development Integrator           | Hesitant in expensive veteran free agency    |
| **Darius Cole**  | 86 / 91 / 94 / 96 / 87 | Adaptive Retooler and Contrarian Valuator  | High roster turnover                         |
| **Mateo Ibarra** | 92 / 88 / 89 / 93 / 96 | Small-Market Asset Compounder              | Sometimes declines the necessary all-in risk |

##### Elena Voss — full behavior

Voss treats the roster as a portfolio. She values top-end talent, but she also tracks contract control, pick timing, development capacity, and future flexibility. She rarely loses badly in a trade.

She is difficult for the human player because she shops important assets, understands alternatives, and does not confuse cap space with value. She can nevertheless miss a championship window by waiting for a perfect consolidation deal.

```text
Primary archetypes:
Portfolio Architect
Cap Optionality Operator

Roster taste:
Multi-Creator Balance

Negotiation:
Patient Auctioneer

Bias:
Mild option-value overprotection
```

##### Marcus Hale — full behavior

Hale is comfortable surrendering future assets when the roster has a genuine championship window. He is also good at recognizing when a star cycle is ending and recovering value before a complete collapse.

His teams frequently possess two or three premium players and a thin middle class. When injuries hit, the lack of depth becomes obvious.

```text
Primary archetypes:
Star Cycle Manager
Big-Market Aggressor

Roster taste:
Star and Specialists

Negotiation:
Aggressive Closer

Bias:
Mild star halo
```

##### Priya Raman — full behavior

Raman builds an integrated scouting, development, and coaching pipeline. She drafts according to role outcomes rather than position labels and rarely gives up on a prospect without a clear organizational reason.

She can be too patient and sometimes misses veterans who would accelerate a young team’s rise.

```text
Primary archetypes:
Draft-and-Develop Builder
Organizational Developer

Roster taste:
Positionless Versatility

Negotiation:
Relationship Dealer

Bias:
Internal-development confidence
```

##### Darius Cole — full behavior

Cole is exceptional at recognizing when the current plan has stopped working. He changes coaches, roster roles, and acquisition priorities without requiring a full teardown.

The downside is churn. Players and staff can feel that the organization is constantly being redesigned.

```text
Primary archetypes:
Aggressive Retooler
Contrarian Valuator

Roster taste:
Talent First

Negotiation:
Creative Broker

Bias:
Action bias, mild
```

##### Mateo Ibarra — full behavior

Ibarra is designed for a smaller or financially constrained organization. He finds surplus contracts, retains suitable stars, develops staff, and avoids long dead-money commitments.

His weakness is the fear that one failed all-in move will destroy the organization. He may preserve future options after the team has become ready to contend.

```text
Primary archetypes:
Small-Market Compounder
Continuity Executive

Roster taste:
Durability and Continuity

Negotiation:
Hardline Valuator

Bias:
Risk aversion, mild
```


#### Five strong GMs

| GM                 | Internal ratings       | Identity                           | Principal limitation                      |
| ------------------ | ---------------------- | ---------------------------------- | ----------------------------------------- |
| **Simone Grant**   | 82 / 80 / 91 / 87 / 94 | Coach-Aligned Organization Builder | Can overfit roster to current coach       |
| **Kenji Watanabe** | 79 / 94 / 84 / 91 / 88 | Cap Optionality Operator           | Occasionally too financially conservative |
| **Amara Okafor**   | 86 / 82 / 93 / 87 / 85 | Versatility and Two-Way Builder    | Can lack elite half-court creation        |
| **Luis Mendoza**   | 78 / 95 / 82 / 85 / 89 | Trade-Network Broker               | Explores too many moves                   |
| **Rachel Kim**     | 91 / 84 / 86 / 90 / 81 | Analytics and Scouting Hybrid      | Average player and agent relationships    |

These GMs should regularly beat a careless human user, particularly when operating within their specialties.


#### Ten competent but mixed GMs

| GM                  | Internal ratings       | Identity                         | Principal limitation                   |
| ------------------- | ---------------------- | -------------------------------- | -------------------------------------- |
| **Adrian Knox**     | 75 / 74 / 77 / 76 / 80 | Balanced Conventional Generalist | No major competitive edge              |
| **Nia Foster**      | 71 / 67 / 78 / 74 / 90 | Culture and Retention Executive  | Overpays internal players              |
| **Pavel Markovic**  | 88 / 69 / 75 / 79 / 70 | International Talent Evaluator   | Weak contract and domestic market work |
| **Jordan Bell**     | 80 / 78 / 79 / 71 / 73 | Second-Draft Miner               | Accumulates too many projects          |
| **Camille Laurent** | 72 / 76 / 84 / 72 / 82 | Coach-Centric Constructor        | Gives coach too much roster control    |
| **Malcolm Reed**    | 69 / 81 / 79 / 66 / 85 | Veteran Floor Raiser             | Underestimates age decline             |
| **Leila Haddad**    | 84 / 70 / 76 / 74 / 69 | Upside Gambler                   | High prospect bust variance            |
| **Thomas Wynn**     | 68 / 86 / 72 / 80 / 82 | Financial Conservative           | Misses expensive upgrades              |
| **Gabriela Santos** | 78 / 73 / 86 / 75 / 74 | Defense-and-Length Builder       | Repeated shooting shortages            |
| **Owen Price**      | 74 / 82 / 73 / 69 / 87 | Public-Pressure Operator         | Becomes too short-term under criticism |

These are the most important class of GMs. They prevent the league from becoming five geniuses and twenty-five idiots.

Each should be capable of:

* Making strong moves in their specialty.
* Winning when roster and coach fit align.
* Making believable mistakes.
* Changing reputation over time.
* Becoming strong or weak through career development.


#### Five weak GMs

| GM                 | Internal ratings       | Identity                  | Principal limitation                         |
| ------------------ | ---------------------- | ------------------------- | -------------------------------------------- |
| **Victor Shaw**    | 79 / 54 / 65 / 57 / 69 | Prospect Hoarder          | Never consolidates assets                    |
| **Helena Brooks**  | 66 / 60 / 58 / 63 / 78 | Loyalty-Captive Executive | Sunk-cost extensions and delayed trades      |
| **Ramon Ellis**    | 72 / 62 / 67 / 52 / 71 | Star Chaser               | Pays for fame without sufficient fit         |
| **Derek Lin**      | 53 / 91 / 59 / 64 / 75 | Cap Technician            | Excellent contracts, poor talent judgment    |
| **Monique Carter** | 63 / 68 / 62 / 49 / 79 | Reactive Retooler         | Changes plans after short performance swings |

##### Victor Shaw

Shaw is not stupid. His scouting is good. His problem is that he becomes attached to every prospect with a high-end outcome.

He repeatedly refuses sensible consolidation deals, carries too many young players, and eventually faces simultaneous extension decisions.

The human can acquire veterans from Shaw during a rebuild, but cannot easily obtain his premium prospects or first-round picks.

##### Derek Lin

Lin is one of the league’s best cap technicians. His contracts usually include favorable structures and useful flexibility.

Unfortunately, he is poor at deciding which players deserve those contracts. His organization remains financially clean while basketball talent stagnates.

This is the type of weak GM who feels real because the weakness is specific.


#### Five dysfunctional GMs

| GM                | Internal ratings       | Identity                 | Principal limitation                                |
| ----------------- | ---------------------- | ------------------------ | --------------------------------------------------- |
| **Bryce Stanton** | 57 / 82 / 47 / 39 / 62 | Reckless Closer          | Completes deals without strategic discipline        |
| **Gerald Moss**   | 45 / 52 / 61 / 43 / 74 | Reputation Scout         | Overvalues famous and previously successful players |
| **Tessa Vaughn**  | 65 / 58 / 49 / 36 / 86 | Owner Puppet             | Strong politics, no independent direction           |
| **Colin Mercer**  | 59 / 73 / 43 / 31 / 52 | Directionless Trader     | Contradictory acquisitions and constant churn       |
| **Frank Delgado** | 48 / 49 / 54 / 41 / 70 | Sunk-Cost Traditionalist | Retains declining veterans and stale evaluations    |

##### Bryce Stanton

Stanton is a good negotiator in the narrow sense that he can close complicated transactions. His problem is that he frequently negotiates the wrong transaction.

He may successfully acquire a star but fail to preserve adequate depth, shooting, or future salary flexibility. His teams can become dangerous for one season and collapse afterward.

##### Tessa Vaughn

Vaughn has excellent owner relationships and unusually strong job security. She changes direction whenever ownership changes priorities.

The team can move from rebuild to star pursuit to cost cutting within eighteen months. Individual transactions may appear defensible, but the combined plan is incoherent.

##### Colin Mercer

Mercer enjoys being active. He frequently moves mid-level players, changes roster identity, and announces new directions.

His organization loses continuity, development plans are interrupted, and trade partners learn that he is often willing to reopen discussions.

A strong human can exploit Mercer occasionally. Repeated exploitation should trigger owner review, competing offers, and negotiation memory.

---

## 9. Scouting system

### 9.1 Core rule

Scouting reduces uncertainty; it never eliminates it. Separate:

```text
True player ability and development probabilities
Observable performance
Scout estimate
Analytics estimate
Coach fit assessment
Development teachability assessment
Medical evaluation
GM interpretation and final value
```

### 9.2 Settings

Department depth and fog of war are separate.

| Fog setting | Information |
|---|---|
| None | Current ratings visible; scouts still report fit, role, personality, market, and opponent information |
| Light | Narrow current-skill ranges; future remains uncertain |
| Standard — default | Current skills, fit, translation, and future all have meaningful uncertainty |
| Harsh | Wider ranges, stronger regional effects, slower crosschecking |
| Custom | Separate controls for current ability, projection, personality, medical, and tactical fit |

### 9.3 Public pillars

| Pillar | Meaning |
|---|---|
| **Evaluation** | Present basketball skills and weaknesses |
| **Projection** | Future role, growth, decline, and competition translation |
| **Fit & Context** | Scheme, lineup, role, and organizational suitability |
| **Information & Network** | Access, regional knowledge, interviews, sources, and market intelligence |
| **Synthesis & Operations** | Report clarity, crosschecking, calibration, workload, and organization |

### 9.4 Required scout attributes

```text
Present evaluation:
overallTalent, shooting, finishing, ballHandling, passing, offBall,
interiorDefense, perimeterDefense, teamDefense, rebounding,
athleticism, basketballIQ

Projection:
futureProjection, skillGrowth, physicalProjection, ageCurve,
roleProjection, competitionTranslation, shootingTranslation,
defensiveTranslation, lateBloomerRecognition, floor, ceiling,
developmentEnvironmentFit

Information:
liveEvaluation, videoEvaluation, interviewing, backgroundResearch,
sourceNetwork, regionalKnowledge, marketIntelligence,
measurementInterpretation, statisticalLiteracy, medicalFlagRecognition

Synthesis and operations:
uncertaintyCalibration, crosschecking, reportWriting, evidenceWeighting,
biasResistance, memoryContinuity, revisionAbility, assignmentManagement,
coveragePlanning, deadlineManagement, staffDevelopment, gmCommunication
```

### 9.5 Scout tendencies


Ability determines how well the scout evaluates. Tendencies determine what the scout tends to value.

| Tendency                        | Low end                                  | High end                                  |
| ------------------------------- | ---------------------------------------- | ----------------------------------------- |
| **Production versus Tools**     | Values demonstrated performance          | Values physical and skill upside          |
| **Floor versus Ceiling**        | Prioritizes dependable outcomes          | Prioritizes star-level possibilities      |
| **Live versus Data**            | Relies on film and in-person observation | Relies on models and statistical evidence |
| **Talent versus Fit**           | Values general talent                    | Values current organizational fit         |
| **Current versus Future**       | Prioritizes immediate contribution       | Prioritizes future outcome                |
| **Technique versus Results**    | Values current production                | Studies mechanics and process             |
| **Consensus versus Contrarian** | Follows market agreement                 | Willing to diverge substantially          |
| **Certainty Threshold**         | Recommends with limited evidence         | Requires extensive evidence               |
| **Character Weighting**         | Treats behavior as secondary             | Heavily weighs habits and role acceptance |
| **Medical-Risk Sensitivity**    | Accepts health uncertainty               | Strongly discounts risk flags             |
| **Age Preference**              | Values youth                             | Values proven maturity                    |
| **Athleticism Preference**      | Values skill and positioning             | Values physical tools                     |
| **Size Preference**             | Comfortable with undersized players      | Strongly values positional size           |
| **Versatility Preference**      | Values specialists                       | Values multi-role players                 |
| **Recommendation Aggression**   | Uses cautious grades                     | Makes strong declarations                 |
| **Report Detail**               | Short executive summaries                | Extensive evidence and qualification      |

A high ceiling preference is not the same as excellent ceiling evaluation.

---

### 9.6 Scout biases


Mistakes should emerge from identifiable biases rather than arbitrary error.

| Bias                          | Result                                                        |
| ----------------------------- | ------------------------------------------------------------- |
| **Pedigree Bias**             | Overvalues prestigious teams, programs, or leagues            |
| **Small-Program Discount**    | Undervalues players from weaker competition                   |
| **Athleticism Bias**          | Overvalues testing and physical tools                         |
| **Production Bias**           | Assumes college or lower-league production transfers directly |
| **Youth Bias**                | Treats age as upside regardless of skill base                 |
| **Veteran Certainty Bias**    | Overvalues known professional production                      |
| **Shooting-Percentage Bias**  | Confuses current percentage with underlying shooting quality  |
| **Role-Player Blindness**     | Misses players with narrow but valuable professional roles    |
| **Star-Outcome Fixation**     | Overweights unlikely ceiling outcomes                         |
| **Recency Bias**              | Overreacts to recent tournaments, playoffs, or workouts       |
| **Combine Overreaction**      | Changes evaluation too strongly after testing                 |
| **Interview Overconfidence**  | Treats polished interviews as reliable character evidence     |
| **Character-Rumor Bias**      | Gives too much weight to weak or anonymous sources            |
| **Medical Overreaction**      | Treats any health flag as disqualifying                       |
| **Medical Underreaction**     | Assumes talent outweighs all health concerns                  |
| **Coach-Capture Bias**        | Values only players suited to the current coach               |
| **Model Overconfidence**      | Treats analytical projection as certainty                     |
| **Eye-Test Overconfidence**   | Rejects statistical evidence too readily                      |
| **Consensus Anchoring**       | Rarely moves far from leaguewide opinion                      |
| **Contrarian Pride**          | Maintains an unusual opinion after contrary evidence grows    |
| **Sunk-Report Attachment**    | Refuses to revise a long-held evaluation                      |
| **Body-Type Comparison Bias** | Assumes physically similar players will develop similarly     |

Good departments should not eliminate bias. They should identify and counterbalance it through diverse staff and crosschecking.

---

### 9.7 Information categories and persistence

**Usually exact:** age, contract, team, public statistics, verified measurements, transaction history, public absences, draft rights, awards, role, and minutes.

**Estimated:** shooting versatility, defensive positioning, handle under pressure, passing reads, athletic function, rebounding translation, decision speed, effort consistency, role flexibility, and system dependence.

**Projected:** future role, skill growth, decline, star/starter/rotation probabilities, role conversion, durability, and league translation.

**Restricted:** medical examination, private history, confidential wellness information, interviews, agent demands, internal conflicts, and personal matters.

Knowledge stages:

```text
Publicly Known
Preliminary File
Initial Scout
Follow-Up Scout
Crosschecked
Decision Ready
Organizational Knowledge
Stale Knowledge
```

Do not erase institutional knowledge when a player leaves. Stable facts barely decay; current form and fit decay moderately; injury status, trade availability, agent demands, and role satisfaction decay quickly.

### 9.8 Observation and estimation

Each observation records player, scout, date, type, competition, opponent, role, minutes, live/video, relevant actions, context diversity, conclusion, and confidence. Repeating the same context produces diminishing information.

```text
scoutObservation =
  trueCurrentSkill
  + scoutSystematicBias
  + contextError
  + randomObservationError

observationPrecision =
  eventInformationQuality
  * scoutRelevantAbility
  * specialtyFit
  * regionalKnowledge
  * accessQuality
  * contextRelevance
  * sampleDiversity
  * reportFreshness

estimatedSkill =
  weightedAverage(
    organizationalPrior,
    publicPerformanceModel,
    scoutObservations,
    internalHistory
  )

remainingUncertainty =
  baseUncertainty
  / sqrt(priorPrecision + totalIndependentObservationPrecision)

scoutDisagreement =
  weightedStandardDeviation(independentScoutEstimates)
```

Show confidence and disagreement separately. Additional reports gain value only when the evidence is meaningfully independent; otherwise groupthink can produce false confidence.

### 9.9 Future outcomes

Potential is an estimate, not a growth force. Display a distribution such as:

```text
Out of league 8%
End of bench 18%
Rotation 31%
Starter 24%
High-level starter 13%
All-Star 5%
Franchise player 1%
```

The distribution can be wrong because present evaluation, age curves, translation, and development assumptions can be wrong.

### 9.10 Reports and boards

A decision-ready report answers:

```text
Current abilities
Likely professional role
Outcome distribution
Evidence for and against
Major uncertainty
Scout disagreement
Coach and development fit
Medical flags
Roster congestion
Expected acquisition range or cost
Recommended next action
```

Draft boards use talent tiers rather than one perfectly sorted list. Combine measurements, testing, shooting, drills, scrimmages, interviews, workouts, and medical review provide different evidence; no single event should dominate.

### 9.11 Assignments and capacity

Recruitment focuses must be basketball questions, for example:

```text
Find a backup center who defends drop, rebounds, accepts 12–18 minutes,
costs under $8 million, and does not require a first-round pick.
```

Very broad focuses find surprises but create noise. Very narrow focuses are efficient but may return nothing and reinforce assumptions.

```text
effectiveDepartmentCapacity =
  baseScoutCapacity
  * operationsQuality
  * travelSupport
  * videoInfrastructure
  * departmentCohesion
```

Overload causes late reports, canceled crosschecks, stale regions, generic conclusions, and excessive video dependence.

### 9.12 Scouting department identities


| Department identity                | Strength                                           | Failure mode                                             |
| ---------------------------------- | -------------------------------------------------- | -------------------------------------------------------- |
| **Hybrid Consensus Department**    | Combines live, video, data, and crosschecks        | Slow decisions and diluted conviction                    |
| **Traditional Live Network**       | Strong relationships and contextual observation    | Lower coverage and weaker data synthesis                 |
| **Model-Driven Department**        | Efficient broad coverage and market comparisons    | Model blind spots and weak personal context              |
| **International Pipeline**         | Finds players before domestic competitors          | Less professional-league coverage                        |
| **College Coverage Machine**       | Deep draft-class knowledge                         | Limited current professional scouting                    |
| **Pro Personnel Specialists**      | Trades, free agents, waivers, and role players     | Less prospect projection                                 |
| **Second-Draft Laboratory**        | Finds discarded young players                      | Roster congestion and many failed projects               |
| **Upside Projection Department**   | Identifies high-ceiling players                    | High bust rate                                           |
| **Floor and Role Department**      | Finds dependable professional contributors         | Misses stars                                             |
| **Character-First Department**     | Strong role acceptance and reliability information | May undervalue difficult personalities with elite talent |
| **Fit-First Department**           | Strong coach and lineup matching                   | Becomes dependent on current system                      |
| **Contrarian Department**          | Finds players the market undervalues               | Can become stubbornly wrong                              |
| **Budget Targeting Unit**          | Excellent narrow assignments at low cost           | Poor leaguewide coverage                                 |
| **Information Network Department** | Strong market intelligence and source access       | Risk of leaks and reputation-based evaluation            |

---

### 9.13 AI scouting safeguards

AI teams use their own reports and never access true ratings. The process is:

```text
GM direction
→ roster needs
→ assignments
→ evidence
→ reports
→ crosschecks
→ coaching/development/analytics/medical input
→ private board
→ decision under remaining uncertainty
```

Before a lottery pick, unprotected-pick trade, best-prospect trade, major contract, medically risky star acquisition, franchise-player trade, or little-scouted international selection, require a minimum report status, independent crosscheck, medical review when relevant, coach/development fit, and final GM audit. Dysfunctional organizations may waive safeguards for identifiable reasons.

Generate scouting department quality independently from GM quality:

```text
5 Elite
5 Strong
10 Competent or Mixed
5 Weak
5 Dysfunctional
```

### 9.14 Scouting profile library


#### S01. Maya Ortiz — Complete Department Architect

**Age 49 · Director of Scouting**
**EVA 91 · PRO 95 · FIT 90 · NET 84 · OPS 97**

Ortiz builds balanced boards, demands independent reports, and communicates uncertainty clearly. She is especially strong when deciding whether an unusual prospect deserves a premium pick.

Her caution can slow decisions, and she sometimes requests one more crosscheck when the market requires speed.

**Specialties:** Board calibration, wing projection, crosschecking
**Bias:** Mild evidence conservatism
**Best organization:** Team seeking a complete long-term scouting infrastructure

---

#### S02. Dean Holloway — Traditional Live Evaluator

**Age 61 · Senior Amateur Scout**
**EVA 96 · PRO 82 · FIT 88 · NET 95 · OPS 70**

Holloway understands live context: effort away from the ball, communication, response to coaching, and performance when the game changes.

He distrusts model-heavy conclusions and can underestimate players whose value is difficult to see in person.

**Specialties:** Live college games, competitive temperament, guards
**Bias:** Eye-test overconfidence
**Best organization:** Data-heavy department needing a strong live evaluator

---

#### S03. Priya Menon — Projection and Uncertainty Specialist

**Age 38 · Scouting Analyst/Crosschecker**
**EVA 86 · PRO 98 · FIT 89 · NET 72 · OPS 96**

Menon creates career-outcome distributions and is excellent at distinguishing uncertainty from weakness. She prevents the department from treating a low-confidence player as a bad player.

She has limited source relationships and needs live scouts to provide context her models cannot capture.

**Specialties:** Age curves, probability calibration, draft tiers
**Bias:** Mild model dependence
**Best organization:** Traditional department modernizing its process

---

#### S04. Amina Yusuf — International Pipeline Director

**Age 44 · Director of International Scouting**
**EVA 90 · PRO 94 · FIT 86 · NET 98 · OPS 84**

Yusuf understands competition levels, professional roles, contract structures, and cultural context across several international systems.

Her domestic college coverage is ordinary, and she can overestimate how quickly adaptable international professionals will adjust to a different tactical environment.

**Specialties:** European leagues, African academies, competition translation
**Bias:** International adaptability optimism
**Best organization:** Team investing in a global talent pipeline

---

#### S05. Marcus Bell — Professional Role Scout

**Age 53 · Director of Professional Personnel**
**EVA 94 · PRO 80 · FIT 97 · NET 92 · OPS 88**

Bell is excellent at identifying what current professionals can do in a different role. He finds seventh men, defensive connectors, backup creators, and veterans capable of reduced responsibilities.

He is less effective when evaluating very young, raw prospects.

**Specialties:** Role players, trade targets, veteran role changes
**Bias:** Veteran certainty
**Best organization:** Contender seeking precise supporting pieces

---

#### S06. Keisha Grant — Second-Draft Scout

**Age 39 · G League and Emerging Talent Scout**
**EVA 88 · PRO 93 · FIT 91 · NET 90 · OPS 81**

Grant finds young players who were drafted into poor situations, blocked by veterans, or assigned unsuitable roles.

Her recommendations produce many inexpensive successes but also occupy numerous roster and development slots.

**Specialties:** G League, waived prospects, role reclamation
**Bias:** Development optimism
**Best organization:** Patient team with affiliate capacity

---

#### S07. Kenji Sato — Shooting Translation Specialist

**Age 47 · Amateur Crosschecker**
**EVA 91 · PRO 96 · FIT 84 · NET 76 · OPS 89**

Sato distinguishes current percentages from underlying shooting indicators such as preparation, balance, touch, release speed, shot versatility, and confidence.

He can give too much weight to shooting development when a player has larger decision-making or defensive limitations.

**Specialties:** Shooting mechanics, free-throw translation, movement shooting
**Bias:** Shooting-fix optimism
**Best organization:** Team with an elite shooting-development staff

---

#### S08. Darnell Price — Defensive Projection Scout

**Age 45 · Professional and Amateur Scout**
**EVA 95 · PRO 89 · FIT 96 · NET 80 · OPS 83**

Price evaluates screen navigation, help timing, recovery, physical matchup range, and defensive role translation. He finds defenders whose value is hidden by weak team environments.

He undervalues offensive specialists and can recommend lineups with insufficient creation.

**Specialties:** Perimeter defense, switchability, team defense
**Bias:** Defense-first evaluation
**Best organization:** Offensive team needing defensive balance

---

#### S09. Elena Varga — Background and Interview Specialist

**Age 42 · Scouting Intelligence Director**
**EVA 79 · PRO 82 · FIT 90 · NET 97 · OPS 94**

Varga builds reliable source networks and separates repeated evidence from rumors. She is effective at role acceptance, work habits, agent expectations, and organizational compatibility.

She should support rather than replace basketball evaluators.

**Specialties:** Interviews, source verification, market intelligence
**Bias:** Mild character conservatism
**Best organization:** Team that has suffered from role and trust conflicts

---

#### S10. Calvin Ross — Upside and Tools Gambler

**Age 36 · Amateur Scout**
**EVA 83 · PRO 95 · FIT 73 · NET 84 · OPS 67**

Ross identifies unusual physical and skill combinations before consensus catches up. His best recommendations become stars unavailable to conservative teams.

He produces a high bust rate and can become attached to theoretical roles that never emerge.

**Specialties:** Athletic projection, young prospects, ceiling outcomes
**Bias:** Tools and star-outcome fixation
**Best organization:** Team with several picks and strong development infrastructure

---

#### S11. Sofia Laurent — Scouting Operations Executive

**Age 46 · Director of Scouting Operations**
**EVA 72 · PRO 75 · FIT 78 · NET 89 · OPS 99**

Laurent ensures that assignments are covered, reports arrive on time, regional knowledge is retained, and critical targets receive crosschecks.

She is not the person who should make the final basketball evaluation.

**Specialties:** Department capacity, travel, report system, information continuity
**Bias:** Process conservatism
**Best organization:** Large full-depth department

---

#### S12. Andre Kim — Advance Scouting Specialist

**Age 40 · Advance Scout**
**EVA 93 · PRO 70 · FIT 98 · NET 85 · OPS 94**

Kim recognizes opponent actions, substitution habits, coverage triggers, and lineup weaknesses. His reports are immediately usable by coaching staffs.

His prospect projection and long-term player evaluation are limited.

**Specialties:** Opponent tendencies, playoff preparation, lineup behavior
**Bias:** Current-system focus
**Best organization:** Contender with a tactical coaching staff

---

#### S13. Luka Petrovic — Big-Man Evaluator

**Age 55 · International and Professional Scout**
**EVA 94 · PRO 90 · FIT 95 · NET 88 · OPS 80**

Petrovic evaluates screening, interior passing, defensive positioning, vertical spacing, rebounding, and frontcourt role combinations.

He can undervalue small-ball centers and unconventional forwards.

**Specialties:** Centers, passing bigs, rim defense
**Bias:** Traditional size preference
**Best organization:** Team building through frontcourt play

---

#### S14. Nia Reynolds — Late-Bloomer and Small-Program Scout

**Age 34 · Regional Amateur Scout**
**EVA 87 · PRO 94 · FIT 88 · NET 91 · OPS 78**

Reynolds specializes in players who received limited exposure, changed roles late, or competed outside major programs. She is willing to diverge from consensus.

Her reports require strong competition translation and careful crosschecking.

**Specialties:** Small programs, older prospects, role discovery
**Bias:** Contrarian enthusiasm
**Best organization:** Team with late picks and strong analytical support

---

## 10. Rotation planning and game execution

### 10.1 Three-layer model

```text
1. Rotation plan:
   User- or coach-selected starters and regulation target minutes

2. Coach rotation policy:
   How minutes are organized into stints, lineups, staggering, and closers

3. Game execution:
   Follows the plan while responding to forced events
```

A 240-minute assignment alone does not define substitution timing, lineup combinations, staggering, or closing groups.

### 10.2 Rotation plan

```ts
type RotationPlan = {
  teamId: string;
  version: number;
  rosterVersion: number;
  starters: [string, string, string, string, string];
  targetMinutes: Record<string, number>;
  source: "coach_generated" | "user_edited";
  userEdited: boolean;
  savedAt: string;
  coachIdAtSave: string;
  coachProfileVersion: number;
  repairHistory: RotationRepair[];
};
```

Derive required regulation minutes from league settings:

```text
requiredMinutes = playersOnCourt * regulationMinutes
```

For standard basketball: `5 * 48 = 240`.

### 10.3 Coach rotation policy

```ts
type CoachRotationProfile = {
  planning: {
    preferredRotationSize: number;
    talentWeight: number;
    roleFitWeight: number;
    defenseWeight: number;
    shootingWeight: number;
    veteranTrust: number;
    developmentBias: number;
    staminaWeight: number;
    starMinuteTarget: number;
    starterMinuteTarget: number;
    benchMinuteFloor: number;
    normalMinuteCeiling: number;
  };
  execution: {
    substitutionCadence: number;
    lineupContinuity: number;
    staggerPrimaryPlayers: number;
    positionFlexibility: number;
    fatigueSensitivity: number;
    foulTroubleSensitivity: number;
    matchupSensitivity: number;
    hotHandSensitivity: number;
    closingPreference:
      | "best_overall"
      | "best_offense"
      | "best_defense"
      | "starters"
      | "matchup_based";
    normalPlanAdherence: number;
    userPlanAdherence: number;
  };
};
```

### 10.4 Auto Rotation

1. Score coach trust from normalized talent, role fit, defense, shooting, stamina, veteran preference, and development preference.
2. Select the coach's preferred rotation size.
3. Check functional coverage: ball handling, perimeter depth, interior size/rebounding, backup creation, and lineup viability.
4. Evaluate starter combinations by quality, role compatibility, spacing, handling, defense, rebounding, and coach preferences.
5. Allocate whole-number minutes to exactly the regulation total. Each additional minute has diminishing marginal value.
6. Return an unsaved preview. Saving explicitly protects the plan as user-edited.

### 10.5 Editor behavior

- **Auto Rotation:** replaces the draft, not persisted data.
- **Reset:** restores the last saved plan.
- **Save:** validates client and server, persists atomically, increments version, and marks `userEdited = true`.
- **Cancel:** closes and discards the draft.
- Starter slots and table toggles are two views of the same state.
- Warn before replacing unsaved manual work.

### 10.6 Validation

Blocking errors:

```text
Total target minutes do not equal required regulation minutes
Not exactly five unique starters
Player not on current roster
Minutes below 0 or above regulation length
Non-integer minutes
Starter has 0 minutes
Fewer than five players have positive minutes
Obsolete roster version cannot be safely rebased
```

Non-blocking warnings:

```text
Only five players have minutes
A player is assigned the full game
Starter has very few minutes
No backup ball handler
Very little size or shooting
Injured player has planned minutes
Rotation is unusually deep
```

A valid manual plan remains valid even when the coach dislikes it.

### 10.7 Temporary availability and permanent repair

Temporary injury, suspension, illness, rest, ejection, or foul-out creates a game-specific overlay and does not rewrite the saved plan.

Permanent roster changes trigger minimum-change repair:

```text
1. Remove departed players
2. Preserve surviving starters
3. Preserve surviving minutes
4. Calculate orphaned minutes
5. Replace a starter only if required
6. Redistribute only orphaned minutes
7. Keep all players within the hard cap
8. Log and display every change
```

Minimize:

```text
repairCost =
  totalAbsoluteChangeToExistingMinutes
  + starterChangesPenalty
  + rotationEntryPenalty
```

### 10.8 Game consumption and adherence

At game start, snapshot the plan version, coach profile version, active roster, availability overlay, starters, target minutes, and whether the plan is user-edited.

At substitution opportunities, evaluate plan adherence, lineup quality, role balance, coach style, matchup, hot hand, fatigue, fouls, and substitution disruption.

For a protected user plan:

- Selected starters start.
- Available players normally finish within about two minutes of targets.
- Zero-minute players do not enter.
- Coach style can rearrange stints and lineups.
- Only forced events can cause major deviations.
- Coach personality cannot regenerate the plan or permanently bench a planned player.
- Closing choices must still reconcile with target minutes.

Overtime adds `5 × overtimeMinutes` extra player-minutes outside the regulation plan and never invalidates the saved 240-minute plan.

## 11. Explainability and interface requirements

Every major screen should answer the decision, not display unexplained ratings.

### Staff overview

```text
Identity
Five public pillars
Strongest qualities
Main weaknesses
Roster/organization fit with reasons
Installation or transition cost
Contract and autonomy
Career context
```

### Candidate comparisons

Compare fit, dimensions, costs, strengths, risks, installation time, and timeline—not an overall score.

### Season and department reviews

Explain positive contributions, negative contributions, contextual causes, and recommended responses. Examples of valid causes:

```text
Shot mix changed
Coverage mismatch
Lineup familiarity
Role conflict
Medical restriction
Assistant departure
Development capacity
Scouting uncertainty
Asset/timeline mismatch
Poor relationship
Random variance
```

### Rival intelligence

Show observed tendencies, history, needs, likely unavailable assets, market reputation, and confidence. Do not reveal exact acceptance thresholds or hidden ratings.

## 12. Balance and quality assurance

### 12.1 Global balance rules

- Every strategy spends a trade-off budget.
- Preferences and ability remain separate.
- Specialists have higher peaks and lower mismatch floors.
- Generalists adjust faster but have lower maximum mastery.
- No staff system solves development, injuries, scouting, or roster building.
- Staff effects remain bounded.
- Information is imperfect but not arbitrary.
- AI teams use the same systems and can act before the human.
- Bad organizations have specific failure modes rather than random stupidity.

### 12.2 Automated tests

**Coach tests**

- Equal-roster round robin across all archetypes.
- Roster-fit matrix across shooting, interior, young, veteran, star-heavy, deep, switchable, and rim-protection rosters.
- No philosophy dominates the full field.
- Specialists show higher peaks; adaptable coaches show lower variance.

**Medical tests**

- Context-adjust injury and setback outcomes.
- Staff do not materially prevent contact injuries.
- Better staff primarily improve information, functional recovery, trust, and avoidable setbacks.
- Conservative and aggressive departments both have legitimate costs.

**Development tests**

- Improvement remains probabilistic.
- Capacity overload visibly reduces plan quality.
- Practice improvement can fail to transfer without role opportunity.
- Medical restrictions bind.

**GM/trade tests**

- Human exploit battery for pick theft, salary dumps, repeated counters, split trades, threshold probing, and market monopolization.
- Post-transaction roster and cap audit.
- AI-to-AI bidding.
- Weak GMs remain exploitable in specific ways but not infinitely.

**Scouting tests**

- AI never reads true ratings.
- More independent evidence narrows uncertainty.
- Duplicate evidence has diminishing value.
- Reports persist reasonably.
- Draft boards contain coverage near every pick.
- Strong departments are better calibrated, not perfectly correct.

**Long-save tests**

Simulate at least 50–100 seasons and inspect staff tenure, promotions, rating inflation, tactical diversity, GM and scouting distributions, rebuild lengths, contender mobility, salary distributions, staff poaching, former-player entry, unemployed candidates, organizational recovery, and human win rate.

### 12.3 Minimum first release

Implement first:

```text
Head coaches with five pillars, packages, traits, fit, contracts, careers
Medical director/trainer with clearance, diagnosis confidence, stages, and restrictions
Development director with individual plans, capacity, and game transfer
One GM per AI team with tendencies, phases, contextual valuation, draft/FA/trade logic
Scouting directors with ranges, confidence, disagreement, reports, and private boards
Protected rotation plan with Auto/Reset/Save/Cancel, validation, repair, and game consumption
AI hiring/firing and full editor/import/export
Explainable decision traces
Off/Lite/Standard settings
```

Add specialist staff, deeper relationships, affiliates, second opinions, groupthink, multi-team trades, practice detail, and advanced opponent game plans only after the foundation behaves correctly.

## 13. Final simulation contract

```text
Owner pressure
+ GM quality and philosophy
+ scouting evidence and uncertainty
+ roster and asset position
+ coach philosophy and fit
+ development quality and opportunity
+ medical limits and availability
+ relationships, familiarity, and staff cohesion
+ randomness and luck
= team direction and outcomes
```

Replacing one staff member should not merely make the team “better.” It should make the organization **different**: different decisions, shots, coverages, roles, development priorities, health risks, trade behavior, information quality, relationships, and long-term direction.
