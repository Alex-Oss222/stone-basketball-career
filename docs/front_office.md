# Miami's front office

Miami is the only simulated club (world model D). Its front office uses only evidence available on the career date: 2002-03 statistics (`library/2003/league/nba_2003_veteran_ratings.json`), contracts, the 1999 rules and Wade's logged requests. It never reads real-career trajectories or real rosters. All rules are provisional judgement constants in `runtime/front_office.py`.

## June 30, 2003 (roadmap item 4)

| Decision | Rule |
|---|---|
| Team options (Rasual Butler, Sean Lampley, Ken Johnson) | Exercise if the player logged 400+ minutes in 2002-03 or is 24 or younger |
| Qualifying offers (Eddie House, Malik Allen, Mike James) | Tender if 500+ minutes in 2002-03 or 24 or younger; amounts from `00_Team/Finances/free_agent_rights.json` |
| Anthony Carter's player option | His decision, drawn by the engine. Chance of opting in: 0.5 + 0.4 x (option - market value) / option, kept within 5-95%. Market value: his minimum plus a share of the mid-level proportional to 2002-03 minutes (capped at 2,000) |
| Renouncing free agents (Mourning and others) | Not a June 30 decision; it belongs to free-agency planning (item 6) |

Run `python scripts/run_june30.py --write` only when the career clock reaches June 30. It stops if Carter's `years_of_service` is not recorded on `contract_schedules.json` (it sets his minimum salary). It writes the rule decisions with reasons and one `*.decision.json` per chance-based decision; pushing lets Railway draw them, and `/decisions/<event_id>` returns the outcome.

## Miami's holdings (conflict rule 2)

`00_Team/Team/Roster/holdings.json` records, with dates, every player simulated Miami holds: `from` the date Miami holds him, `until` the first date it no longer does (null while held). Real clubs' rotations leave out whoever Miami holds on the game's date. When Miami signs, trades, waives or loses a player, append an entry or set `until` on or after the career date, in the same change as the register; never change a date that has passed, because played games depend on it. On June 26, 2003 the expiring contracts run until July 1, and the pending options stay open until the June 30 decisions close the ones that are declined. Validation checks that every player the register holds is held on its `as_of` date.

## Hiring pool (league staffs)

`library/<year>/league/nba_<season>_staffs.json` (2002-03 to 2013-14, `scripts/import_staffs.py`) lists every real club's head coaches (in order, with the part of the season each coached), top basketball executives and assistant and support staff, from the Basketball-Reference team pages and coaches tables, with no win-loss records. Everyone on a real club's staff on the career date is a candidate Miami can hire; once Miami hires him he leaves his real club from that date. A coaching change counts only once the career clock reaches it, and Miami's own staff from 2003-04 lives in its organization records.

## Wade's requests

Before a decision date, Wade's wishes go in the phase folder's `wade_requests.json`:

```json
{"requests": [{"date": "2003-06-28", "subject": "team_option", "player": "Ken Johnson",
               "requested": "exercise", "note": "what Wade tells the front office"}]}
```

A request that agrees with the rule changes nothing. One that opposes it becomes an engine-drawn decision. The chance it wins is Wade's standing weight times how close the rule's call was (0 = right on the line, 1 = clear-cut). Standing weights: unsigned rookie 0.15, rookie 0.2, starter 0.35, All-Star 0.6, franchise player 0.8. A clear-cut decision cannot be moved.

## Free agency (roadmap item 6, phase B of `front_office_design.md`)

`python scripts/run_free_agency.py --write <date>` moves the career clock one day at a time from `current_state.json` to the date: the June 30 decisions, Miami's plan, offers, the players' answers, signings and finally Wade's rookie offer. `--plan <date>` prints Miami's plan for a date without writing. Every chance event is a `*.decision.json` the engine draws; the run stops on the day a draw is pending and continues from that day once `scripts/collect_results.py` (run by the `collect-results` workflow after each push to `milestone-1`, and hourly) has written the `*.decision.result.json` beside it. Nothing in the driver draws chance.

| Piece | Module | What it reads | Judgement constants (named in code) |
|---|---|---|---|
| Value and price | `runtime/valuation.py` | 2002-03 totals, birth dates, the June 26 contract inventory, the 2003-04 cap rules | replacement 5.0 efficiency per game, 500-minute shrinkage, age factors, comparables fit on players under contract with 500+ minutes |
| Market | `runtime/market.py` | the rights file (129 free agents), the dated real 2003 moves as exit dates (a real Miami signing is skipped and the player stays with his old club), the calendar | pressure from clubs with room and tier supply, 5% ask decay a week from July 16, years wanted by age, trait odds by age, the priority vectors, logistic acceptance (slope 6, floor 2%, ceiling 95%), insult at 70% of the ask, three rounds of patience |
| Front office | `runtime/gm.py` | Miami's cap sheet, rights, register, depth chart, `team_config.json` (`budget`, `projection`, `location_appeal`) | cap room = planning cap (prior cap until July 15) less salary, holds and a minimum-salary charge per spot under twelve; needs by position; target score = fit x (value above replacement)^1.5 per mid-level of ask, Wade's request x (1 + standing weight); keep rights while the hold is under 1.5x the valuation; renounce cheap rights for a target scoring 20+; open at 87.5% of the ask, concede toward the counter, never past 110% of the valuation, three rounds; a real incumbent matches a sheet with 0.5 + 2.5 x surplus, x 0.3 over the tax projection |
| Desk adapter | `runtime/negotiation.py` | `runtime/contract_negotiation.py` | offers open three days; every offer passes `cba.terms_errors` first and the attestation records the check; answers and matches cite their decision event; RFA sheets run the 15-day receipt and the fifth slot; a counter is the split between the offer and the ask, at least 8% above the offer |
| Write-back | `runtime/signing.py` | all of Miami's records | one adapter writes a signing to the cap sheet, the holdings (rule 2), the register, a new player card, the finance summary and `cap_sheet.md`, the depth chart (unassigned arrival), the phase note and `current_state.json`; renouncements mark the rights file; a matched sheet goes to `01_Free_Agency/world_effects.json` |

Records under `01_Free_Agency/`: `June_30/` (rule decisions and draws), `Plans/plan_<date>.json` (cap position, holds to renounce, needs, targets, re-sign candidates, the review of Wade's requests), `Negotiations/<player>.json` (the desk state with every offer version, the drawn priorities, each round, the agreement, the sheet, the signing), the decision requests and results beside them, `free_agency_state.json` (the driver's progress) and the dated lines in `note.md`. During the moratorium (July 1 to 15) Miami talks only to targets scoring 20 or more and an acceptance is an agreement in principle; the desk records the acceptance, or the signed sheet, on July 16 or the day of agreement after it. Re-sign talks with own free agents open from July 16, best first, down to a roster of thirteen. Miami offers Wade his rookie contract once no talks are open after July 16, with the role the depth chart can honestly promise.

Validation replays every negotiation record on the desk (`negotiation_errors`) and, once the clock has left June 26, reconciles the finance summary to the cap sheet and checks that every signed player has a card, a signed record and an open holding from his signing date (`ledger_errors`).

## Wade's rookie contract (roadmap item 5)

Miami opens with 120% of the No. 5 scale, the customary level for first-round picks: $2,636,400, $2,834,160 and $3,031,920 over 2003-04 to 2005-06, plus a $3,841,443 team option for 2006-07, to be exercised by October 31, 2005 (October 31 after his second season, FAQ Q38). Miami intends to sign him after its July free-agency moves, because until he signs he counts at 100% of scale.

The free-agency driver opens `01_Free_Agency/Wade_Rookie_Contract/negotiation_log.json` with this offer and a role promise once Miami's July talks are closed (`python scripts/open_rookie_negotiation.py --write <date>` does the same by hand). Wade's answers (accept, counter, request a signing date, hold out) are the user's decisions and are appended as entries. Validation checks every entry's terms against the rookie scale and keeps dates in order; nothing may follow the signing.
