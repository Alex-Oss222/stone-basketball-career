# Complete player-rating architecture

Yes, this changes the math. The cleanest design is to stop treating every number as the same kind of rating.

Your game should have six distinct layers:

| Layer               | What it contains                                         |       Used in OVR? |
| ------------------- | -------------------------------------------------------- | -----------------: |
| **Measurements**    | Height, weight, wingspan, standing reach                 |         Indirectly |
| **Base ratings**    | Offensive, defensive, physical, and mental abilities     |                Yes |
| **Derived ratings** | Speed with ball, rim deterrence, pressure handling, etc. |     Not separately |
| **Tendencies**      | What the player chooses to do and how often              |                 No |
| **Hidden traits**   | Development, health susceptibility, personality          |                 No |
| **Summary outputs** | Category grades, OVR, potential, availability            | Calculated results |

This separation matters. Speed and agility should not be blended into one attribute, and length should affect several basketball actions without becoming another shooting or defensive skill. NBA 2K now separates Speed, Agility, Strength and Vertical, while Basketball GM separately models physical tools, shooting, passing, rebounding and offensive/defensive IQ. Both also demonstrate that the mix of ratings matters more than simply averaging every number. ([NBA 2K][1])

The weights below are recommended **starting weights**, not scientific constants. They should be adjusted after you run league-level simulation tests.

For every main category:

[
\text{Category Score}
=====================

\frac{\sum(\text{Subrating}\times\text{Weight})}
{\sum\text{Weights}}
]

All weights within a category total 100%.

---

# 1. Offensive skills

## Complete offensive-rating catalog

The descriptions below are written so they can be used directly as hover text.

| Main skill                                                                                                            | Sub-skill               | Weight | Hover description                                                                                                                 |
| --------------------------------------------------------------------------------------------------------------------- | ----------------------- | -----: | --------------------------------------------------------------------------------------------------------------------------------- |
| **Rim Finishing** — Scoring at the basket from drives, cuts, dump-offs and rebounds, excluding deliberate post moves. | Standing Finish         |    15% | Ability to score near the rim from a stationary catch, dump-off or offensive rebound.                                             |
| ↳                                                                                                                     | Driving Layup           |    25% | Touch, angles and hand control on layups while moving toward the basket.                                                          |
| ↳                                                                                                                     | Contact Finishing       |    25% | Ability to maintain balance and convert rim attempts through body contact.                                                        |
| ↳                                                                                                                     | Dunking                 |    20% | Ability to complete dunks when reach, space and momentum create a dunk opportunity.                                               |
| ↳                                                                                                                     | Foul Drawing            |    15% | Ability to create shooting fouls through timing, angles and contact craft. Raises free-throw frequency rather than shot accuracy. |
| **Post Scoring** — Scoring through back-to-the-basket and short-post techniques.                                      | Post Control & Footwork |    30% | Ability to establish position, protect the ball and execute post moves without losing balance or control.                         |
| ↳                                                                                                                     | Post Finishing          |    30% | Ability to convert close shots after a post move, seal or power move.                                                             |
| ↳                                                                                                                     | Post Hook & Touch       |    20% | Touch and accuracy on hooks, push shots and other short post attempts.                                                            |
| ↳                                                                                                                     | Post Fadeaway           |    20% | Accuracy and balance on fadeaways generated from the post.                                                                        |
| **Mid-Range Shooting** — Shot-making inside the three-point line but outside the immediate rim area.                  | Catch-and-Shoot Mid     |    25% | Accuracy on mid-range jumpers taken immediately after receiving a pass.                                                           |
| ↳                                                                                                                     | Pull-Up Mid             |    30% | Accuracy on mid-range jumpers taken off the dribble.                                                                              |
| ↳                                                                                                                     | Movement Mid            |    20% | Accuracy on mid-range shots after curls, fades, lateral movement or off-balance catches.                                          |
| ↳                                                                                                                     | Contested Mid           |    25% | Ability to maintain mid-range accuracy against a meaningful defensive contest.                                                    |
| **Three-Point Shooting** — Shot-making from beyond the three-point line.                                              | Catch-and-Shoot Three   |    30% | Accuracy on three-pointers taken immediately after receiving a pass.                                                              |
| ↳                                                                                                                     | Pull-Up Three           |    25% | Accuracy on three-pointers taken off the dribble.                                                                                 |
| ↳                                                                                                                     | Movement Three          |    20% | Accuracy on threes following relocation, screens, fades or other movement.                                                        |
| ↳                                                                                                                     | Contested Three         |    25% | Ability to maintain three-point accuracy against a meaningful contest.                                                            |
| **Free-Throw Shooting** — Uncontested shooting from the free-throw line.                                              | Free-Throw Accuracy     |    85% | Establishes the player's normal long-run free-throw make probability.                                                             |
| ↳                                                                                                                     | Free-Throw Consistency  |    15% | Controls how much the player's short-term free-throw performance varies around his normal accuracy.                               |
| **Passing** — Seeing, selecting and delivering passes.                                                                | Pass Accuracy           |    40% | Ability to place passes where teammates can receive them without bobbling, reaching or losing momentum.                           |
| ↳                                                                                                                     | Court Vision            |    35% | Ability to recognize open teammates and passing windows across the floor.                                                         |
| ↳                                                                                                                     | Pass Timing             |    25% | Ability to release a pass while the intended window is still available.                                                           |
| **Ball Handling** — Controlling and protecting the ball while moving or creating an advantage.                        | Dribble Control         |    30% | Ability to maintain a controlled dribble during moves, traffic and changes of pace.                                               |
| ↳                                                                                                                     | Ball Security           |    30% | Ability to protect the ball from strips, pokes, pressure and careless turnovers.                                                  |
| ↳                                                                                                                     | Change of Direction     |    25% | Ability to redirect the dribble sharply without losing control or speed.                                                          |
| ↳                                                                                                                     | Pace Control            |    15% | Ability to use hesitations, stops and speed changes to manipulate defenders.                                                      |
| **Off-Ball Offense** — Creating value without controlling the ball.                                                   | Cut Timing              |    30% | Ability to begin cuts when passing lanes and scoring windows are available.                                                       |
| ↳                                                                                                                     | Relocation              |    25% | Ability to move into open shooting space after passing or when the defense shifts.                                                |
| ↳                                                                                                                     | Screen Use              |    20% | Ability to set up defenders and run tightly off screens to create separation.                                                     |
| ↳                                                                                                                     | Catch Security          |    25% | Ability to receive difficult passes cleanly and prepare for the next action without a bobble.                                     |
| **Screening** — Creating advantages for teammates through legal screens and follow-up movement.                       | Screen Angle            |    35% | Ability to position a screen so the ball handler or cutter receives a useful path.                                                |
| ↳                                                                                                                     | Screen Timing           |    35% | Ability to arrive, become legally set and make contact at the correct moment.                                                     |
| ↳                                                                                                                     | Roll or Pop Timing      |    30% | Ability to separate from a screen at the correct moment as a roller, popper or short-roll option.                                 |
| **Offensive Rebounding** — Creating extra possessions after a teammate's missed shot.                                 | Offensive Positioning   |    30% | Ability to occupy useful rebounding space before and during a shot attempt.                                                       |
| ↳                                                                                                                     | Rebound Reading         |    25% | Ability to predict the direction and distance of a missed shot. This is a shared rating also used for defensive rebounding.       |
| ↳                                                                                                                     | Rebound Pursuit         |    25% | Willingness and technique used to chase rebounds outside the player's immediate area.                                             |
| ↳                                                                                                                     | Box-Out Escape          |    20% | Ability to avoid, slip or fight through defensive box-outs.                                                                       |

## Important offensive changes from your current system

Your present **Inside Scoring** category should become two categories:

* **Rim Finishing**
* **Post Scoring**

Post Finishing does not belong with Driving Layup and Dunking. Post Fadeaway also belongs under Post Scoring, not Mid-Range Shooting.

Pressure Free Throws and Pressure Handling should be derived ratings rather than separate stored skills. Otherwise, Composure gets counted more than once.

---

# 2. Defensive skills

| Main skill                                                                                | Sub-skill                      | Weight | Hover description                                                                                           |
| ----------------------------------------------------------------------------------------- | ------------------------------ | -----: | ----------------------------------------------------------------------------------------------------------- |
| **Perimeter Defense** — Defending the ball against guards and wings in space.             | On-Ball Containment            |    30% | Ability to stay between the ball handler and the basket without being beaten cleanly.                       |
| ↳                                                                                         | Lateral Recovery               |    25% | Ability to recover after the attacker gains a step or changes direction.                                    |
| ↳                                                                                         | Screen Navigation              |    25% | Ability to get over, under or through an on-ball screen without being removed from the play.                |
| ↳                                                                                         | Closeout Control               |    20% | Ability to contest a shooter without overrunning the play, allowing an easy drive or committing a foul.     |
| **Off-Ball Defense** — Tracking assignments and preventing advantages away from the ball. | Denial                         |    35% | Ability to make catches difficult without losing defensive position.                                        |
| ↳                                                                                         | Cutter Tracking                |    35% | Ability to stay connected to players cutting toward the basket.                                             |
| ↳                                                                                         | Off-Ball Screen Navigation     |    30% | Ability to chase shooters and cutters through screens away from the ball.                                   |
| **Interior Defense** — Defending post play, paint attacks and close shots.                | Post Containment               |    30% | Ability to resist post movement and prevent deep interior position.                                         |
| ↳                                                                                         | Paint Positioning              |    25% | Ability to occupy useful interior defensive space before an attack reaches the rim.                         |
| ↳                                                                                         | Verticality                    |    25% | Ability to contest vertically without unnecessarily fouling or surrendering position.                       |
| ↳                                                                                         | Interior Recovery              |    20% | Ability to recover to the rim after helping, rotating or being displaced.                                   |
| **Stealing** — Removing or disrupting the ball without surrendering defensive position.   | On-Ball Steal                  |    35% | Ability to attack an exposed live dribble without being beaten by the ball handler.                         |
| ↳                                                                                         | Strip Technique                |    30% | Ability to dislodge the ball during gathers, post moves, shots and exposed carries.                         |
| ↳                                                                                         | Deflection Timing              |    35% | Ability to time hand placement when disrupting passes and dribbles.                                         |
| **Blocking** — Preventing shot attempts through legal shot-blocking technique.            | Block Timing                   |    40% | Ability to time a jump or reach so the ball is contacted without fouling.                                   |
| ↳                                                                                         | Help-Side Blocking             |    30% | Ability to block shots after rotating from another assignment.                                              |
| ↳                                                                                         | Recovery & Chase-Down Blocking |    30% | Ability to block shots after initially trailing or being beaten.                                            |
| **Defensive Rebounding** — Ending defensive possessions after missed shots.               | Defensive Positioning          |    30% | Ability to establish useful rebounding position before the ball reaches the rim.                            |
| ↳                                                                                         | Box-Out Technique              |    30% | Ability to locate an opponent, make legal contact and prevent access to the rebound.                        |
| ↳                                                                                         | Rebound Reading                |    20% | Ability to predict where a missed shot will travel. Store this once and share it with offensive rebounding. |
| ↳                                                                                         | Rebound Security               |    20% | Ability to secure the ball cleanly and prevent tips, strips and loose rebounds.                             |

## What should move out of your current defensive categories

| Current rating                            | Better location                                                            |
| ----------------------------------------- | -------------------------------------------------------------------------- |
| Passing-Lane Anticipation                 | Defensive IQ                                                               |
| Help Rotation                             | Defensive IQ                                                               |
| Rim Deterrence                            | Derived from length, positioning, verticality, timing and help recognition |
| Vertical Contest                          | Interior Defense as Verticality                                            |
| Second Jump                               | Physical Explosiveness                                                     |
| Rebound Reading in two categories         | One shared rating                                                          |
| Physical Leverage                         | Derived physical value                                                     |
| Recovery Blocking and Chase-Down Blocking | One combined rating unless your simulation treats them very differently    |

---

# 3. Physical ratings

NBA 2K's separation of Speed, Agility, Strength and Vertical is a useful baseline because those physical capacities affect different actions. Basketball GM similarly applies speed, strength, jumping and endurance to different parts of its simulation. ([NBA 2K][1])

| Main physical                                                                         | Sub-rating          | Weight | Hover description                                                                                              |
| ------------------------------------------------------------------------------------- | ------------------- | -----: | -------------------------------------------------------------------------------------------------------------- |
| **Speed** — Straight-line movement ability.                                           | Acceleration        |    50% | How quickly the player reaches useful running speed from a stationary or slow position.                        |
| ↳                                                                                     | Top Speed           |    50% | The player's maximum straight-line running speed in open space.                                                |
| **Agility** — Redirecting and reacting while maintaining balance.                     | Lateral Quickness   |    40% | Side-to-side movement speed, particularly when defending the ball.                                             |
| ↳                                                                                     | Change of Direction |    35% | Ability to stop, plant and redirect the body without excessive loss of speed.                                  |
| ↳                                                                                     | Reactive Agility    |    25% | Ability to physically respond to an opponent's unexpected movement. Mental anticipation is applied separately. |
| **Explosiveness & Body Control** — Short-burst power, jumping and control in the air. | First-Step Burst    |    30% | Initial explosive movement used to attack a gap, cut or recover defensively.                                   |
| ↳                                                                                     | Vertical Leap       |    30% | Maximum upward explosion used for finishing, rebounding, contests and blocks.                                  |
| ↳                                                                                     | Second Jump         |    20% | Ability to leave the floor again quickly after landing.                                                        |
| ↳                                                                                     | Body Control        |    20% | Ability to maintain coordination while airborne, off balance or changing direction.                            |
| **Strength** — Producing and absorbing contact.                                       | Lower-Body Strength |    40% | Ability to hold position, drive through the floor and resist displacement.                                     |
| ↳                                                                                     | Upper-Body Strength |    25% | Ability to absorb, create and control upper-body contact.                                                      |
| ↳                                                                                     | Contact Balance     |    35% | Ability to remain coordinated and upright after physical contact.                                              |
| **Conditioning** — Maintaining performance through games and schedules.               | Stamina             |    45% | Determines how quickly the player's current abilities decline as in-game fatigue rises.                        |
| ↳                                                                                     | Recovery Rate       |    30% | Determines how quickly the player regains energy between possessions, substitutions and games.                 |
| ↳                                                                                     | Workload Capacity   |    25% | Ability to handle sustained minutes, repeated games and demanding roles without excessive fatigue.             |
| **Durability** — Remaining available and tolerating physical stress.                  | Injury Resistance   |    55% | General resistance to suffering an injury during play or training.                                             |
| ↳                                                                                     | Load Tolerance      |    45% | Ability to tolerate heavy minutes and repeated physical workload without elevated breakdown risk.              |

## Measurements are separate from ratings

Do not put these inside Strength or average them directly like normal skills:

| Measurement    | Hover description                                                                                            |
| -------------- | ------------------------------------------------------------------------------------------------------------ |
| Height         | The player's listed standing height. Influences visibility, matchups and functional reach.                   |
| Weight         | The player's body mass. Used with strength and movement when resolving physical contact.                     |
| Wingspan       | Fingertip-to-fingertip length. Influences contests, deflections, blocks, finishing reach and passing angles. |
| Standing Reach | Maximum standing reach. Especially important for rim finishing, rebounding and interior defense.             |
| Hand Size      | Optional measurement affecting catch security, ball control and rebound security.                            |

Basketball GM explicitly treats length and standing reach as simulation-relevant rather than merely cosmetic, while NBA 2K uses height, weight and wingspan to limit attribute potential. ([Basketball GM][2])

### Derived functional-size score

Use fixed reference means and standard deviations from your baseline league:

[
z_x=\frac{x-\mu_x}{\sigma_x}
]

[
\text{Functional Size}
======================

\operatorname{clamp}
\left(
50+
10\left[
0.60z_{\text{Standing Reach}}
+
0.25z_{\text{Wingspan}}
+
0.15z_{\text{Height}}
\right],
0,
100
\right)
]

Use a fixed reference dataset. Do not recalculate the means every season, or a player's score could change simply because the league became taller or shorter.

---

# 4. Mental ratings

## On-court mental ratings

| Main mental                                                                           | Sub-rating               | Weight | Hover description                                                                                              |
| ------------------------------------------------------------------------------------- | ------------------------ | -----: | -------------------------------------------------------------------------------------------------------------- |
| **Offensive IQ** — Understanding and choosing effective offensive actions.            | Offensive Awareness      |    25% | Ability to recognize offensive opportunities, teammate positioning and defensive mistakes.                     |
| ↳                                                                                     | Shot Selection           |    25% | Ability to distinguish strong shot opportunities from low-value or unnecessary attempts.                       |
| ↳                                                                                     | Decision-Making          |    30% | Ability to choose effectively between shooting, passing, driving, resetting and protecting the ball.           |
| ↳                                                                                     | Spacing & Read-and-React |    20% | Ability to maintain useful spacing and respond correctly when teammates or defenders change the play.          |
| **Defensive IQ** — Reading the offense and executing team defensive responsibilities. | Defensive Awareness      |    25% | Ability to track assignments, ball location and developing threats.                                            |
| ↳                                                                                     | Anticipation             |    20% | Ability to predict passes, drives, cuts and other offensive actions before they fully develop.                 |
| ↳                                                                                     | Help Recognition         |    20% | Ability to recognize when help defense is required and when staying home is safer.                             |
| ↳                                                                                     | Rotation Discipline      |    20% | Ability to execute the correct rotation and avoid abandoning responsibilities unnecessarily.                   |
| ↳                                                                                     | Foul Discipline          |    15% | Ability to contest, reach and use contact without committing avoidable fouls.                                  |
| **Competitive Makeup** — Effort and performance response during competition.          | Competitiveness          |    25% | Desire to challenge opponents and respond strongly to competitive situations.                                  |
| ↳                                                                                     | Composure                |    25% | Ability to remain controlled when pressured, frustrated or placed in high-leverage situations.                 |
| ↳                                                                                     | Motor                    |    20% | Frequency and intensity of effort across possessions, including loose balls, recovery and rebounding activity. |
| ↳                                                                                     | Focus                    |    15% | Ability to avoid mental lapses and remain engaged throughout a game.                                           |
| ↳                                                                                     | Resilience               |    15% | Ability to recover mentally from mistakes, slumps, losses and setbacks.                                        |
| **Team & Leadership** — Supporting organized team performance.                        | Communication            |    35% | Ability to communicate coverages, assignments, screens and developing actions to teammates.                    |
| ↳                                                                                     | Teamwork                 |    35% | Willingness and ability to cooperate within the team's intended system and role structure.                     |
| ↳                                                                                     | Leadership               |    30% | Ability to stabilize, organize and positively influence teammates.                                             |

Coachability should be separated from current basketball IQ. Research describes coachability as a multidimensional willingness and ability to seek, receive and implement feedback, including attentiveness, persistence and willingness to learn. That supports treating it as a development trait rather than as current court awareness. ([Springer][3])

---

# 5. Hidden development traits

These ratings should never be included in current OVR.

Their exact numbers can remain permanently hidden. Scouts can communicate them through phrases such as “excellent worker,” “slow to adjust,” or “responds well to coaching.”

| Hidden trait      | Development weight | Internal description                                                                      |
| ----------------- | -----------------: | ----------------------------------------------------------------------------------------- |
| Work Ethic        |                30% | Effort and consistency applied to practice, training and offseason improvement.           |
| Coachability      |                20% | Ability and willingness to receive feedback and turn it into corrected behavior.          |
| Adaptability      |                20% | Ability to learn a new role, scheme, position, league or coaching system.                 |
| Learning Capacity |                20% | Underlying rate at which new technical and tactical abilities can be acquired.            |
| Professionalism   |                10% | Consistency of preparation, recovery habits, punctuality and long-term career management. |

### Hidden development score

[
D=
0.30(\text{Work Ethic})
+
0.20(\text{Coachability})
+
0.20(\text{Adaptability})
+
0.20(\text{Learning Capacity})
+
0.10(\text{Professionalism})
]

Convert it into a development multiplier:

[
M_{\text{development}}=0.70+0.006D
]

That produces:

| Development score | Multiplier |
| ----------------: | ---------: |
|                 0 |      0.70× |
|                25 |      0.85× |
|                50 |      1.00× |
|                75 |      1.15× |
|               100 |      1.30× |

This multiplier is deliberately meaningful without allowing Work Ethic alone to turn every low-ceiling player into a superstar.

---

# 6. Derived ratings that should not be stored separately

A derived rating can still be shown in the interface. It simply should not exist as another independent player attribute.

| Derived value                | Recommended starting formula                                                                                       |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| **Pressure Free Throws**     | (0.75FTA + 0.15Composure + 0.10Focus)                                                                              |
| **Pressure Handling**        | (0.45BallSecurity + 0.20DribbleControl + 0.20Composure + 0.15DecisionMaking)                                       |
| **Speed With Ball**          | (0.30Acceleration + 0.20TopSpeed + 0.25DribbleControl + 0.15ChangeDirection + 0.10BodyControl)                     |
| **Shot Creation**            | (0.25DribbleControl + 0.20ChangeDirection + 0.20FirstStep + 0.20PaceControl + 0.15Composure)                       |
| **Physical Leverage**        | (0.45LowerBodyStrength + 0.25ContactBalance + 0.20WeightAdvantage + 0.10BodyControl)                               |
| **Late-Game Conditioning**   | (0.45Stamina + 0.25RecoveryRate + 0.20WorkloadCapacity + 0.10Composure)                                            |
| **Rim Deterrence**           | (0.25FunctionalSize + 0.25Verticality + 0.20BlockTiming + 0.15PaintPositioning + 0.15HelpRecognition)              |
| **Passing-Lane Threat**      | (0.35Anticipation + 0.30DeflectionTiming + 0.20DefensiveAwareness + 0.15FunctionalSize)                            |
| **Offensive Rebound Impact** | (0.45OREB + 0.15FunctionalSize + 0.15Strength + 0.10Vertical + 0.10SecondJump + 0.05Motor)                         |
| **Defensive Rebound Impact** | (0.45DREB + 0.15FunctionalSize + 0.15Strength + 0.10Vertical + 0.10Motor + 0.05SecondJump)                         |
| **Transition Offense**       | (0.20Acceleration + 0.15TopSpeed + 0.20RimFinishing + 0.15BallHandling + 0.15Passing + 0.15OffensiveIQ)            |
| **Transition Defense**       | (0.20Acceleration + 0.15TopSpeed + 0.20PerimeterDefense + 0.15DefensiveAwareness + 0.15Motor + 0.15FunctionalSize) |

Do not count a base rating and its derived rating in the same OVR formula. For example, do not include Ball Security, Composure and Pressure Handling independently. That would count Ball Security and Composure twice.

---

# 7. Tendencies

Tendencies should be 0–100 frequency or preference values, but they should never raise OVR.

A player with a 95 Pull-Up Three tendency attempts many pull-up threes. It does not mean he is good at them.

| Tendency family                       | What it controls                                                         |
| ------------------------------------- | ------------------------------------------------------------------------ |
| Touches and Usage                     | How often the player becomes the primary decision-maker.                 |
| Rim, Mid and Three Shot Diet          | Preferred distribution of shot locations.                                |
| Catch-and-Shoot, Pull-Up and Movement | Preferred creation type for jump shots.                                  |
| Drive, Shoot and Pass                 | Choice made after receiving or controlling the ball.                     |
| Isolation                             | Frequency of attacking without a screen.                                 |
| Pick-and-Roll Handler                 | Frequency of using ball screens as the handler.                          |
| Roll, Pop and Short Roll              | Preferred action after setting a screen.                                 |
| Post-Up                               | Frequency of requesting and using post possessions.                      |
| Cutting and Relocating                | Frequency of off-ball movement.                                          |
| Transition Aggression                 | Frequency of running or attacking before the defense sets.               |
| Contact Seeking                       | Frequency of deliberately attacking contact.                             |
| Offensive-Rebound Crash               | Frequency of pursuing offensive rebounds instead of retreating.          |
| Steal Aggression                      | Frequency of reaching or leaving position to pursue steals.              |
| Block Aggression                      | Frequency of leaving the floor or rotating to pursue blocks.             |
| Passing Risk                          | Willingness to attempt narrow-window or high-value passes.               |
| Pace Preference                       | Preference for quick decisions versus deliberate half-court possessions. |

---

# 8. Actual OVR math

## Do not average all 91 base ratings

That would give categories with more subratings more influence.

For example, Rim Finishing has five subratings and Free Throws has two. A flat average would make Rim Finishing 2.5 times more important simply because you stored more detail beneath it.

Use this hierarchy:

[
\text{Subratings}
\rightarrow
\text{Category Scores}
\rightarrow
\text{Position/Role Pillars}
\rightarrow
\text{OVR}
]

---

## Step 1: Calculate all main-category scores

You will have:

| Pillar           |                                     Main categories |
| ---------------- | --------------------------------------------------: |
| Offensive skills |                                                  10 |
| Defensive skills |                                                   6 |
| Physicals        | 6, although Durability is excluded from healthy OVR |
| Visible mental   |                                                   4 |

---

## Step 2: Calculate position-adjusted offensive score

These are recommended starting weights.

| Offensive category   | PG / Lead Guard | SG / Scoring Guard | SF / Wing | PF / Forward | C / Big |
| -------------------- | --------------: | -----------------: | --------: | -----------: | ------: |
| Rim Finishing        |             10% |                13% |       14% |          18% |     23% |
| Post Scoring         |              1% |                 2% |        5% |          12% |     18% |
| Mid-Range            |             10% |                13% |       12% |           8% |      5% |
| Three-Point          |             15% |                22% |       20% |          15% |      8% |
| Free Throw           |              4% |                 5% |        4% |           4% |      4% |
| Passing              |             25% |                12% |       10% |           7% |      7% |
| Ball Handling        |             23% |                14% |       10% |           6% |      3% |
| Off-Ball Offense     |              8% |                13% |       14% |          10% |      7% |
| Screening            |              1% |                 2% |        4% |           9% |     12% |
| Offensive Rebounding |              3% |                 4% |        7% |          11% |     13% |

For a shooting guard:

[
\begin{aligned}
O_{SG}={}&
0.13(Rim)+0.02(Post)+0.13(Mid)+0.22(Three)\
&+0.05(FT)+0.12(Passing)+0.14(Handling)\
&+0.13(OffBall)+0.02(Screening)+0.04(OREB)
\end{aligned}
]

---

## Step 3: Calculate position-adjusted defensive score

| Defensive category   |  PG |  SG |  SF |  PF |   C |
| -------------------- | --: | --: | --: | --: | --: |
| Perimeter Defense    | 35% | 30% | 25% | 15% |  5% |
| Off-Ball Defense     | 25% | 25% | 25% | 20% | 15% |
| Interior Defense     |  3% |  7% | 15% | 25% | 32% |
| Stealing             | 25% | 20% | 13% |  8% |  5% |
| Blocking             |  2% |  5% |  8% | 15% | 25% |
| Defensive Rebounding | 10% | 13% | 14% | 17% | 18% |

---

## Step 4: Calculate position-adjusted physical score

Durability is not included here. Durability measures expected availability, not how good the player is while healthy.

| Physical category |  PG |  SG |  SF |  PF |   C |
| ----------------- | --: | --: | --: | --: | --: |
| Functional Size   |  5% |  8% | 12% | 18% | 25% |
| Speed             | 23% | 21% | 18% | 12% |  7% |
| Agility           | 27% | 23% | 20% | 13% |  8% |
| Explosiveness     | 15% | 18% | 18% | 18% | 18% |
| Strength          | 10% | 12% | 16% | 23% | 27% |
| Conditioning      | 20% | 18% | 16% | 16% | 15% |

---

## Step 5: Calculate position-adjusted mental score

| Mental category    |  PG |  SG |  SF |  PF |   C |
| ------------------ | --: | --: | --: | --: | --: |
| Offensive IQ       | 40% | 35% | 30% | 25% | 20% |
| Defensive IQ       | 25% | 30% | 35% | 40% | 45% |
| Competitive Makeup | 20% | 25% | 25% | 25% | 25% |
| Team & Leadership  | 15% | 10% | 10% | 10% | 10% |

---

## Step 6: Combine the four pillars

| Role               | Offense | Defense | Physical | Mental |
| ------------------ | ------: | ------: | -------: | -----: |
| PG / Lead Guard    |     50% |     18% |      12% |    20% |
| SG / Scoring Guard |     48% |     22% |      15% |    15% |
| SF / Wing          |     42% |     30% |      15% |    13% |
| PF / Forward       |     36% |     34% |      18% |    12% |
| C / Big            |     32% |     38% |      20% |    10% |

Therefore:

[
OVR_p=
w_OO_p+w_DD_p+w_PP_p+w_MM_p
]

Calculate the score for every position or role the player can realistically perform:

[
OVR=
\operatorname{round}
\left(
\max_{p\in\text{eligible roles}}OVR_p
\right)
]

### Example

Suppose a shooting guard has:

* Offensive score: 78
* Defensive score: 69
* Physical score: 75
* Mental score: 76

[
OVR_{SG}
========

0.48(78)+0.22(69)+0.15(75)+0.15(76)
]

[
OVR_{SG}=75.27
]

Using your current letter scale, that player is a **75 OVR, B**.

Use the unrounded 75.27 when selecting the letter. Round only the displayed number.

---

## What is excluded from current OVR?

| Rating or system               | Why it is excluded                                         |
| ------------------------------ | ---------------------------------------------------------- |
| Durability                     | Measures availability and injury risk, not healthy ability |
| Injury history                 | Affects health and future availability                     |
| Work Ethic                     | Affects future improvement                                 |
| Coachability                   | Affects response to coaching                               |
| Adaptability                   | Affects role and system learning                           |
| Learning Capacity              | Affects development                                        |
| Professionalism                | Affects preparation, growth and recovery                   |
| Tendencies                     | Control choices rather than ability                        |
| Potential                      | Is an output, not a current ability                        |
| Contract or personality traits | Affect management decisions rather than court ability      |

The actual game simulation should also use the individual ratings, not OVR. OVR is only a readable summary. Official Basketball GM similarly notes that a player's rating mix, teammates and context affect performance, and that OVR alone does not guarantee results. ([Basketball GM][4])

---

# 9. Potential system

## Potential should not cause development

Do not code this:

```text
Player has 90 potential, therefore he automatically grows toward 90.
```

Instead:

```text
The player develops according to age, hidden ceilings, work habits,
coaching, opportunity, randomness and health.

Potential is calculated from the possible future outcomes.
```

Basketball GM uses a similar concept: its potential value does not drive development. It simulates possible career paths and uses the 75th-percentile peak OVR as the displayed potential estimate. ([Basketball GM][4])

## Give every base rating a hidden ceiling

A player should not have only one global potential number.

A prospect could have:

* 92 hidden Catch-and-Shoot Three ceiling
* 74 Ball Handling ceiling
* 58 Strength ceiling
* 80 Defensive Awareness ceiling
* 66 Vertical ceiling

That produces much more realistic player development than a single global cap.

For each subrating (i), store:

[
CurrentRating_i
]

[
HiddenCeiling_i
]

[
CeilingGap_i=
\max(0,HiddenCeiling_i-CurrentRating_i)
]

---

## Annual development formula

[
\begin{aligned}
\Delta r_i={}&
Growth_{\text{group}}(age)
\times
\frac{CeilingGap_i}{100}
\times
M_{\text{development}}\
&\times M_{\text{coaching}}
\times M_{\text{opportunity}}
\times M_{\text{health}}
+\epsilon_i\
&-Decline_{\text{group}}(age)
\end{aligned}
]

Where:

* `Growthgroup(age)` differs for skills, physicals and mental attributes.
* `CeilingGap` slows growth as the player approaches his ceiling.
* `Development multiplier` comes from the five hidden development traits.
* `Coaching` reflects staff quality and training focus.
* `Opportunity` reflects useful minutes, role stability and practice.
* `Health` reflects missed training and chronic issues.
* (\epsilon_i) is random yearly variation.
* `Decline` increases with age and physical wear.

Overall NBA performance research supports using nonlinear and individualized age curves rather than one fixed development cutoff. One large aging-curve study found net performance generally increased to roughly ages 28–29, while individual inflection points ranged from approximately 24 to 33. ([Springer][5])

Physical ratings should generally begin declining sooner than technical or awareness ratings, but every player should receive a randomized aging profile.

---

## Calculate potential through career simulations

For every player:

1. Simulate 300 future careers.
2. Apply development, age decline, injuries, coaching-neutral conditions and randomness.
3. Calculate OVR every season.
4. Record the highest OVR reached in each career.
5. Build a distribution of those peak OVRS.

Then use:

[
ExpectedPeak=P_{50}(\text{Peak OVR})
]

[
Potential=P_{75}(\text{Peak OVR})
]

[
UpsideCeiling=P_{90}(\text{Peak OVR})
]

I recommend displaying the 75th percentile as Potential. It represents a believable upside outcome without pretending it is guaranteed.

---

## Scouted versus true potential

The exact potential result should remain hidden.

[
ScoutedPotential=
TruePotential+\epsilon_{\text{scouting}}
]

A reasonable starting uncertainty model:

| Scouting quality | Typical error standard deviation |
| ---------------- | -------------------------------: |
| Elite            |                  2 rating points |
| Good             |                              3–4 |
| Average          |                                5 |
| Poor             |                              7–8 |

The UI should show:

> **Potential: B+ (Medium confidence)**

The parenthetical should communicate scouting confidence, not reveal the hidden true number.

### Potential tooltip

> **Potential** — A scouted estimate of the player's 75th-percentile peak OVR. It accounts for age, development traits, health risk and uncertainty. Potential does not directly cause player growth.

Basketball GM also presents displayed ratings as scouting estimates rather than exact underlying values. ([Basketball GM][4])

---

# 10. Durability, injuries and chronic conditions

## Endurance and durability must remain different

| Attribute         | What it controls                              | OVR treatment |
| ----------------- | --------------------------------------------- | ------------- |
| Stamina           | In-game fatigue                               | Included      |
| Recovery Rate     | Energy recovery between action and games      | Included      |
| Workload Capacity | Ability to sustain large minute loads         | Included      |
| Injury Resistance | Probability of suffering an injury            | Excluded      |
| Load Tolerance    | Injury risk under repeated workload           | Excluded      |
| Chronic Health    | Recurrence, permanent limitation and recovery | Hidden        |

A player can be excellent while healthy but unreliable. Lowering his healthy OVR because he is injury-prone hides that distinction.

Display these separately:

* **OVR:** Healthy current ability
* **Availability:** Expected ability to remain available
* **Potential:** Health-adjusted projected upside
* **Career Value:** OVR, age, potential, availability and contract combined

---

## Availability grade

[
Availability=
0.55(\text{Injury Resistance})
+
0.45(\text{Load Tolerance})
]

This can use the same letter-grade scale as the other categories, but it is not included in OVR.

---

## Hidden health data

Store hidden health values by body region:

| Hidden health field     | Purpose                                        |
| ----------------------- | ---------------------------------------------- |
| Ankle and Foot Health   | Lower-leg injury susceptibility and recurrence |
| Knee Health             | Knee injury susceptibility and recurrence      |
| Hip and Back Health     | Core, hip and back injury susceptibility       |
| Shoulder and Arm Health | Upper-body and shooting-arm susceptibility     |
| Hand and Wrist Health   | Ball-control and shooting-hand susceptibility  |
| Recovery Quality        | Natural recovery response after injury         |
| Chronic Burden          | Accumulated long-term physical limitation      |
| Recurrence Risk         | Elevated chance of repeating a prior injury    |

A low general Durability score raises broad risk. Body-part health determines where the risk is concentrated.

---

## Injury probability

A useful structure is:

[
p_{\text{injury}}
=================

\operatorname{clamp}
\left(
p_0
\times M_{\text{load}}
\times M_{\text{fatigue}}
\times M_{\text{age}}
\times M_{\text{history}}
\times M_{\text{durability}},
0,
p_{\max}
\right)
]

A simple starting durability multiplier is:

[
M_{\text{durability}}
=====================

1.50-\frac{Durability}{100}
]

This gives:

| Durability | Risk multiplier |
| ---------: | --------------: |
|          0 |           1.50× |
|         50 |           1.00× |
|        100 |           0.50× |

The exact coefficients must be calibrated against your desired injury frequency. Recent basketball research supports treating workload and prior health as meaningful parts of injury modeling, while reviews identify ankle and knee injuries as particularly common basketball concerns. ([PMC][6])

---

## What an injury should do

An injury can cause four different effects.

### 1. Missed games

This changes availability but not necessarily the player's permanent ratings.

### 2. Temporary rating penalties

[
TemporaryLoss_{i,t}
===================

Severity
\times BodyPartRelevance_i
\times RecoveryCurve_t
]

The penalty gradually declines during rehabilitation.

### 3. Missed development

[
M_{\text{health}}
=================

\operatorname{clamp}
\left(
0.25+
0.75(\text{Training Availability})
----------------------------------

0.30(\text{Chronic Burden}),
0,
1
\right)
]

A young player who misses most of a season loses valuable development time even if he eventually returns at full strength.

### 4. Permanent loss or reduced ceiling

[
CeilingLoss_i
=============

K
\times Severity
\times Chronicity
\times BodyPartRelevance_i
\times
(1-RehabResponse)
]

Where (K) is a tuning coefficient controlling the maximum possible permanent loss.

---

## Rehabilitation response

[
\begin{aligned}
RehabResponse={}&
0.35(RecoveryQuality)
+0.25(WorkEthic)\
&+0.15(Professionalism)
+0.15(Resilience)
+0.10(Coachability)
\end{aligned}
]

This means work ethic and professionalism help a player maximize rehabilitation, but they do not guarantee a complete recovery.

Severe lower-extremity injuries should have meaningful long-term downside. A study of NBA players found that fewer than half returned to previous performance levels within two years after severe lower-extremity injury, supporting a system where major injuries can affect availability, performance and career outlook rather than acting only as short absences. ([OUP Academic][7])

---

## Recommended injury-to-rating mappings

These are game-design mappings, not medical diagnoses.

| Injury area             | Most affected ratings                                                            |
| ----------------------- | -------------------------------------------------------------------------------- |
| Ankle, foot or Achilles | Acceleration, lateral quickness, change of direction, vertical leap, second jump |
| Knee                    | Acceleration, agility, vertical leap, workload capacity, contact balance         |
| Hip or back             | Strength, contact balance, agility, stamina, post containment                    |
| Shoulder or elbow       | Shooting, passing accuracy, upper-body strength, blocking                        |
| Hand or wrist           | Shooting, ball security, catch security, passing and rebound security            |

Do not reduce every rating after an injury. A knee injury should not automatically reduce Court Vision or Leadership.

---

# 11. How chronic injuries affect potential

Keep two different hidden ideas:

| Potential type          | Meaning                                                                                                    |
| ----------------------- | ---------------------------------------------------------------------------------------------------------- |
| **Talent Ceiling**      | What the player could theoretically become under excellent health and development                          |
| **Projected Potential** | What the player is currently likely to become after accounting for development traits, age and health risk |

Before an injury, low durability affects Projected Potential because the career simulations contain a higher probability of missed development or physical decline.

After a chronic injury:

* Current physical ratings may fall.
* Specific hidden ceilings may fall.
* Recurrence probability rises.
* Training availability falls.
* The potential career simulation is rerun.
* The displayed scouted potential gradually updates.

The raw talent ceiling can remain historically recorded internally, but the player's current health-adjusted potential should decline when the injury materially changes his future.

---

# 12. Optional hidden GM traits

These are useful for a franchise-management game, but they should not affect OVR or basketball potential directly.

| Trait              | Game effect                                                   |
| ------------------ | ------------------------------------------------------------- |
| Ambition           | Preference for winning, status, awards and major roles        |
| Loyalty            | Willingness to remain with a team or organization             |
| Financial Priority | Importance placed on salary during negotiations               |
| Role Acceptance    | Willingness to accept reduced touches, minutes or bench roles |
| Market Preference  | Preference for certain markets or locations                   |
| Ego                | Sensitivity to status, touches and organizational decisions   |

Role Acceptance can affect morale and chemistry, but it should not magically improve shooting or defense.

---

# 13. Exact changes I would make to your current screen

| Current setup                              | Recommended change                                                           |
| ------------------------------------------ | ---------------------------------------------------------------------------- |
| Inside Scoring                             | Rename to Rim Finishing                                                      |
| Post Finishing inside Inside Scoring       | Move to new Post Scoring category                                            |
| Post Fadeaway inside Mid-Range             | Move to Post Scoring                                                         |
| Pressure Free Throws                       | Make derived from FT Accuracy, Composure and Focus                           |
| Passing                                    | Keep; current three subratings are good                                      |
| Pressure Handling                          | Make derived                                                                 |
| Add Pace Control                           | Add to Ball Handling                                                         |
| No Off-Ball Offense                        | Add it                                                                       |
| No Screening category                      | Add it                                                                       |
| Second Jump in Offensive Rebounding        | Move to Explosiveness                                                        |
| Rebound Reading stored twice               | Store once and share it                                                      |
| No Off-Ball Defense                        | Add it                                                                       |
| Help Rotation in Interior Defense          | Move to Defensive IQ                                                         |
| Rim Deterrence stored directly             | Make derived                                                                 |
| Passing-Lane Anticipation in Stealing      | Move the anticipation component to Defensive IQ                              |
| Vertical Contest in Blocking               | Move to Interior Defense as Verticality                                      |
| Lateral Quickness and Agility inside Speed | Move to separate Agility category                                            |
| Physical Leverage stored directly          | Make derived                                                                 |
| Late-Game Conditioning stored directly     | Make derived                                                                 |
| Basketball IQ as one category              | Split into Offensive IQ and Defensive IQ                                     |
| Intangibles as one category                | Split into Competitive Makeup, Team/Leadership and hidden Development Makeup |
| No measurements layer                      | Add height, weight, wingspan and standing reach                              |
| No tendencies layer                        | Add behavior and play-style tendencies                                       |
| Durability included like a normal ability  | Display separately as Availability                                           |

---

# Final recommended size

This is the complete deep-simulation version:

| Section          | Main categories | Unique visible base ratings |
| ---------------- | --------------: | --------------------------: |
| Offensive skills |              10 |                          37 |
| Defensive skills |               6 |       20 additional ratings |
| Physicals        |               6 |                          17 |
| Mental           |               4 |                          17 |
| **Total**        |          **26** |                      **91** |

The defensive total has one fewer unique rating than its visible rows because Rebound Reading is shared with Offensive Rebounding.

Additionally:

* 5 hidden development traits
* Hidden body-part health values
* Optional hidden personality traits
* Measurements
* Tendencies
* Derived ratings

The user should not see all 91 ratings simultaneously on the Overview page. Show the 26 main category grades first, then reveal the subratings when the user opens a category. That preserves the depth of the simulation without turning every player page into a wall of numbers.
