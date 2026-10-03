# Front office design: free agency, contracts, trades and the offseason

What Miami's simulated front office does from June 30, 2003 onward, how a free agent or a real club answers it, where chance enters, and what the user does as Wade. It builds on the contract desk already in the repository (`runtime/contract_negotiation.py`, the four-offer board with the reserved fifth matching slot, the milestone templates) and on the research recorded in `docs/research/` and `library/2003/league/nba_2003_offseason_market_research.md`. Rules come from the 1999 agreement as recorded in `library/2003/league/nba_1999_cba_rules.json`; everything marked *judgement* is a constant chosen for this simulation, not a sourced rule, and lives in code with its name so it can be revisited.

## 1. Principles

1. **Authority.** The user decides Wade's own choices: his contract answers, his requests to the front office, his consent where a right exists. The AI/GM decides every club action: whom to pursue, what to offer, when to walk away, what to trade. A real club has no front office; its answers are rule-based.
2. **No hindsight for the front office.** Every valuation, need, budget and bid uses evidence dated on or before the career date: 2002-03 statistics, the June 26 contract inventory, published cap figures, signings already announced. Real later signings, real rosters and real-career trajectories never enter a Miami decision. They enter the world only through two doors: a free agent's real alternative decides how hard he is to sign (section 4.4), and a player Miami fails to sign leaves the market on his real date (section 3).
3. **Chance is journaled.** Rules decide clear cases; chance decides close ones. Every chance outcome is a `*.decision.json` drawn by the Railway engine (`runtime/decisions.py`), keyed by date and content, so the same offer on the same date always gets the same answer and nothing can be re-rolled.
4. **One ledger of offers.** Every offer, counter, revision, withdrawal, sheet and match is a version in the contract desk's state machine, whether the player is Wade or a free agent Miami is chasing. Templates show it; the state machine records it; a separate adapter writes signed contracts into the canonical records exactly once.
5. **Promises are tracked.** A role or minutes statement Miami attaches to an offer is recorded with a date and checked against closed games. A broken promise never changes the engine; it changes only Wade's later decisions, through his own choices (AGENTS.md, Wade's voice).

## 2. The 2003 calendar

| Date | Event | Source |
|---|---|---|
| June 30 | Option, qualifying-offer and tender deadline; Miami's decisions already built (`scripts/run_june30.py`) | FAQ Q34 |
| July 1 to 15 | Moratorium: clubs and free agents may talk and agree verbally; nothing can be signed | ESPN, July 15, 2003 ("eve of the expiration of a moratorium") |
| July 15, evening | 2003-04 cap published: $43,840,000; mid-level $4,917,000; $1.5M exception; minimum team salary $32,880,000 | ESPN, July 15, 2003; `league_cap_history.json` |
| July 16 | First signings (Mourning, Howard, Malone, Payton, Duncan, Kidd, the Brand, Miller and Maggette offer sheets) | Basketball-Reference 2003-04 transactions |
| July to September | The market thins; by September most remaining free agents sign one-year or minimum deals | ESPN scoreboard, August 25, 2003 |
| About September 30 | Training camp opens (date to verify from a period source); up to 20 under contract | 1999 rules, roster limits |
| October 5 to 24 | Preseason, 7 Miami games, already in `nba_2003_04_preseason_schedule.json` | schedule file |
| By opening night, October 28 | Roster cut to 15 (12 active, up to 3 on the injured list) | `runtime/era.py` |
| February 19, 2004, 3 p.m. ET | Trade deadline | Basketball-Reference, February 19, 2004 trades |
| October 31, 2005 | Deadline for Miami's fourth-year option on Wade: October 31 after his second season | FAQ Q38 (corrects the earlier October 31, 2004) |

The luxury tax line for 2003-04 was not knowable in July 2003: the union projected about $57 million; the actual $54.56 million was computed after the season. The front office plans against the projection; the actual is applied only when the 2004 computation date is reached.

## 3. The market

**Pool.** The 129 players whose contracts ended June 30 (`library/2003/league/nba_2003_free_agent_rights.json`, with rights, holds and qualifying-offer arithmetic), plus Miami's own expiring players and anyone a club waives later. Draft picks are not free agents.

**Exit dates.** `library/2003/league/nba_2003_offseason_transactions.json` records each real signing, offer sheet, match and trade of the 2003 offseason with its date, terms where reported, and an evidence level. It is world data under option D, like the roster files. A free agent whom Miami has not signed by his real signing date joins his real club on that date and is gone. Signings that involved real Miami are skipped (rule 1): Mourning's July 16 move to New Jersey is a real alternative Miami competes against, but Odom's, Alston's and the others' real moves to Miami do not happen unless simulated Miami makes them.

**What the front office sees on a date.** Past signings as news (anyone could read on July 17 that Mourning had signed); the remaining pool; each player's rights, prior salary and 2002-03 production; its own cap sheet; every club's cap position as the June 26 ledger shows it. It never sees future dates or terms.

## 4. The player's side

### 4.1 Value

Each free agent gets a **production value** from 2002-03 evidence only: a box-score composite of his per-minute rates (`library/2003/league/nba_2003_veteran_ratings.json`) times his 2002-03 minutes, with an age adjustment from a generic curve (peak 26 to 28, decline from 30, steep after 33; *judgement*, from the aging studies in the research). Rookies and overseas players use the draft-night estimate or none.

### 4.2 Price

A player's **asking price** is what his agent argues from comparables, so it is fitted on the June 26 contract inventory, never on 2003 results: first-year salary of contracts signed 2000 to 2002 against the signer's production at signing gives a price per unit of value, bounded below by the minimum and above by the maximum for his years of service. On top of that:

- a **market-pressure multiplier** from how many clubs had room on the date against how many players of his tier are available (room is counted from the June 26 ledger and the published cap; *judgement*: between 0.8 and 1.3);
- a **mood multiplier** of 1.0 to 1.5 when the player is unhappy with his situation (Basketball GM's rule; *judgement*);
- **years** he wants: younger players ask for more years, older ones trade years for money (OOTP's rule).

The ask decays while he stays unsigned (Basketball GM lowers it daily; here it drops about 5% a week from July 16, floored at the minimum; *judgement*) and rises after an insulting offer (an offer under 70% of the ask ends talks for a week; *judgement*).

### 4.3 Priorities

At market entry each player draws, once, a **trait** (fame, loyalty, money, winning) and a priority vector over guaranteed money, years, role, winning and location, from his age and prior salary (a 33-year-old on a big contract weights winning and money; a 25-year-old weights years and role). The draw is a journaled decision so it cannot be chosen.

### 4.4 Answering an offer

For each live Miami offer the player compares two utilities: Miami's offer, and his **best alternative**, which is his real contract on his real date when the market file has it, otherwise the tier price for a player of his value (section 4.2). Utility is the priority-weighted sum of log guaranteed money, years, projected role at the club (minutes available at his position from the depth chart or the real rotation), the club's projected strength from on-date evidence (last season's record and the current roster), and location. The chance he accepts is a logistic function of the difference (`p = 1 / (1 + exp(-k * (U_miami - U_alt)))`, with `k` *judgement*, and `p` kept inside 0.02 to 0.95 so a weak offer never lands a star and a strong one is never certain). Three answers are possible: accept, counter with a stated ask, or reject. Patience: three rounds per club per window (*judgement*).

### 4.4a The answer model (`runtime/player_utility.py`, `utility-2003.2`)

From July 3, 2003 every answer packet uses the factor model below. It adapts a twelve-factor negotiation framework the user supplied (assessed in section 4.4b). Drawn answers made under the earlier five-weight utility stay as drawn.

- **Factors, each scored 0 to 100 for Miami's offer and for his best alternative.** Money (guaranteed salary against his ask for the seasons he wants), security (seasons offered against seasons wanted), net income (state or provincial income-tax tier: none in Florida, Texas, Washington and Tennessee; highest in California, New York City and Ontario), role, contention, loyalty (the club he played for in 2002-03) and market (media-market tier). Tiers are *judgement*.
- **Rosters decide role and contention** (`runtime/club_strength.py`), at the user's request. Every club's roster is rebuilt on the date: real clubs from the end-of-2002-03 rosters plus the real moves dated on or before it, under the conflict rules; Miami from its ledger. Contention is that club's projected wins *with him on it*, from a straight line fitted on the 2002-03 rosters against the 2002-03 standings. Role elsewhere is his value rank inside his position group on that roster. Miami's role is its own depth-chart promise. A signing therefore changes what the next free agent sees: a club that has just added a guard offers the next guard less, and a stronger roster draws veterans.
- **Weights** come from his career stage (24 or younger, 25 to 29, 30 or older) and are tilted by his drawn trait. Contention carries more than in the supplied table at the early and prime stages, because the user asked that the rosters weigh heavily.
- **Not scored.** These have no dated evidence: scheme fit (Miami's staff has set no scheme), organisation, coach and locker-room ties, medical staff, and family. They are named on every packet and never guessed for a real person. Era rules are not a preference; the contract desk refuses an illegal offer first.
- **Answer odds.** The utility gap (Miami minus alternative, in points) goes through an ordered logistic. Accept is centred 4 points above the alternative and reject 10 points below it, with a scale of 4. Counter takes the band between. Accept is kept inside 2% to 95%. There is no counter in the last round he hears. An offer under 70% of the ask is near-certain rejection. The engine draws the answer.
- **Counter.** The agent pushes on the factor where Miami loses most weighted ground. Money and years are fixed by the money counter and the next offer's length. A weakness money cannot fix, such as a weaker club or a smaller role, adds up to 15% to the counter (`runtime/negotiation.counter_amount`).
- **Dealbreaker.** A starter in his prime offered a bench role walks without a draw. That means at least 30 minutes and 75% starts in 2002-03, aged 25 to 31, offered under 20 minutes.

### 4.4b The supplied framework, assessed

These parts were adopted:

- The factor-weighted utility.
- Career-stage weights.
- Counters aimed at the weakest factor.
- The role-disrespect dealbreaker.

These parts were changed:

- **Fixed thresholds become a draw.** The framework's fixed thresholds (accept at 72 or more, counter from 45 to 72, walk under 45) are deterministic and absolute. Here they become a draw on the gap to his real alternative, because a player measures an offer against what else he can get.
- **The California rate is corrected.** The framework's 13.3% California rate is the 2012 rate. In 2003 the top rate was lower, so tiers are used, not rates.
- **Era rules move out of the utility.** The framework's factor 12, era rules, is a legal constraint, not a preference.

These parts were not adopted:

- **The coach as the user.** The framework makes the user the coach. Here the user is Wade, and the coach is part of the AI front office.
- **Invented personal details.** Psychometric profiles, family preferences and friendships for real players would be invented facts.
- **Post-signing effects.** Morale, chemistry and coach-versus-star power have no engine hooks yet.

A free agent Miami pursues before his real date can still be lost on that date: if no agreement exists, he signs his real contract. An agreement in the moratorium becomes a signing on July 16 or later.

### 4.5 Restricted free agents

Miami's own: the qualifying offer, matching rights and holds are already recorded; an outside sheet is a real event only when the market file has one (none involve Miami's players in 2003). Other clubs' restricted players (Brand, Miller, Odom, Maggette, Arenas, Hamilton, Thomas, Posey, Terry): Miami may sign them to an offer sheet of at least three seasons; the incumbent matches by rule, drawn when close: it matches when the sheet's surplus value is at or above zero and its payroll after matching stays under its tax tolerance (*judgement*; the Clippers' real matching of Brand and Maggette and declining of Miller is the evidence that money, not loyalty, decides). The 15-day window, the fifth-slot record and the frozen terms are the contract desk's existing flow.

## 5. Miami's front office

### 5.1 Ledger

The cap sheet (`00_Team/Finances/finance.json`, `contract_schedules.json`, `free_agent_rights.json`) gains an **exceptions ledger**: the mid-level ($4,917,000 to start, up to six seasons, 10% raises, splittable), the $1.5M exception (every other season), the minimum exception, Bird, Early Bird and Non-Bird rights by player, and the rookie-scale hold for Wade. Cap room is cap minus committed salary minus holds for unrenounced free agents minus the roster charge for empty spots. Renouncing a free agent removes his hold and his Bird rights until the next June 30 (FAQ Q31).

### 5.2 Budget

`team_config.json` gains the owner's **payroll ceiling** for the season and a **tax tolerance** (whether the club will pay the dollar-for-dollar tax at all). For 2003, Miami's evidence is a club cutting payroll with about $7 million of room before June 30 (*judgement*: ceiling at the projected tax line, no tax).

### 5.2a Standing roster and payroll rules

These rules run without anyone's input, and validation checks them every time it runs.

- **Later seasons.** Every offer's later seasons must fit under the owner's payroll ceiling, together with what Miami has already committed for that season (`FrontOffice.future_fit`). Later caps are not known on the date, so the ceiling is the yardstick, not a guessed cap. If only a shorter deal fits, the offer shrinks to it. If no legal length fits, Miami walks away; a sign-and-trade and an offer sheet need three seasons.
- **Who may dress.** Only players Miami holds under a signed contract may dress (`camp.playable`). Unsigned draft rights, released, traded and departed players are out. A rotation player who is no longer playable is replaced by the next playable man on the depth chart.
- **The cut.** The cut to fifteen counts signed players only. It releases camp invites before guaranteed players and the staff's rotation last.
- **Validation.** Validation fails if a scheduled Miami game dresses a player who is not playable, or if Miami carries more than fifteen signed players after the cut.
- **No routine renouncing.** Holds are renounced only when they buy room for a target. Over the cap, a hold costs nothing and keeps Bird rights, so the front office does not renounce routinely.

### 5.2b Availability, voided signings and the roster refill

- **Truly available.** A player is available to Miami on a date only if three things hold: he is a free agent in the world data, he has no real move dated on or before it, and he is not restricted. A real move with no dated source counts from the day camps open, as an inference, and is labelled on the row.
- **Restricted free agents.** A restricted free agent can only be signed through an offer sheet his club may match (`Market.restricted`). Camp invites and refills skip restricted players.
- **Voided signings.** A signing that broke one of these conditions is voided (`scripts/correct_camp_signings.py`). The player leaves Miami's books and is back with his real club. Played games keep their inputs.
- **Refill.** Open spots are filled at the minimum, non-guaranteed until January 10, 2004 (`runtime/refill.py`).
  - Candidates are unrestricted free agents available on the date, plus unattached players. An unattached player has no previous NBA club and his only real 2003 club was Miami, so rule 1 leaves him unsigned.
  - The rule ranks candidates by 2002-03 production value times positional fit. A player with no NBA line counts at replacement level.
  - Equal scores are broken by Wade's requests, because the front office is indifferent between those players.
  - A request for a candidate the rule does not pick is drawn at standing weight times one minus the margin.
  - Each player's answer is an engine draw.

### 5.3 Needs

From the depth chart: minutes available by position after the players under contract, the quality of the incumbent at each position (2002-03 production value), and the coach's stated structure (Spoelstra's preferences are unassessed until camp, so the first season uses a neutral structure). Need at a position = minutes short of a full rotation plus a gap term where the incumbent is below league average.

### 5.4 Plan and targets

The front office decides first how to use its room (chase one large contract, or two mid-sized, or hold it), then ranks targets by **surplus value** (production value priced at the comparables rate minus the ask) times fit (need at his position). Wade's requests move a target up the list by his standing weight (unsigned rookie 0.15; `docs/front_office.md`); when a request puts a decision inside the rule's margin, the engine draws it. Wade's standing is computed from closed simulated results and recorded honors on the date (`runtime/standing.py`: signed, closed seasons, the starter line, All-Star and All-NBA honors, MVP), dated in `career/Dwyane_Wade/standing.json` and replayed by validation; never typed and never the historical Wade. Once it is `franchise`, the front office must consult him before it adds another star (a 2002-03 production value of 20 or more) by any route, and his objection stops that move for the season (the user's premise; `docs/front_office.md`, Franchise consultation). A target the room and the exceptions cannot reach, whose incumbent holds his full Bird rights, may be planned on the sign-and-trade route when a two-sided feasibility probe passes (7.1). The plan is written to the phase note before any offer, so the user can read why Miami did what it did.

### 5.5 Bidding policy

Open at 85 to 90% of the ask when it is inside Miami's valuation, concede years first, then guarantees, then dollars, never past the valuation; walk away after three rounds or when the player's counter exceeds the valuation by 10%; one live offer per player; no offer during the moratorium can be signed before July 16, so moratorium offers are agreements in principle. All *judgement*, named in code.

### 5.6 Write-back

A signing reaches the canonical records once, through one adapter: the contract on `contract_schedules.json`, the holding on `holdings.json` (rule 2), the register and a player card, the cap sheet, the depth chart as an unassigned arrival, the phase note, and `current_state.json`. The free-agent rights file marks renouncements. A failed write leaves everything untouched.

## 6. Wade's own negotiations

**Now: the rookie scale.** Under the 1999 scale there is little to bargain: 80 to 120% of scale, three seasons and a team option, 20% signing bonus at most. Miami opens at 120% after its July moves (built). What Wade can do: accept, ask for the full 120% and a signing date, ask for a signing bonus within the limit, attach a role request, or hold out (he counts at 100% of scale, cannot play, and the front office's view of him worsens). Miami's answers are rules (`runtime/front_office.rookie_offer`) with a draw where a request is close.

**Promises.** Miami may state a role ("secondary creator in the rotation") with a date and a speaker. At season end the reporter compares it with closed minutes and starts. A broken promise lowers Wade's loyalty term in his later decisions and is shown to the user; it never changes the engine.

**Later.** The extension window after his third season (through October 31 of the fourth), restricted free agency after the fourth with the qualifying offer and the 15-day match flow, and unrestricted free agency after that, all run on the same desk, with the user as the player and the AI/GM producing Miami's offers by the policy above and other clubs' offers by the market model with their real cap positions.

## 7. Trades

### 7.1 Legality (`runtime/cba.py`)

Matching for a club over the cap after the trade: incoming salary at most 115% of outgoing plus $100,000 (1999 figure, reported by Cuban in 2004; the 2005 agreement moved it to 125%); outgoing salaries may be aggregated. Base-year compensation: a player re-signed with Bird or Early Bird rights at a raise over 20% counts, for matching, at the greater of half his new salary and his old salary through the first season. A newly signed free agent cannot be traded for three months or until December 15, whichever is later; a signed first-round pick for 30 days. Cash up to $3 million a season. The Stepien rule: never without a first-round pick in consecutive future drafts. Roster of 15 after the trade. Trade bonus up to 15% of remaining salary. Items the research could only infer for 1999 are marked in `nba_1999_cba_rules.json` as inferred, and the module reports which rule it used.

Sign-and-trade (`trades.sign_and_trade` in the rules file): the incumbent signs its own free agent with full Bird rights and trades the contract in the same transaction; the contract runs at least three non-option seasons (Article VII section 8(e) via the research locator), needs no first-season guarantee under the 1999 rules (a 2005 addition; inferred), carries base-year compensation when the signing attaches it (computed once from the signing club's cap position after the signing and stored on the contract entry, never re-derived in a later trade), is signed inside the trade itself (sourced from the Miller example, signed and traded the same day), so the newly-signed restriction, which starts at a signing, cannot bar it and never extends to a trade on a later day (inferred), and cannot be signed during the moratorium, which the model also treats as a trade ban (July 1-15; inferred from the 2003 log). A club at or under the cap after the trade absorbs incoming salary into room (inferred). Matching therefore works on four totals: each side's outgoing salary at full value and at matching value (base-year reductions only in the matching value), and each club's post-trade payroll, which never counts a sign-and-trade player on the side that signed him because his salary was never on that payroll. Both directions are modeled: Miami acquiring a real club's full-Bird free agent, and Miami signing its own agreed full-Bird free agent and trading him to a real club in the same transaction (he is unsigned until the trade executes; a player Miami has already re-signed is an ordinary signed player whom the newly-signed restriction binds, whatever label the proposal carries); restricted free agents are not.

### 7.2 Value

Each asset has a value: a player's production value with an age curve, plus a contract term (what his production would cost at the comparables price minus his salary, over the years left, capped), with injuries subtracting their remaining games; an expiring contract counts at a small positive value for a taxpayer; a draft pick's value comes from a 1999-era chart (first pick about five times the thirtieth, the fifteenth about two and a half times; from Pelton's chart) placed by the owning club's projected finish from on-date evidence and regressed toward the middle over future years, pessimistically for Miami's own picks. A player with negative value counts at a twentieth of it, so a salary dump needs a real sweetener. Before summing, every asset above 1 is raised to the seventh power (Basketball GM's star premium), so two good players never equal one star.

### 7.3 Posture of a real club

From on-date evidence only: last season's record, the age of its minutes, its cap and tax position, young players about to be paid. Contending clubs discount picks and weight the present; rebuilding clubs the reverse (Basketball GM's strategy multipliers, *judgement* values in code).

### 7.4 Acceptance

A real club accepts when the trade is legal for both sides, fits (minutes exist at the arriving positions in its real rotation) and raises its summed value; the acceptance chance is a logistic function of the value change, floored at 0.02 and capped at 0.9, drawn by the engine. The same proposal on the same date gives the same answer. A sign-and-trade adds the contract to the packet: for an acquisition the incumbent counts the player it signs only to trade at `SIGN_AND_TRADE_RIGHTS_SHARE` (0.5) of his value, because it would otherwise lose him for nothing, and its acceptance is the one packet; for an own sign-and-trade-out there are two packets, the player's consent (his agreed terms at the partner, judged by the market's answer rule with the partner's depth at his position, its record and `PARTNER_LOCATION`, against the same terms at Miami) and the partner's acceptance at the player's full value; both accepting signs and trades him in one commit, and a decline on either leaves the agreement standing, so Miami re-signs him on the agreed terms. Every packet is engine-drawn, never rolled locally. Miami may receive proposals: rare, rule-generated (a taxpayer dumping salary into Miami's room; a contender after one position before the deadline), their arrival itself a draw.

### 7.5 After a trade

Players Miami sends to a real club enter that club's rotation through the arrivals ledger (`runtime/rotations.py`, conflict rule 3; the open part of roadmap item 8), dated. Players Miami receives enter `holdings.json`, the register, the cap sheet and the depth chart; a player Miami sent away is excluded from every other real club's roster on the dates his departures entry is active. Wade is told through the trade-update template. Below `franchise` standing his page is a notice and a role meeting, and his objection is logged for his later decisions; at `franchise` standing the front office must ask him before it trades for another star, the ask stops the career clock until he answers, and his objection stops the move (the user's premise; `docs/front_office.md`, Franchise consultation).

## 8. Offseason and training camp

- **Summer League:** a record container only; no games are played (roadmap).
- **Development:** nothing new. The engine's per-season swing and Wade's age step already cover the summer; an "offseason focus" that re-allocates a drawn swing would be a user policy change under AGENTS.md and is not built.
- **Camp roster:** Miami invites up to 20 from the unsigned pool on non-guaranteed minimums (`04_Training_Camp/camp_roster.json`); each invitee gets one camp injury draw with the existing injury model.
- **Preseason:** the seven games are played by the engine from the preseason schedule with Miami's camp rotation; results are evidence, not statistics that count.
- **Position battles and the depth chart:** the staff's decision reads preseason box scores and one journaled evaluation draw per close battle, then writes the depth chart, Miami's 240-minute rotation for the game builder, and Wade's perimeter-defense grade (roadmap item 9), mapped onto the engine's defensive value.
- **Cut-down:** to 15 by lowest value and fit, with non-guaranteed money and guarantee dates on the cap sheet; injured-list placements labeled.
- **Promise check:** promised roles against the written rotation before opening night.

## 9. Corrections the research found

1. Wade's fourth-year option deadline is October 31, 2005, not 2004 (`runtime/rookie_contract.py`, `docs/front_office.md`).
2. The 2003-04 tax line in `nba_2003_04_cap_rules.json` is the after-season actual; the live front office uses the July 2003 projection (about $57 million) until the computation date.
3. The 1999 rules file's rookie-scale "raise_percent 10" is not a negotiable raise: the scale fixes years two and three at 107.5% and 115% of year one.
4. The 105% maximum rule and mid-level-equals-average are confirmed by the July 15, 2003 cap announcement and are moved out of the unverified list.
5. The calendar above (moratorium, first signing day, trade deadline) was recorded nowhere; it now lives in `library/2003/league/nba_2003_04_calendar.json`.

## 10. Build order

| Phase | Builds | Done when |
|---|---|---|
| A | This design, the research files, the corrections, the calendar file, the dated 2003 transactions world file | validation and tests pass; the roadmap points here |
| B | Valuation and asking prices, priorities, acceptance draws; Miami's ledger, budget, needs, plan and bidding; the negotiation adapter on the contract desk; write-back; Wade's rookie negotiation with promises; June 30 run | Miami's July is played through the clock, every decision written to the phase note with its reasons, every draw on Railway |
| C | Trades: legality, value, posture, acceptance, arrivals, deadline; Wade's trade page | a proposed trade is answered by rule and draw and written back |
| D | Camp: invites, injuries, preseason games, battles, depth chart, Wade's defense grade, cut-down | Miami's opening-night roster and rotation exist for the game builder |

## Sources

Research reports with their evidence levels: `docs/research/cba_1999_rules.md`, `docs/research/sim_design_brief.md`, `library/2003/league/nba_2003_offseason_market_research.md`. Primary: Larry Coon's 1999 Salary Cap FAQ (extract in `library/2003/league/`), the 1999 NBA/NBPA agreement (UNH Law archive), ESPN's July 15, 2003 cap announcement, Basketball-Reference's 2003-04 transactions, Basketball GM's source (ZenGM, GitHub), Kevin Pelton's draft value chart (FiveThirtyEight). The user's own contract-desk research: `docs/templates/player_milestones/contract_negotiation_research.md`.
