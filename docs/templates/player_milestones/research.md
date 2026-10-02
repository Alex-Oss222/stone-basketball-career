# Research behind the milestone templates

[Template collection](README.md) · [Filled previews](../../examples/player_milestones/README.md)

Reviewed October 2, 2026. The layouts and reply prompts are original design choices for this simulation. Later publications inform the kinds of information a player needs; they do not establish the rules or events of the 2003 career.

The expanded [contract negotiation and free-agency research](contract_negotiation_research.md) adds a primary 1999 agreement source, detailed compensation analysis, team-aware presentation, four ordinary offers and a reserved fifth incumbent matching record. It also distinguishes the local demonstration and isolated workflow module from remaining live-career integration.

## Source use

| Source | What informed the design | Boundary |
| --- | --- | --- |
| [NBA CBA 101, November 2024](https://cms.nba.com/wp-content/uploads/sites/4/2024/11/2024-25-CBA-101.pdf), contract structure, extensions, trade rules and free agency | Separate salary, protection, options, signing conditions, rights and consent | Modern reference only; numerical limits and deadlines must be verified for the career's agreement |
| [NBPA agreement page](https://www.nbpa.com/cba) | Identify the applicable agreement instead of treating every season alike | Current agreement is not the 1999 agreement |
| [NBA free-agency explainer](https://www.nba.com/news/free-agency-explained) | Distinguish offers, negotiations, options and free-agent status | Concept reference; do not import its modern calendar or matching window |
| [New Orleans player-development program](https://www.nba.com/pelicans/news/player-development-program-crucial-pelicans-offseason) | Individual focus and coaching attention during summer | Process reference; no historical player's workout becomes Wade's workout |
| [Lakers strength-program update](https://www.nba.com/lakers/news/180516-weightroom-update-with-gunnar-peterson) | Player-specific offseason priorities communicated by staff | No borrowed workload prescription |
| [Texas Legends offseason development discussion](https://texas.gleague.nba.com/players-get-better-off-season) | Balance recovery, physical preparation and focused skill work | Training organization, not evidence for a fixed rating increase |
| [Clippers offseason player capsule](https://www.nba.com/clippers/features/offseason-player-capsule-blake-griffin-patten-120701.html) | Connect season review with a specific summer focus | Layout/process reference only |

The central design inference is that each milestone should answer three questions: **What changed for me? What can I decide? What happens after I reply?** The offer comparison, drill log, role review and trade transition are different because the player has different kinds of control at each moment.

## Sources governing this repository

| Record | Use |
| --- | --- |
| [Operating rules](../../../AGENTS.md) | Player/AI-GM authority, no hindsight, real-league/simulated-club boundaries |
| [1999 rule inventory](../../../library/2003/league/nba_1999_cba_rules.json) | The existing branch's era-specific contract and free-agency inputs |
| [1999 FAQ extract](../../../library/2003/league/cba_1999_salary_cap_faq_extract.txt) | Existing historical source extract; its online page could not be retrieved during this review |
| [2003-04 cap and rookie-scale data](../../../library/2003/league/nba_2003_04_cap_rules.json) | Published/activated salary inputs only; never future cap knowledge |
| [Front-office workflow](../../front_office.md) | Existing rookie offers and player requests; offers remain club-owned |
| [Build roadmap](../../ROADMAP.md) | Which outcomes still need an implementation before becoming playable |

Under the repository's 1999 inputs, a first-round rookie-scale deal has a different structure from a modern rookie contract. The live page must read its era's structure rather than copy the modern two-option pattern. Likewise, RFA matching periods, eligibility, raises, option deadlines and signing windows are parameter fields, not evergreen constants embedded in the template.

## Display rules derived for this simulation

- Show guaranteed and conditional compensation separately, with the salary schedule underneath. Do not count an unexercised option or an unearned incentive as protected cash.
- Treat a team's stated role as a basketball plan with a speaker and date, not an enforceable minutes promise.
- Verify the actual trade-consent basis. For an ordinary assignment with no applicable consent right, show the transition and available player response; a sign-and-trade also requires a new-contract decision.
- Give training a focus, a staff-agreed workload, a repeatable observation and a review. Practice results never become NBA box-score results or automatic attribute points.
- Use era-specific deadlines and actual sources. The [workflow notes](workflow.md) flag an existing rookie-option deadline inconsistency for verification before activation.
