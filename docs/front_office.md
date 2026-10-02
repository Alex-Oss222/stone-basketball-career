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

## Wade's rookie contract (roadmap item 5)

Miami opens with 120% of the No. 5 scale, the customary level for first-round picks: $2,636,400, $2,834,160 and $3,031,920 over 2003-04 to 2005-06, plus a $3,841,443 team option for 2006-07, to be exercised by October 31, 2005 (October 31 after his second season, FAQ Q38). Miami intends to sign him after its July free-agency moves, because until he signs he counts at 100% of scale.

`python scripts/open_rookie_negotiation.py --write <date>` opens `01_Free_Agency/Wade_Rookie_Contract/negotiation_log.json` on the offer date. Wade's answers (accept, counter, request a signing date, hold out) are the user's decisions and are appended as entries. Validation checks every entry's terms against the rookie scale and keeps dates in order; nothing may follow the signing.
