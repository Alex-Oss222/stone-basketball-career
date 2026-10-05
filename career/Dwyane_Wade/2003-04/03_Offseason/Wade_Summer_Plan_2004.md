---
type: player_decision
status: planned
date: 2004-06-24
owner: player
---

# Wade's 2004 summer plan

Recorded on the career date, June 24, 2004, from the user's framework for Wade's offseason. Miami's season ended April 28 (first-round loss to Milwaukee, 1-4). The plan covers the rest of the offseason from today. The weeks from April 29 to June 23 passed without a recorded plan and are not credited after the fact.

## What this plan is and is not

- It is Wade's own decision about his summer work, his private spending and what he asks of the front office.
- It is not an ability change. Wade's 2004-05 expectation is already fixed by the season close (`2004-05/wade_expected_profile.json`: previous expectation, simulated 2003-04 results, generic age step), and a plan never adds rating points (AGENTS.md; `docs/live_player_milestones.md`). Udonis Haslem's ability follows his real career like every real player's; Wade's sessions with him change nothing in the engine.
- What it does decide: Wade attends Miami's designated program, which his contract pays for (below), and the request on Trevor Ariza goes to the front office.

## Contract facts that shape it

| Item | Recorded value | Source |
|---|---|---|
| 2004-05 counted salary | $2,361,800 | `Contracts/contract_records.json` |
| Protected 2004-05 cash | $1,889,440 | same |
| Designated offseason skill and conditioning program (at most two weeks) | $236,180 incentive, included in Salary | same, incentive `conditioning_program` |
| Preseason conditioning standard (Exhibit 1 test) | $236,180 incentive, included in Salary | same, incentive `physical_condition` |
| Other recorded income | None | the save records no endorsement income |

Wade therefore attends Miami's designated block when the club schedules it, and the private work is built around that block, never instead of it. Specialists are hired by the block, not on salaries.

## Evidence the work starts from (simulated 2003-04)

75 games, 70 starts, 35.0 minutes, 17.9 points, 4.8 rebounds, 4.5 assists, 1.6 steals; 52.0% from the field, 39.7% from three on 2.4 attempts, 90.9% at the line; two playoff games after sitting Games 1 to 3 of the Milwaukee series. Profile weakness to target: after a mistake he can rush the next possession, and a second defender can change his first read.

## Who does the work

| Need | Provider | Arrangement | Status on the date |
|---|---|---|---|
| Medical review, treatment, recovery | Miami's medical staff | Team-controlled; review of season load and the two in-season interruptions first | To request from the club |
| Strength and durability | Miami's strength staff; approach to Tim Grover (Attack Athletics) for concentrated blocks | One private lead, not a second organization | Approach planned, not agreed |
| Shooting | Dave Hopla or a qualified Miami-area shooting coach | Several multi-day visits | Approach planned, not agreed |
| Ballhandling and defense | Erik Spoelstra and Miami's staff | Integrated with Miami's system and terminology | To request from the club |
| Mental performance | Jim Loehr's Orlando practice (LGE) or another qualified performance psychologist | Assessment plus periodic sessions | Approach planned, not agreed |
| Nutrition | A registered sports dietitian | Assessment, plan, weekly or biweekly review; supplements and bloodwork only under medical oversight | Approach planned, not agreed |

The user's framework names Miami staff of the era (Bill Foran, Ron Culp, Jay Sabol, Vinny Aquilino). They are not yet in Miami's organization records, which hold basketball decision makers only, so the plan refers to the staff functions. Every private specialist is an approach: whether he takes the work is recorded when it happens.

## Priorities

**Wade:** ballhandling under pressure, defensive discipline, physical durability, and a wider range of situations for a jumper that already works. Do not rebuild his mechanics.

- Body: posterior chain, hips, single-leg strength, landing and deceleration, ankle and calf durability, trunk; repeat-sprint conditioning later. Keep his weight useful (220 pounds on the profile), not chase mass.
- Handle: weak-hand advance against pressure, retreat dribble, escaping sideline traps, splitting and rejecting screens, snake dribble, protecting the ball from a second defender, keeping the dribble alive. Every drill ends with a decision against a live defender.
- Shooting: relocation catch-and-shoot, one-dribble pull-ups both ways, pull-up when the defender goes under, hesitation jumper, side-step, limited late-clock step-back, balanced transition three; keep the 12-to-18-foot pull-up.
- Defense (Spoelstra's staff): over screens without opening the hips early, recovery after contact, when to go under, closeouts that do not give up the drive, tag and recover, no unnecessary help, seeing man and ball.
- Mental: a consistent between-possession reset; film the possession after every error; measure whether bad possessions still come in clusters. The target is breaking mistake, rushed possession, second mistake.

**Haslem (private invitation, not a Miami program):** Wade invites him to train together; Haslem has no 2004-05 contract on the date (his 2003-04 agreement was $366,931), so this is between the two players. The shooting coach owns the mechanics; Wade is his partner and runs the actions. Progression only when the stage before holds: 15 to 18 feet (elbows, foul-line extended, short baseline, pick-and-pop), then 18 to 21 feet with the same mechanics, then the set corner three off Wade's penetration, then other spots around the arc, top of the arc last. The camp aim is an uncontested shot without changing his form, not volume.

**Live work (July to September):** Wade and Haslem against two defenders with coverage changing without warning (drop, switch, trap, show, under); Caron Butler, who is under contract for 2004-05, invited for bigger-wing matchups; then full-court possessions, transition, end-of-clock and end-of-quarter possessions, possessions right after a turnover, games with officials when available. The last month is for making the summer's work hold up against defenders, not for adding moves.

## The Ariza request

On April 28 Wade could only recommend scouting him. On the career date the draft is over and Trevor Ariza went undrafted in the simulated draft (Miami's No. 54 draw had him among its three options and took Christian Drejer; Houston's No. 56 draw also passed on him). He is an undrafted free agent from July 1.

Wade's position: "Trevor Ariza is somebody I want our scouts to take seriously. I like the size, rebounding, activity and defensive upside next to me. I am not telling you what to pay him. Do the work, and if our scouts agree, find a way to get him."

Evidence available now: one UCLA season, 11.6 points, 6.5 rebounds, 2.1 assists, 1.68 steals; 23.7% from three, 50.4% at the line; strength questions; the June pre-draft camp measured him at 6'7" without shoes, 7'2" wingspan, 201 pounds (`library/2004/league/nba_2004_prospect_evidence.json`). Nothing after the date is used. The request is filed in `10_Free_Agency/wade_requests.json`; the front office weighs it by Wade's standing on the date (franchise, weight 0.8) and decides. Ariza is not a star, so no consultation applies.
