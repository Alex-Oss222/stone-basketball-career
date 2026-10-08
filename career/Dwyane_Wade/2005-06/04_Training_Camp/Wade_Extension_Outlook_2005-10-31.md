---
type: player_decision
status: planned
date: 2005-10-31
owner: player
---

# Wade's contract extension outlook

Recorded on the career date, October 31, 2005, from the user's extension framework for Wade ("Revised Contract Extension Framework, 2006-07 negotiations, planning only"). The negotiation itself is in the future: this records Wade's own position and two scouting recommendations, nothing else.

Authority: Wade states his terms and answers Miami's offer. Miami's AI/GM decides whether to offer, what it offers and whom it drafts. The engine decides chance outcomes.

## What this is and is not

- It is Wade's dated preference for his rookie-scale extension and his request to the scouting department.
- It is not an offer, a negotiation or a contract. No contract, draft record, career date or game outcome changes today.
- Miami may decline to offer. If it does, Wade plays out his rookie contract.

## Contract facts on the date

| Item | Recorded value | Source |
|---|---|---|
| Current contract | Rookie scale, signed 2003-07-21, No. 5 pick, 120% of scale | `00_Team/Finances/contract_schedules.json` |
| 2005-06 counted salary | $2,526,600 | same |
| 2006-07 | $3,201,202, team option exercised by Miami on 2005-10-31 | `League/option_decisions.json` (`2006-07-option-wadedw01-team_option`) |
| Extension window | From the day after the July 2006 moratorium to October 31, 2006, the October 31 before his last option season (cbafaq05 Q52) | `library/2005/league/nba_2005_cba_rules.json`, `extensions` |
| Extension limits | Up to five seasons beyond 2006-07; first year up to his maximum; raises up to 10.5% of the first extension year (Q52); one option season, the last (Q51) | same |
| Miami's decision day | 2006-10-31 (`runtime/extensions.py`, `docs/extensions.md`) | same |
| If no extension | Restricted free agency in July 2007 if Miami tenders a qualifying offer, unrestricted otherwise | same |

## Wade's terms

Recorded in `wade_requests.json` beside this page (subject `extension_terms`).

| Term | Wade's position |
|---|---|
| Extension begins | 2007-08 |
| Length | Five additional seasons (2007-08 to 2011-12) |
| Salary | First year 20% below his fair market value on the decision day (the midpoint of the 15% to 25% range the user considered) |
| Guarantee | First four seasons fully guaranteed |
| Fifth season (2011-12) | Miami team option |
| Raises | Up to 10.5% of the first-year salary |
| Trade protection | None requested |
| If Miami will not offer | Play out the rookie contract |
| Purpose | Give Miami room to keep and add talent |

"Fair market value" is the same benchmark Miami's front office already computes for every extension: his market price for his production on the decision day, within his minimum and his maximum under the cap rules known that day. It is set on 2006-10-31 from the closed 2005-06 season, not today. The user's illustration used a $12 million benchmark (first year $9.6 million, $58.08 million over five seasons against $72.6 million); that figure is an illustration, not a valuation, and the sim does not use it.

## Wade's words

"I want to remain with the Miami Heat long term and help this organization build a championship-caliber roster. When I become eligible to negotiate my extension, my preferred starting point is 20% below my established fair market value. I am willing to discuss a five-season extension with four guaranteed seasons and a team option in the fifth year. I understand that the final terms must comply with the collective bargaining agreement and be agreed upon by Miami's front office. The purpose of the discount is to provide meaningful financial flexibility for the team."

## How the front office weighs it

On 2006-10-31 Miami decides by its own rule whether to offer (his worth against the mid-level, the same rule as every club). If it offers, it adopts each of Wade's terms that is legal and at least as favourable to Miami as its own rule: the discounted first year, the five seasons, the raises within the limit and the final-season team option. The payroll test uses the offered salary. The offer then opens as Wade's pending decision and the career clock stops until the user accepts or declines it on its page. Nothing is accepted in advance. An accepted fifth-season option is decided by Miami on its deadline in June 2011 like any other team option.

## Scouting recommendations for the 2006 draft

Recorded in `../09_Draft/wade_requests.json` (subject `draft_prospect`, `evaluate`). Wade's words: "Separately, for the 2006 offseason, I would like the scouting department to keep Kyle Lowry of Villanova and P.J. Tucker of Texas under consideration. These are recommendations for evaluation, not demands for roster transactions."

| Prospect | School and position | What Wade asks the scouts to watch |
|---|---|---|
| Kyle Lowry | Villanova, PG | Perimeter defense, playmaking, competitiveness, development as a lead guard |
| P.J. Tucker | Texas, F | Physical defense, rebounding, positional versatility, offensive development |

Miami holds its own 2006 first- and second-round picks (`00_Team/Finances/draft_picks.json`). Whether either player enters the 2006 draft, where he ranks on the draft-night boards and whom Miami takes are decided by the simulation. On Miami's own pick, a recommended prospect still available in the best available tier is always among Miami's candidates and his chance is raised by Wade's standing weight (`runtime/draft.py`); otherwise the recommendation changes nothing.

## Next checkpoint

October 31, 2006: Miami's extension decision on Wade. Before it, the June 2006 draft weighs the scouting recommendations on Miami's own picks.
