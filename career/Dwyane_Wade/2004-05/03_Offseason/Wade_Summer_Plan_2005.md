---
type: player_decision
status: planned
date: 2005-06-16
owner: player
---

# Wade's 2005 summer plan

Recorded on the career date, June 16, 2005, from the user's 2005 offseason framework for Wade. Miami's season ended May 19 (East semifinal loss to Atlanta, 2-4); the Finals closed June 16 (Sacramento over Toronto, 4-0). The plan covers the rest of the offseason from today, preparing for 2005-06. The weeks from May 20 to June 15 passed without a recorded plan and are not credited.

Authority: Wade controls his personal decisions and requests. Miami controls roster transactions. The simulation controls development outcomes and tournament results.

## What this plan is and is not

- It is Wade's own decision about his summer work and what he asks of the front office.
- It is not an ability change. Wade's 2005-06 expectation is already fixed by the season close (`2005-06/wade_expected_profile.json`: previous expectation, simulated 2004-05 results, generic age step and the role-growth rule). That rule raises his expected usage from 22.7% to 27.3%, because his 2004-05 true shooting (65.7%) was well above the league's (51.6%), and lowers his accuracy by about 1.8% for the added shots. The plan adds nothing to it and does not change the engine's development swing (AGENTS.md; `docs/live_player_milestones.md`).
- What it does decide: Wade attends Miami's designated offseason program, which his contract pays for (below); his three skill priorities go to Miami's staff; his request on Udonis Haslem goes to the front office.

## Contract facts that shape it

| Item | Recorded value | Source |
|---|---|---|
| 2005-06 counted salary | $2,526,600 | `Contracts/contract_records.json` |
| Protected 2005-06 cash | $2,021,280 | same |
| Designated offseason skill and conditioning program (at most two weeks) | $252,660 incentive, included in Salary | same, incentive `conditioning_program` |
| Preseason conditioning standard (Exhibit 1 test) | $252,660 incentive, included in Salary | same, incentive `physical_condition` |
| Regular-season minutes (at least 1,200) | $252,660, Unlikely | same, incentive `minutes` |
| Achievement (at least 17.0 points per game in at least 60 games) | $252,660, Unlikely | same, incentive `achievement` |
| 2006-07 | $3,201,202 team option; Miami decides by 2005-10-31 | same |

Neither included incentive is earned by filing this plan. Attendance and the test need their own dated evidence (`runtime/incentives.py` reads the 2005-06 camp review and reply); until then they stay unrecorded.

## Evidence the work starts from (simulated 2004-05)

Regular season: 76 games, 76 starts, 36.2 minutes, 21.3 points, 5.4 rebounds, 4.0 assists, 1.4 steals, 1.2 blocks, 1.3 turnovers; 53.0% from the field, 42.9% from three on 2.7 attempts, 93.2% at the line, 65.7% true shooting. Playoffs: 12 games, 20.5 points, 50.0% from the field, 94.8% at the line. Honors: All-NBA First Team, All-Star, third in MVP voting, East Player of the Month three times. Source: `Stats_and_Awards/2004-05/README.md` and `Stats_and_Awards/League/2004-05/Playoffs/Playoff_Stats.md`.

## Main objective

Make Wade a more disciplined one-on-one defender, a more selective high-volume scorer and a more reliable creator for teammates. The offense is already highly efficient; the goal is better decisions as his scoring load rises, not replacing his scoring strengths.

## Training priority allocation

These shares describe the requested distribution of basketball skill work, not guaranteed staff assignments or engine rating changes. Medical supervision, conditioning and strength work continue alongside them.

| Priority | Share | Primary objective |
|---|---:|---|
| Man-to-man defense | 35% | Containment, screen navigation and defensive discipline |
| Shot selection | 30% | Recognize high-value scoring chances and avoid unnecessary difficult attempts |
| Passing | 25% | Help-defense reads, passing timing and decisions under pressure |
| Skill maintenance | 10% | Shooting mechanics, ball control and established counters |

### Priority A: man-to-man defense

Contain opposing guards without depending on steals or spectacular recoveries.

1. Isolation containment from the top, wings and corners: positioning, keeping the ball handler from his spots, recovering without fouls.
2. First-step recognition: read a player's driving preference and protect against the first move without overcommitting.
3. Ball-screen navigation: over, under, recovery after contact, holding responsibility when the coverage changes.
4. Larger wings: controlled possessions against stronger opponents, positioning and resistance without reaching.
5. Late-clock isolation defense: a contested attempt without a foul.
6. Discipline: fewer gambles; never leave the assignment without a real help responsibility.

Evaluation: Miami's coaches set a baseline from comparable practice possessions and film, then track clean blow-bys, containment, unnecessary fouls, quality contests, missed assignments and screen-recovery mistakes against it. No improvement is awarded subjectively.

### Priority B: shot selection

Not fewer shots for their own sake: telling the right aggressive possession from a forced one. With an advantage he attacks the rim, draws contact, takes the clean in-rhythm jumper or creates an open shot for a teammate; when a second defender removes the advantage he passes, resets or changes the attack.

1. Early-clock contested jumpers that could have become better possessions.
2. When a defender concedes the pull-up rather than contesting the drive.
3. Finish, draw the foul or pass after penetration.
4. Shot-clock awareness: forced late-clock attempts against avoidable early-clock ones.
5. Reading changing coverages before deciding to shoot.
6. Film of the possession after every turnover or miss, looking for rushed decisions.

Evaluation: shot location, shot-clock context, defender pressure, turnovers after forced attacks and how often a possession creates a high-quality shot for Wade or a teammate.

### Priority C: passing and playmaking

Timing, finding the second defender and keeping the advantage after drawing help.

1. Drive-and-kick to the weak-side shooter when a defender rotates.
2. Pick-and-roll: pocket passes, the rolling big, reads when the screener's defender commits.
3. Against traps: keep the dribble when useful, no desperate cross-court passes, find the first release.
4. Weak-hand delivery when the preferred angle is taken away.
5. Skip passes when help opens the far side.
6. Secondary creation: give it up, relocate, get it back and continue.
7. Late-clock playmaking without spending too much of the clock.

Evaluation: turnovers by cause, missed open teammates, good reads after help, timely passes and possessions where his advantage leads to a teammate's score. Assists alone are not evidence, since teammates must finish.

### What receives less time

Flashy new isolation moves, rebuilding his shooting mechanics, extra long-range volume, nonessential dribble combinations and weight gain. None is prohibited.

## Who does the work

| Need | Provider | Arrangement | Status on the date |
|---|---|---|---|
| Medical assessment, treatment, recovery | Miami's medical staff | Team-controlled; first step, June 16 to 30 | To request from the club |
| Defense, shot selection, passing within Miami's terminology | Erik Spoelstra and Miami's assistants, with the video staff | Primary development structure | To request from the club |
| Strength and conditioning | Miami's strength staff | Integrated with the skill work | To request from the club |
| Private specialists (shooting or conditioning coaches from the 2004 approaches) | By the block, if useful | Contact again; the 2004 approaches establish nothing for 2005 | Not contacted |
| Live competition | Professional guards and wings Wade invites | Small-sided and full-speed sessions | Invitations not yet made |
| Udonis Haslem | Private invitation between the two players | Screening, pick-and-roll passing, competitive work; does not depend on his signing with Miami | Invitation not yet answered |

## Progression

| Period | Main work | Review |
|---|---|---|
| June 16 to 30 | Medical assessment, film study, baselines | The specific defensive and decision-making weaknesses |
| July | Isolation defense fundamentals, shot-choice recognition, basic passing reads | Controlled live repetitions against the baseline |
| August | Changing coverages, small-sided competition, faster decisions | Skills under game-like pressure |
| September to camp | Full-speed possessions, system integration, conditioning for the test | Staff review of readiness for the preseason |

An ordinary week: four or five skill days, integrated conditioning and planned recovery; volume, restrictions and workloads need qualified staff approval. Wade asks for a documented skills review about every two weeks when the schedule allows; each review separates completed work from planned sessions.

## Miami's designated offseason program

Wade commits to attending Miami's designated program for its permitted period of up to two weeks, whenever the club schedules it. His private work fits around it, never instead of it.

## The Haslem request

Recorded in `10_Free_Agency/wade_requests.json` (subject `free_agent_target`, `pursue`, term `multi_year`). Wade's words: "I want the Miami Heat front office to make bringing Udonis Haslem back a priority this offseason. I want us to pursue a multi-year agreement, not another temporary one-year arrangement. I believe his defensive toughness, rebounding, screening, physical play and familiarity with me would help us compete. I understand that Toronto controls his restricted free agency if it makes a qualifying offer. I still want our organization to explore a serious offer. The final contract has to work financially, but my preference is clear: bring Haslem back to Miami for several seasons."

On the date Haslem is a Toronto player on a one-season $620,046 contract ending June 30, 2005, with two seasons of service: a restricted free agent if Toronto tenders a qualifying offer (Toronto may then match an offer sheet), otherwise unrestricted. Miami's general manager values him, chooses the mechanism and the terms, and may decline or abandon the pursuit; Wade sets no salary and cannot guarantee acceptance. Until a contract is executed Haslem stays off Miami's signed roster. The outcome (whether Miami pursues him, any offer actually made, his answer, Toronto's tender and match decisions, the transaction) is reported from the market's own records.

## The Ray Allen request

Added the same day: "One more thing: if the contract situation is the same, try to sign Ray Allen to a multi-year plan." Recorded in `10_Free_Agency/wade_requests.json` (subject `free_agent_target`, `pursue`, term `multi_year`). Allen's Seattle contract ($14,625,000 in 2004-05) ends June 30, 2005, the same expiring situation as Haslem's, but he is unrestricted after nine seasons and Seattle holds his Bird rights. Simulated 2004-05: 78 games, 39.5 minutes, 22.9 points, 44.3% from three on 6.3 attempts. Miami's 2005-06 commitments are about $32.5 million against the $49.5 million cap, so a bid needs Miami to clear its cap holds, which could also limit what is left for Haslem. Allen is a star under the franchise consultation rule: Miami must ask Wade before signing him, and the user approved in advance ("approve"); the answer is recorded on the consultation when Miami asks. Wade sets no terms and Miami may decide not to bid.

## Other decisions in the framework

- Chris Bosh keeps his own development settings (`career/Chris_Bosh/Development_Profile_2004-10-01.md`); nothing in this plan is copied to him.
- The June 28 draft: no request from Wade; Miami's No. 58 pick follows its own process.
- USA Basketball: the 2006 World Championship places come from the simulated 2005 FIBA Americas and the existing qualification rules; Wade's standing instruction to accept invitations unless injured stands.

## Next checkpoint

Miami schedules its designated offseason program and the staff confirm the baselines; the front office answers the Haslem request in the summer market (talks from July 1).
