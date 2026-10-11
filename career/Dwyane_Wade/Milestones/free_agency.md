<!-- Generated live career view; edit canonical event records and rebuild. -->

# Free agency | Dwyane Wade

Career date: 2006-06-11 · Miami Heat · needs evidence

[Live milestone desk](index.html#free_agency) · [All milestones](README.md)

Player eligibility requires actual contract, option and qualifying-offer records; team recruitment is separate.

Activation: A verified player market window or actual dated Miami roster-market event.

## Your market position

| Item | Current evidence |
| --- | --- |
| Control | rookie_scale_contract |
| UFA / RFA | Not established by a calendar date alone |
| Qualifying offer | Requires actual tender and rights evidence |
| Outside written offers | None established by the current player control record |
| Market value | No verified estimate supplied to this live view |

## Your team-direction requests

| Date | Subject | Target | Request | Explanation | Source |
| --- | --- | --- | --- | --- | --- |
| 2005-10-31 | extension_terms | Dwyane Wade | propose | Wade's terms for his rookie-scale extension: five additional seasons from 2007-08 (to 2011-12), the first year 20% below his fair market value on Miami's decision day (the front office's own market benchmark for his production within his minimum and maximum, set on 2006-10-31 from the closed 2005-06 season; the user's $12 million figure was an illustration only), the first four seasons fully guaranteed, the fifth a Miami team option, raises up to 10.5% of the first-year salary (cbafaq05 Q52), no no-trade clause. Legal as filed: one option season, the last (Q51), inside the five seasons a rookie-scale extension allows (Q52). Miami decides whether to offer by its own rule on 2006-10-31 (runtime/extensions.py) and adopts each term that is legal and at least as favourable to it as its rule; the offer then waits for the user's own accept or decline. If Miami does not offer, Wade plays out his rookie contract (2006-07 option exercised 2005-10-31). | [Recorded request](../2005-06/04_Training_Camp/wade_requests.json) |
| 2005-10-31 | trade_target | Trevor Ariza | pursue | Wade asks the front office to go after Trevor Ariza (Los Angeles Lakers, SF). On the date Ariza plays 2005-06 on the one-season $816,748 qualifying offer he accepted from the Lakers on 2005-09-30 (career/Dwyane_Wade/2004-05/10_Free_Agency/free_agency_2005.json); he was undrafted in the simulated 2004 draft, signed by Detroit on 2004-07-14 and traded to the Lakers on 2005-01-03. As a newly signed contract he cannot be traded before 2005-12-30 (three months after signing, or December 15 if later; cbafaq05 Q83). Miami's 2005-06 payroll ($67,315,693) is above the $61,700,000 luxury-tax line that is the owner's ceiling, so a trade may not raise it: Miami must send out at least his salary. The request weighs on Miami's in-season trade ranking by Wade's standing (runtime/trades.py); the Lakers decide their answer by engine draw; Miami may decline to pursue him. Not a star under the consultation rule. | [Recorded request](../2005-06/04_Training_Camp/wade_requests.json) |
| 2006-04-19 | keep_picks | Dwyane Wade | keep | Standing request: Miami keeps its draft picks, and if it trades one more, Wade asks for a trade. On the date Miami owns its 2006 second-round pick and its 2007 first- and second-round picks; its 2006 first went to the New Orleans/Oklahoma City Hornets on 2006-01-16 (trade 2006-01-16-7a8ce79392; 00_Team/Finances/draft_picks.json). The request stands from this date, in this and every later season, until Wade withdraws it with a later keep_picks row (runtime/keep_picks.py reads every season folder, so the rollover carries nothing). Miami's front office weighs it wherever it could send a pick away: its in-season packages, Wade's own package requests (one he files later naming a pick is his newer wish for that pick) and draft-night trades; offers from other clubs and the summer market's trades carry no Miami pick, and the sign-and-trade pick fallback runs only in the 2003 summer. A package with a pick is scored as an opposed departure at his standing weight (on draft night, Miami's even-chance answer to a trade-down offer loses that share of its acceptance): at franchise standing (weight 0.8 on the date) a pick package needs five times the front office's threshold, so only a large gain still sends a pick. A request never forces a decision, and the trade request he states is his own decision, not a cost the front office prices in. If Miami trades a pick while it stands, his trade request is written the same day and the career clock stops until the user confirms or withdraws it; what follows a confirmed request is not modelled (docs/ROADMAP.md F1), so a confirmed request keeps the clock stopped until it is. Effective 2006-04-19 (the user's premise, October 2026: "make it a hard rule"): while this request stands, Miami's front office never trades away a draft pick, with no weighing and no engine draw, on every path (in-season packages, Wade's own earlier package requests, offers, the sign-and-trade fallback, draft night); this replaces the weighing by his standing described above, which never decided anything. A package he himself requests on or after this date that names a pick is still his own newer choice, and a pick that left anyway would still write his trade request (runtime/keep_picks.py; docs/front_office.md, Keep the picks). | [Recorded request](../2005-06/04_Training_Camp/wade_requests.json) |
| 2005-10-31 | draft_prospect | Kyle Lowry | evaluate | Scouting recommendation: watch his perimeter defense, playmaking, competitiveness and development as a lead guard. On the date he is a Villanova sophomore; whether he enters the 2006 draft and where he ranks are decided by the simulation's draft-night evidence. Weighed only on Miami's own 2006 picks (runtime/draft.py); never a demand. | [Recorded request](../2005-06/09_Draft/wade_requests.json) |
| 2005-10-31 | draft_prospect | P.J. Tucker | evaluate | Scouting recommendation: watch his physical defense, rebounding, positional versatility and offensive development. On the date he is a Texas junior; whether he enters the 2006 draft and where he ranks are decided by the simulation's draft-night evidence. Weighed only on Miami's own 2006 picks (runtime/draft.py); never a demand. | [Recorded request](../2005-06/09_Draft/wade_requests.json) |
| 2006-04-19 | draft_prospect | P.J. Tucker | draft | Wade asks Miami to draft P.J. Tucker in the 2006 draft, more than the evaluation he asked for on 2005-10-31; this row replaces that one (the latest row per prospect stands; Kyle Lowry's evaluate request is unchanged). Weighed on Miami's own 2006 picks only (on the date it holds only its 2006 second-round pick), never another club's and never in a trade (runtime/draft.py rule 7): available in the best available tier at Miami's pick, he is always a candidate with the evaluate lift and an engine draw first takes him at Wade's request with chance standing weight x closeness (his draw weight against the club favourite's); outside that tier the request opposes tier dominance and is an engine-drawn decision at standing weight x closeness (one less his distance below the tier's line in tier widths; a whole tier below is a clear-cut call that cannot be moved). Never a certainty. Whether he enters the 2006 draft and where he ranks are decided by the simulation's draft-night evidence. | [Recorded request](../2005-06/09_Draft/wade_requests.json) |
| 2005-10-31 | free_agent_target | Trevor Ariza | pursue | The same request for the 2006 summer market, read by runtime/free_agency_2004.py for 2006 (this folder is the 2006 market's): if Ariza is still unsigned after 2005-06 (an unrestricted free agent, having played the season on his qualifying offer), Miami's front office moves him up its list by Wade's standing weight and may pay up to 110% of its valuation; it sets the terms, other clubs bid and Ariza answers by engine draw. Miami's 2006-07 commitments are $63,325,002 on the date, so without room the route is an exception (the mid-level of the 2006-07 rules once published). No term preference stated. | [Recorded request](../2005-06/10_Free_Agency/wade_requests.json) |

## Miami's actual negotiation records

These are Miami's roster negotiations, not offers to Wade.

| Player | Opened | Dated rounds | Known position | Source |
| --- | --- | --- | --- | --- |
| No dated record | N/A | N/A | N/A | N/A |

## Recorded market events

| Date | Event / player discussion |
| --- | --- |
| 2005-10-01 | The 2005 summer market closed on September 30, 2005; its record is `../../2004-05/10_Free_Agency/free_agency_2005.json`, carried into `../00_Team` by the rollover. |
| 2005-10-31 | Kwame Brown released at the cut to 15 (non-guaranteed camp contract; no dead money). |
| 2005-10-31 | Adonal Foyle released at the cut to 15 (non-guaranteed camp contract; no dead money). |
| 2005-10-31 | Theo Ratliff released at the cut to 15 (non-guaranteed camp contract; no dead money). |
| 2005-10-31 | Bonzi Wells released at the cut to 15 (non-guaranteed camp contract; no dead money). |
| 2005-10-31 | Sam Cassell released at the cut to 15 (non-guaranteed camp contract; no dead money). |
| 2005-12-19 | Matt Harpring traded to Milwaukee Bucks (2005-12-19-aaa5cfaab5). |
| 2006-01-16 | Brian Grant traded to New Orleans/Oklahoma City Hornets (2006-01-16-7a8ce79392). |

## Decision authority

| Item | Who decides | Player response |
| --- | --- | --- |
| Targets, offers and roster construction | AI/GM | State a preference and ask for an answer |
| Wade's actual eligible contract offer | Wade | Accept, counter or decline through the actual desk |
| Adding another star at franchise standing | Recorded consultation premise | Answer the actual approve/object question |
| RFA matching | Incumbent under verified rules | A valid offer sheet starts its binding workflow |

## Available response paths

- [Open market events and your requests](../2005-06/01_Free_Agency/note.md): Review the actual dated roster-market discussion.
- [Record your authorized reply](../../../docs/live_player_milestones.md): Use the dated source and current record version; a browser visit does not submit a decision.

## Next checkpoint

Miami's next recorded market action or an actual proposal in Wade's own contract desk.

## Evidence

- [Authoritative career checkpoint](../2005-06/current_state.json)
- [Dated professional identity](../professional_identity.json)
- [Established player profile](../Dwyane_Wade_Player_Profile.md)
- [Owning event](../2005-06/04_Training_Camp/note.md)
- [Current contract and cap-control record](../2005-06/00_Team/Finances/contract_schedules.json)
- [Recorded request](../2005-06/04_Training_Camp/wade_requests.json)
- [Recorded request](../2005-06/09_Draft/wade_requests.json)
- [Recorded request](../2005-06/10_Free_Agency/wade_requests.json)
- [Dated staff rotation review](../2005-06/00_Team/Team/Depth_Chart/Reviews/2006-04-12/review.json)
- [Current dated staff depth chart](../2005-06/00_Team/Team/Depth_Chart/Reviews/2006-04-12/depth_chart.json)
- [Offseason player decisions and events](../2005-06/03_Offseason/note.md)
- [Recorded camp roster](../2005-06/04_Training_Camp/camp_roster.json)
- [Dated staff rotation](../2005-06/00_Team/Team/Depth_Chart/Reviews/2006-04-12/rotation.json)
- [Owning dated record](../2005-06/04_Training_Camp/Wade_Extension_Outlook_2005-10-31.md)
- [Transaction record](../2005-06/00_Team/Transactions/Trades/2005-12-19-aaa5cfaab5.json)
- [Transaction record](../2005-06/00_Team/Transactions/Trades/2006-01-16-7a8ce79392.json)
- [Closed game](../2005-06/05_Preseason/Game_1.md)
- [Closed game](../2005-06/05_Preseason/Game_2.md)
- [Closed game](../2005-06/05_Preseason/Game_3.md)
- [Closed game](../2005-06/05_Preseason/Game_4.md)
- [Closed game](../2005-06/05_Preseason/Game_5.md)
- [Closed game](../2005-06/05_Preseason/Game_6.md)
- [Closed game](../2005-06/05_Preseason/Game_7.md)
- [Closed game](../2005-06/06_Regular_Season/11_November/Week_1/Game_1.md)
- [Closed game](../2005-06/06_Regular_Season/11_November/Week_1/Game_2.md)
- [Closed game](../2005-06/06_Regular_Season/11_November/Week_1/Game_3.md)
- [Closed game](../2005-06/06_Regular_Season/11_November/Week_1/Game_4.md)
- [Closed game](../2005-06/06_Regular_Season/11_November/Week_2/Game_1.md)
- [Closed game](../2005-06/06_Regular_Season/11_November/Week_2/Game_2.md)
- [Closed game](../2005-06/06_Regular_Season/11_November/Week_2/Game_3.md)
- [Closed game](../2005-06/06_Regular_Season/11_November/Week_3/Game_1.md)
- [Closed game](../2005-06/06_Regular_Season/11_November/Week_3/Game_2.md)
- [Closed game](../2005-06/06_Regular_Season/11_November/Week_3/Game_3.md)
- [Closed game](../2005-06/06_Regular_Season/11_November/Week_4/Game_1.md)
- [Closed game](../2005-06/06_Regular_Season/11_November/Week_4/Game_2.md)
- [Closed game](../2005-06/06_Regular_Season/11_November/Week_4/Game_3.md)
- [Closed game](../2005-06/06_Regular_Season/11_November/Week_4/Game_4.md)
- [Closed game](../2005-06/06_Regular_Season/11_November/Week_4/Game_5.md)
- [Closed game](../2005-06/06_Regular_Season/12_December/Week_1/Game_1.md)
- [Closed game](../2005-06/06_Regular_Season/12_December/Week_1/Game_2.md)
- [Closed game](../2005-06/06_Regular_Season/12_December/Week_1/Game_3.md)
- [Closed game](../2005-06/06_Regular_Season/12_December/Week_1/Game_4.md)
- [Closed game](../2005-06/06_Regular_Season/12_December/Week_2/Game_1.md)
- [Closed game](../2005-06/06_Regular_Season/12_December/Week_2/Game_2.md)
- [Closed game](../2005-06/06_Regular_Season/12_December/Week_2/Game_3.md)
- [Closed game](../2005-06/06_Regular_Season/12_December/Week_2/Game_4.md)
- [Closed game](../2005-06/06_Regular_Season/12_December/Week_3/Game_1.md)
- [Closed game](../2005-06/06_Regular_Season/12_December/Week_3/Game_2.md)
- [Closed game](../2005-06/06_Regular_Season/12_December/Week_3/Game_3.md)
- [Closed game](../2005-06/06_Regular_Season/12_December/Week_4/Game_1.md)
- [Closed game](../2005-06/06_Regular_Season/12_December/Week_4/Game_2.md)
- [Closed game](../2005-06/06_Regular_Season/12_December/Week_4/Game_3.md)
- [Closed game](../2005-06/06_Regular_Season/12_December/Week_4/Game_4.md)
- [Closed game](../2005-06/06_Regular_Season/12_December/Week_4/Game_5.md)
- [Closed game](../2005-06/06_Regular_Season/01_January/Week_1/Game_1.md)
- [Closed game](../2005-06/06_Regular_Season/01_January/Week_1/Game_2.md)
- [Closed game](../2005-06/06_Regular_Season/01_January/Week_1/Game_3.md)
- [Closed game](../2005-06/06_Regular_Season/01_January/Week_2/Game_1.md)
- [Closed game](../2005-06/06_Regular_Season/01_January/Week_2/Game_2.md)
- [Closed game](../2005-06/06_Regular_Season/01_January/Week_2/Game_3.md)
- [Closed game](../2005-06/06_Regular_Season/01_January/Week_2/Game_4.md)
- [Closed game](../2005-06/06_Regular_Season/01_January/Week_3/Game_1.md)
- [Closed game](../2005-06/06_Regular_Season/01_January/Week_3/Game_2.md)
- [Closed game](../2005-06/06_Regular_Season/01_January/Week_4/Game_1.md)
- [Closed game](../2005-06/06_Regular_Season/01_January/Week_4/Game_2.md)
- [Closed game](../2005-06/06_Regular_Season/01_January/Week_4/Game_3.md)
- [Closed game](../2005-06/06_Regular_Season/01_January/Week_4/Game_4.md)
- [Closed game](../2005-06/06_Regular_Season/01_January/Week_4/Game_5.md)
- [Closed game](../2005-06/06_Regular_Season/01_January/Week_4/Game_6.md)
- [Closed game](../2005-06/06_Regular_Season/02_February/Week_1/Game_1.md)
- [Closed game](../2005-06/06_Regular_Season/02_February/Week_1/Game_2.md)
- [Closed game](../2005-06/06_Regular_Season/02_February/Week_1/Game_3.md)
- [Closed game](../2005-06/06_Regular_Season/02_February/Week_2/Game_1.md)
- [Closed game](../2005-06/06_Regular_Season/02_February/Week_2/Game_2.md)
- [Closed game](../2005-06/06_Regular_Season/02_February/Week_2/Game_3.md)
- [Closed game](../2005-06/06_Regular_Season/02_February/Week_3/Game_1.md)
- [Closed game](../2005-06/11_All_Star/All_Star_Game/Game_1.md)
- [Closed game](../2005-06/06_Regular_Season/02_February/Week_4/Game_1.md)
- [Closed game](../2005-06/06_Regular_Season/02_February/Week_4/Game_2.md)
- [Closed game](../2005-06/06_Regular_Season/02_February/Week_4/Game_3.md)
- [Closed game](../2005-06/06_Regular_Season/03_March/Week_1/Game_1.md)
- [Closed game](../2005-06/06_Regular_Season/03_March/Week_1/Game_2.md)
- [Closed game](../2005-06/06_Regular_Season/03_March/Week_1/Game_3.md)
- [Closed game](../2005-06/06_Regular_Season/03_March/Week_2/Game_1.md)
- [Closed game](../2005-06/06_Regular_Season/03_March/Week_2/Game_2.md)
- [Closed game](../2005-06/06_Regular_Season/03_March/Week_2/Game_3.md)
- [Closed game](../2005-06/06_Regular_Season/03_March/Week_2/Game_4.md)
- [Closed game](../2005-06/06_Regular_Season/03_March/Week_3/Game_1.md)
- [Closed game](../2005-06/06_Regular_Season/03_March/Week_3/Game_2.md)
- [Closed game](../2005-06/06_Regular_Season/03_March/Week_3/Game_3.md)
- [Closed game](../2005-06/06_Regular_Season/03_March/Week_3/Game_4.md)
- [Closed game](../2005-06/06_Regular_Season/03_March/Week_4/Game_1.md)
- [Closed game](../2005-06/06_Regular_Season/03_March/Week_4/Game_2.md)
- [Closed game](../2005-06/06_Regular_Season/03_March/Week_4/Game_3.md)
- [Closed game](../2005-06/06_Regular_Season/03_March/Week_4/Game_4.md)
- [Closed game](../2005-06/06_Regular_Season/04_April/Week_1/Game_1.md)
- [Closed game](../2005-06/06_Regular_Season/04_April/Week_1/Game_2.md)
- [Closed game](../2005-06/06_Regular_Season/04_April/Week_1/Game_3.md)
- [Closed game](../2005-06/06_Regular_Season/04_April/Week_1/Game_4.md)
- [Closed game](../2005-06/06_Regular_Season/04_April/Week_2/Game_1.md)
- [Closed game](../2005-06/06_Regular_Season/04_April/Week_2/Game_2.md)
- [Closed game](../2005-06/06_Regular_Season/04_April/Week_2/Game_3.md)
- [Closed game](../2005-06/06_Regular_Season/04_April/Week_2/Game_4.md)
- [Closed game](../2005-06/06_Regular_Season/04_April/Week_3/Game_1.md)
- [Closed game](../2005-06/06_Regular_Season/04_April/Week_3/Game_2.md)
- [Closed game](../2005-06/06_Regular_Season/04_April/Week_3/Game_3.md)
- [Closed game](../2005-06/08_Playoffs/First_Round/Game_1.md)
- [Closed game](../2005-06/08_Playoffs/First_Round/Game_2.md)
- [Closed game](../2005-06/08_Playoffs/First_Round/Game_3.md)
- [Closed game](../2005-06/08_Playoffs/First_Round/Game_4.md)
- [Closed game](../2005-06/08_Playoffs/First_Round/Game_5.md)
- [Closed game](../2005-06/08_Playoffs/Conference_Semifinals/Game_1.md)
- [Closed game](../2005-06/08_Playoffs/Conference_Semifinals/Game_2.md)
- [Closed game](../2005-06/08_Playoffs/Conference_Semifinals/Game_3.md)
- [Closed game](../2005-06/08_Playoffs/Conference_Semifinals/Game_4.md)
- [Closed game](../2005-06/08_Playoffs/Conference_Semifinals/Game_5.md)
- [Closed game](../2005-06/08_Playoffs/Conference_Finals/Game_1.md)
- [Closed game](../2005-06/08_Playoffs/Conference_Finals/Game_2.md)
- [Closed game](../2005-06/08_Playoffs/Conference_Finals/Game_3.md)
- [Closed game](../2005-06/08_Playoffs/Conference_Finals/Game_4.md)
- [Closed game](../2005-06/08_Playoffs/Conference_Finals/Game_5.md)
- [Closed game](../2005-06/08_Playoffs/Conference_Finals/Game_6.md)
- [Closed game](../2005-06/08_Playoffs/Conference_Finals/Game_7.md)
- [Dated milestone working records and player replies](../milestones.json)
