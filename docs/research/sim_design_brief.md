# Research: how management sims and front offices model free agency, negotiation and trades

Research report gathered October 2, 2026 for `docs/front_office_design.md`. Mechanics are attributed to their sources; the design doc says which were adopted and marks every constant as judgement.

**Scope and method.** Read first: `AGENTS.md`, `docs/front_office.md`, `docs/contract_negotiation_engine.md`, `runtime/contract_negotiation.py`, plus `runtime/front_office.py`, `decisions.py`, `cba.py`, `contracts.py`, `trajectories.py`, `protagonist.py`, `rookie_contract.py`, `private_service.py`, the cap sheet, `free_agent_rights.json`, `holdings.json`, `docs/ROADMAP.md` and the negotiation research template. Nothing in the repo was modified. Basketball GM (ZenGM) was read from source in a shallow clone at `/home/user/zengm-games/zengm` (outside the repo). The egress proxy blocked zengm.com, basketball-gm.com, cbafaq.com, hoopsrumors, ESPN, The Ringer, FiveThirtyEight, OOTP/FM sites and the UNH 1999 CBA PDF; Wikipedia was readable; for the rest I relied on search-result summaries, so numbers quoted from those articles are as summarized, and era rules I could not read from the primary text are marked **verify**.

**Cross-cutting principles (fit the repo's own rules).** (a) Rules decide clear cases; chance decides only close ones, as `front_office.request_override` already does. (b) Every draw is a `*.decision.json` (`runtime/decisions.py`: options with probabilities strictly in (0,1), journaled on Railway, never re-rolled). (c) The AI/GM and every real club's "posture" are computed from evidence on the career date only (2002-03 rates, contracts, rights), never from `library/careers` trajectories or real later transactions. (d) Draws are keyed by date + content hash, so re-proposing the same offer/trade on the same date returns the same answer: ZenGM made this a deliberate anti-exploit design in its trade finder ("keeps giving the same answer unless something has changed") [S10].

---

## 1. Free-agency market

**Mechanics worth adopting**

1. **Market-set asking prices, not a value table.** ZenGM runs a mock auction before each free agency (`normalizeContractDemands.ts`): 60 annealed rounds in which clubs with cap space bid on the best available players; a player with several bids scales his ask up, one with none scales it down; demands are bounded by min/max contract [S3]. Translate: Miami's view of a free agent's ask = base value from on-date evidence × a *market-pressure* multiplier computed from the 28 real clubs' cap room on the date (`contracts.club_ledger` already gives committed/conditional/holds per club) and from the player's tier. Real clubs' cap positions are facts that existed on the date, so this is not hindsight; real July signings are not.
2. **Willingness as a mood sum → sigmoid.** ZenGM's redesigned mood [S1,S2,S4]: components market size (−2..2), facilities (−2..2), team performance (−2..2 from win%, negatives doubled for basketball), hype (−2..2), loyalty (seasons with club / 8 plus a re-sign bonus), trades (−(tradedAwayNormalized − 5)/4, where players traded away are weighted by a sigmoid of their value so dumping scrubs does not count, and decayed 0.75/0.5/0.25 over three seasons), playing time (×10, capped at 2), **rookie-contract +8** (their stand-in for restricted free agency), relatives +2. Four traits multiply components: Fame (market, hype, playing time ×2.5), Loyalty (loyalty, trades ×2.5; market ×0.5), Money (facilities ×1.5; market, performance ×0.5), Winning (performance ×2.5; market, playing time ×0.5). `probWilling = 1/(1+exp(−0.7·sum))`, with up to +10 for 30 days unsigned, minus a term that grows with player value (stars are pickier, capped at 4 when re-signing your own player — the "superstar fickleness" cap [S6]), and −3 for AI clubs so more AI players test the market [S4]. A poor mood also raises the ask by up to 50% (`×bound(1 + 0.5·(−sum)/10, 1, 1.5)`). Mood affects *only* negotiation, nothing on-court [S1]. Trades made after a player is already a free agent no longer affect him [S7].
3. **Demand decay and patience.** ZenGM lowers every unsigned player's ask daily by `50·√(maxContract/20000)` (thousands), floored at the minimum, and shortens the term of cheap contracts [S5]. Baseball Mogul's help page adds the opposite lever: after a couple of low offers players get impatient and *raise* the ask; "greedy/egotistical" personalities want the first offer within 5% of the ask, "modest/generous" tolerate 20% [S13]. OOTP: younger players want more money for longer deals, older ones take less for length; a rejected offer usually moves the player's stated demand [S12].
4. **Agents and leverage.** Agent leverage = productivity + value to the club + interest from other clubs [S22]; agents argue from comparables and know cap projections [S23]. The 2003 Arenas case is the era's textbook: Washington's sheet started about $8.5M, Golden State could offer only about $4.9M with Early Bird rights, so it could not match within the 15-day window and lost him [S19]. Calendar for the live checkpoint: negotiations from July 1, cap ($43.84M) announced July 15, first signings July 16, 2003 [S20].
5. **How clubs actually value room.** Staying over the cap keeps Bird rights, sign-and-trade and trade-exception routes and the mid-level; cap space is increasingly "weaponized" to absorb unwanted contracts for picks rather than to chase stars [S21]. Sign-and-trades exist because the incumbent can offer more money/years and would otherwise lose the player for nothing; they needed ≥3 seasons [S16]. Base-year compensation (re-signing with >20% raise counts at the greater of 50% of new salary or old salary in trades) existed precisely to stop signing-to-trade [S18].

**Inputs needed.** Dated free-agent pool (from `nba_2003_expiring_contracts.json`, `nba_2003_free_agent_rights.json`), per-player: age, 2002-03 rates (veteran ratings), rights status and hold, QO status; Miami: cap sheet, exceptions ledger (MLE = average salary, $1M exception), depth-chart minute gaps, owner tax tolerance (new `team_config` field); league: real clubs' room on the date.

**Chance (all journaled).** Per free agent per season: trait draw (F/L/$/W) and a priority vector (money, years, security, role, winning, location) drawn once at market entry; acceptance of each Miami offer: `p = sigmoid(k·(utility(offer) − utility(best alternative)))`; patience break/walk-away; arrival of a rival bid that raises the ask. World model D already resolves everyone Miami does not sign by real history; the real destination must stay invisible to the AI/GM before the decision, and if Miami's draw wins, rule 2 removes the player from his real club.

**Pitfalls.** Loyalty discounts that let the user re-sign everyone (cap the re-sign value term, as ZenGM does); hoarding (roster 15, tax line, incomplete-roster charges already modeled in the cap sheet); the "+8 rookie" shortcut masquerading as RFA — the repo already has true RFA with holds and QOs, so use mood only for willingness/ask, not legality; letting mood changes re-roll (draw once per offer version per date); using Miami's own cap-space knowledge of July 15 before July 15 (`contracts.cap_rules` already refuses this).

**Repo extension.** New `runtime/market.py` (pool on date, ask = value × pressure × mood multiplier, priorities, patience); `runtime/front_office.py` gains `market_value()` beyond the current minutes-prorated minimum→MLE line, a `need_score()` from the depth chart and a bidding policy (open ~85-90% of own valuation, concede years/guarantees before dollars, hard walk-away); offers flow through the existing `contract_negotiation.submit_offer` with attestations produced by a new adapter that calls `cba.py`/`contracts.py` for legality; player answers become `*.decision.json` in `01_Free_Agency/<date>/`; `wade_requests.json` subjects extended (`free_agent_target`, `role`).

---

## 2. Contract negotiation

**(a) Wade ↔ Miami (user is the player).**
- Keep the repo's 4+1 comparison desk and immutable offer versions; add a **terms model** richer than `salary_schedule`: raise % (1999: 10%, 12.5% with Bird/Early Bird), option kind (player/team/ETO), guarantee by season, trade bonus (≤15% of remaining salary [S17]), incentives flagged likely/unlikely, signing-bonus field with the double-count guard the research template already specifies. 1999-era limits: max 6 years (7 with Bird), 25/30/35% max tiers or 105% of prior salary (already in `nba_1999_cba_rules.json`).
- **Promises** (Football Manager): before money, agree playing-time status and a future-playing-time pathway; broken promises make players unhappy, trigger transfer requests and a permanent "lost trust in the manager" trait [S14,S15]. Translate: Miami may attach dated role statements to an offer (`promises.json`), evaluated at season end from closed minutes/starts; a broken promise lowers Wade's loyalty weight and raises his later ask/exit probability through his *own* decisions, exactly the channel `AGENTS.md` allows.
- **Wade's leverage levers** (user decisions, rule-checked): hold out as an unsigned pick (he counts at 100% of scale and cannot play), the rookie extension window after year 3, accepting the QO to reach unrestricted status, signing an outside offer sheet (the 15-day match flow already built), requesting a trade. Miami's response rules: sign the rookie at 120% after July moves (already coded); match an offer sheet when its surplus value ≥ 0 and the tax line allows, drawn only when the margin is small.
- **Standing** already drives request weights; use the same ladder (unsigned rookie 0.15 … franchise 0.8) as the player-value term in the willingness sigmoid, so Wade's leverage grows with simulated production and awards only.

**(b) Miami's AI/GM ↔ other free agents and their agents.**
- Valuation: **surplus value** = dollar value of projected production − salary over the contract, with an age curve. Public models price a win at roughly $1.8-2.2M (2015), about $2.6M for free agents once rookie-scale bargains are excluded [S26], and project production with an RPM-style aging curve [S25]; aging studies put the peak at 26-27, decline from about 30 and a cliff in the mid-30s [S27,S28]. Scale these to the 2003 cap ($43.84M ≈ 55 wins' worth) rather than copying dollar figures.
- Negotiation loop: ask (from §1) vs Miami's ceiling; counter cadence with a patience counter; the agent's "comparables" are the on-date contracts in `nba_2003_contracts.json`; concessions ordered years → guarantees → options → dollars; sign-and-trade considered when the player is leaving anyway (must be ≥3 seasons and respects BYC [S16,S18]).
- Each round's player reaction is a journaled draw; the GM's own moves are deterministic rules so the user can audit them in the phase note.

**Pitfalls.** Agent asks anchored to the user's offers instead of the market; infinite re-offers (count offers per player per window; patience ends negotiations); letting "principal terms" absorb coaching pitches (the module already forbids this); treating options and incentives as guaranteed money (template already separates them).

**Repo extension.** `contract_negotiation.Terms.validate` stays; add `cba.terms_errors(terms, status, era)` for raises/length/options/trade-bonus/BYC consequences, an `exceptions ledger` (MLE/$1M usage per season), and extension/QO windows (**verify** exact 1999 extension rules from CBA Art. VII §7 before use). Record promises next to the negotiation log; evaluate them in the year-end reporter.

---

## 3. Trades (Miami ↔ real clubs with no simulated front office)

**Mechanics worth adopting (ZenGM `ValueChangeCalculator.ts` [S8], `makeItWork.ts` [S9], `propose.ts`, `updateStrategies.ts` [S11]).**
1. **Asset value**: z-scored player value, plus a *contract value* term = (expected salary for that value − actual salary), capped at +0.1; expiring deals count 0. Strategy multipliers: rebuilding ×1.1 for future picks, ×1.075 at ≤19 down to ×0.9 at ≥29; contending ×0.825 for picks, ×0.8 at ≤19 rising to ×0.95 at 24. Contract term weighted ×2 when rebuilding, ×0.5 when contending. Injuries: −75% if >75 games out, else −gamesRemaining%. **Negative-value players are divided by 20**, so a dump needs a real sweetener. Just-drafted players floor at 0.
2. **Star premium**: each asset above 1 is raised to the **7th power** before summing (basketball), so two decent players never equal one star — the classic "AI gives away stars" fix. Accept iff Δvalue > 0; rejection text tiers at −2 and −5.
3. **Picks**: estimated slot from projected team strength (roster overall → est. win%, blended with the record as the season proceeds), regressed toward the middle over up to five years, pessimistically for the user's own picks (regression target 25% vs 75% of the round) and with a difficulty factor; value read from the prospect pool for that draft; giving up more than two firsts inflates each by (1 + n/5). Real-world anchors: Pelton's chart (1st 4000, 2nd 3250, 3rd 2890, 8th 2200, 9th 2120, 10th 2030; pick 1 ≈ 5× pick 30, pick 15 ≈ 2.5× pick 30) built from net WARP over the rookie deal [S29]; a No. 1 pick averages ~20 WARP over four rookie seasons, 2.0 → 6.9 by year four [S30]; protections cluster at 5/10/14 and lower a pick's value; swaps are options [S31,S32].
4. **Guardrails**: untradable for 14 games after signing (0.17 × games), expired contracts untradable between playoffs and free agency, deadline at 60% of the season; "untouchable" flags; a 5% AI fudge factor plus 10% per difficulty level; the finder uses forward selection to add the single asset that moves Δvalue just above zero, deterministically.
5. **Posture**: `0.8·Δwins + (wins − 41) + 5·(26 − minutes-weighted age) + 20·(young stars about to get paid)`; > 20 contending, < −20 rebuilding, else keep [S11].

**Era rules to encode (`cba.py`).** Over-cap matching: today 125% + $100,000 [S17]; the 1999 agreement is cited in secondary summaries as 115% + $100,000 — **verify in Art. VII §6(j) of the CBA PDF the cap sheet already cites** before use. BYC [S18]; trade bonus ≤15% [S17]; sign-and-trade ≥3 years [S16]; newly signed free agents untradable until Dec 15 / 3 months (current rule; **verify** for 1999) [S24]; Bird rights travel with the player [S33]; 15-man roster; February deadline date for 2003-04 (**verify**).

**Rule-based acceptance for a real club.** (i) Legality for both sides. (ii) Posture of the real club from on-date evidence only (2002-03 record, age of its minutes, cap ledger). (iii) Δvalue computed with the exponent-7 sum, values from `nba_2003_veteran_ratings` + age curve, contracts from `nba_2003_contracts.json`, picks from a 1999-era chart file. (iv) Acceptance draw `p = sigmoid(Δvalue/s)`, floored at 0.02 and capped at 0.9, so lopsided offers never pass and close ones are journaled. (v) Fit: minutes available at the arriving player's position (the roster/rotation data already powers rule 3). Incoming proposals to Miami: rule-generated and rare (a real club over the tax line dumping salary; a contender seeking a specific position before the deadline), with arrival itself a draw. Completed trades update `holdings.json`, `contract_schedules.json`, the roster and the open roadmap-8 record of players Miami sends to real clubs.

**Pitfalls.** Salary dumps for free (negative/20 + pick sweetener priced by the chart); user farming the pick estimator (pessimistic regression on the user's picks); infinite proposal spam (hash + date caching, counter-proposal budget per window); the AI valuing by hindsight trajectories (forbidden; read only `veteran_ratings`); trading a just-signed Bird player to dodge BYC; ignoring that a real club's later real trades may now conflict (rules 1-3 already resolve this).

---

## 4. Offseason and training camp ("a little more robust")

**What the games do.** ZenGM develops every player once at the preseason phase with a coaching-budget effect; shooting and basketball IQ keep improving into the late 20s/early 30s while speed and jumping decline from 26-27, endurance improves randomly to 23; AI clubs then auto-sign free agents to fill rosters and drop the lowest-value players to reach the limit [S34,S35]. FM front-loads camp with promises/playing-time pathways and club vision [S14,S15]. Real NBA: camps run up to 20 players on non-guaranteed deals paid a per diem, cut to the regular-season limit before opening night; most spots are settled long before camp [S36]. For 2003-04 the repo's `era.py` already fixes 12 actives, 15 maximum and an injured list.

**Proposed camp loop (all evidence-based, draws journaled).**
1. **Camp roster**: Miami invites up to 20 from the on-date pool of unsigned players (non-guaranteed minimums, written as `04_Training_Camp/camp_roster.json`).
2. **Position battles**: preseason games are played by the engine from `nba_2003_04_preseason_schedule.json`; the coaching staff's depth-chart decision reads those box scores plus a journaled "camp evaluation" draw per battle, then writes the depth chart, the explicit 240-minute rotation the engine already expects, and Wade's perimeter-defense grade (roadmap item 9).
3. **Cut-down and guarantees**: rule-based cuts to 15 by the lowest value/fit; non-guaranteed money and guarantee dates tracked on the cap sheet; injured-list placements as a labeled status.
4. **Promise check-in**: compare promised vs projected role before opening night; a broken promise is logged for Wade's later decisions only.
5. **Development**: nothing new is needed for ability — the journaled per-season swing (`trajectories.py`) and Wade's age step (`protagonist.py`) already cover the offseason. An optional user "offseason focus" could only re-allocate a drawn swing across rate groups, never change its size or sign; this needs an explicit user policy decision because `AGENTS.md` forbids tuning Wade's path.
6. **Conditioning/injury at camp**: one camp injury draw per player using the existing injury model, so 82 healthy camps are not the norm.

**Pitfalls.** Camp as a free re-roll of ratings (no: evaluation draws only order close battles); using summer-league results (excluded by the roadmap); importing real 2003 preseason rosters for Miami.

**Repo extension.** `runtime/camp.py` (invites, battles, cut-down), `scripts/run_training_camp.py` writing the phase note, `depth_chart.json` and decisions; roadmap items 6, 9, 16 updated in the same change.

---

## Sources

- S1 Basketball GM manual, Player Mood: https://basketball-gm.com/manual/player-mood/
- S2 ZenGM blog, redesigned player mood (2020): https://zengm.com/blog/2020/09/player-mood/
- S3 ZenGM source, market demand normalization: https://github.com/zengm-games/zengm/blob/master/src/worker/core/freeAgents/normalizeContractDemands.ts
- S4 ZenGM source, mood components and willingness: https://github.com/zengm-games/zengm/blob/master/src/worker/core/player/moodComponents.ts and https://github.com/zengm-games/zengm/blob/master/src/worker/core/player/moodInfo.ts
- S5 ZenGM source, daily demand decay: https://github.com/zengm-games/zengm/blob/master/src/worker/core/freeAgents/decreaseDemands.ts
- S6 ZenGM blog, cap on superstar fickleness: https://zengm.com/blog/2024/06/superstar-fickleness/
- S7 ZenGM blog, trades after free agency no longer affect mood: https://zengm.com/blog/2026/04/trades-free-agent-mood/
- S8 ZenGM source, trade valuation: https://github.com/zengm-games/zengm/blob/master/src/worker/core/team/ValueChangeCalculator.ts
- S9 ZenGM source, trade finder and acceptance: https://github.com/zengm-games/zengm/blob/master/src/worker/core/trade/makeItWork.ts and .../trade/propose.ts, .../trade/isUntradable.ts, .../player/sign.ts
- S10 ZenGM blog, trade-finding algorithm: https://zengm.com/blog/2021/05/trade-finding-algorithm/
- S11 ZenGM source, contending/rebuilding: https://github.com/zengm-games/zengm/blob/master/src/worker/core/team/updateStrategies.ts
- S12 OOTP wiki, building a contract offer: https://wiki.ootpdevelopments.com/index.php?oldid=896
- S13 Baseball Mogul help, Negotiate (patience/personality rules): https://files.sportsmogul.com/help/Negotiate.htm
- S14 FM24 contract negotiations (promises, playing time, agents): https://afkgaming.com/gaming/general/how-contract-negotiations-work-in-football-manager-2024
- S15 FM2020 Club Vision and Playing Time Pathway: https://www.si.com/soccer/2019/09/19/football-manager-2020-new-features-unveiled-focus-player-development-club-identity ; broken promises: https://www.fmscout.com/q-18875-A-Promise-I-Couldnt-Keep.html
- S16 Sign-and-trade rules and rationale: https://en.wikipedia.org/wiki/Sign-and-trade_deal
- S17 Trade matching 125% + $100k and trade kickers ≤15%: https://hoopsrumors.com/2018/02/hoops-rumors-glossary-traded-player-exception.html ; https://www.hoopsrumors.com/2018/12/page/7
- S18 Base year compensation: https://hoopsrumors.com/2019/05/hoops-rumors-glossary-base-year-compensation.html
- S19 Arenas 2003 offer sheet / provision: https://hoopsrumors.com/2013/05/gilbert-arenas-provision.html
- S20 2003 cap announcement and first signings: https://www.espn.com/nba/news/2003/0716/1581622.html ; https://www.espn.com/nba/s/2003/freeagents/scoreboard.html
- S21 Why teams place less premium on cap space: https://www.cbssports.com/nba/news/why-teams-are-placing-less-of-a-premium-on-cap-space-and-what-it-could-mean-for-team-building-moving-forward/ ; https://spotrac.com/news/_/id/2428/not-all-cap-space-is-created-equal
- S22 Agent leverage: https://sportsagentblog.com/?p=7127 ; ESPN, players and teams use maximum leverage: https://www.espn.com/nba/story/_/id/27162365/players-teams-use-maximum-leverage-deals-summer
- S23 Comparables/analytics in agent negotiation: https://basketball.scouting4u.com/basketball-contract-negotiation-analytics
- S24 Dec 15 / three-month trade restriction: https://hoopsrumors.com/2024/09/free-agents-signed-after-sunday-wont-become-trade-eligible-on-december-15.html
- S25 Pelton net value with RPM aging curve: https://www.espn.com/nba/story/_/id/13092021/why-timberwolves-take-karl-anthony-towns
- S26 Dollars per win: https://www.espn.com/nba/story/_/id/13303463/money-free-agent-spending-spree ; https://www.brewhoop.com/2019/8/17/20801579/value-in-the-nba-dollars-minutes-wins-2019-2020-updates-milwaukee-bucks-contracts-cba
- S27 Aging curves (peak 26-27): https://apbr.org/metrics/viewtopic.php?p=238 ; https://harvardsportsanalysis.org/2015/05/player-progression-in-the-nba/
- S28 Aging decline after 30: https://courses.cs.washington.edu/courses/cse163/20su/files/project/archive/nba.pdf
- S29 Pelton draft value chart: https://fivethirtyeight.com/features/the-76ers-can-tank-all-they-want-but-they-still-need-lottery-luck
- S30 WARP over rookie contracts by pick: https://www.espn.com/nba/draft2012/story/_/id/8112120/nba-draft-2012-draft-picks-worth-four-year-rookie-contracts
- S31 Valuing pick protections (Sloan): https://www.sloansportsconference.com/research-papers/analytics-for-the-front-office-valuing-protections-on-nba-draft-picks
- S32 Pick protections and swaps: https://theringer.com/2021/03/17/nba/nba-trade-deadline-first-pick-protection ; https://theringer.com/2022/10/12/nba/nba-draft-swap-picks
- S33 Bird rights, holds, 2005 Arenas rule: https://en.wikipedia.org/wiki/Bird_rights
- S34 ZenGM development curve: https://github.com/zengm-games/zengm/blob/master/src/worker/core/player/developSeason.basketball.ts
- S35 ZenGM preseason phase, auto-sign and roster cuts: https://github.com/zengm-games/zengm/blob/master/src/worker/core/phase/newPhasePreseason.ts ; .../team/checkRosterSizes.ts ; .../freeAgents/autoSign.ts
- S36 NBA camp rosters and non-guaranteed deals: https://hoopsrumors.com/2023/08/hoops-rumors-glossary-nba-roster-limits-2.html ; https://hoopsrumors.com/2014/11/invitees-remain-rosters.html
- Background on front-office culture (not a mechanic source): E. S. Strauss, *The Victory Machine* — https://www.hachettebookgroup.com/titles/ethan-sherwood-strauss/the-victory-machine/9781549118449/ ; Coon FAQ history: https://www.blazersedge.com/2025/6/21/24453051/larry-coon-cba-salary-cap-retirement-faq-site-history
