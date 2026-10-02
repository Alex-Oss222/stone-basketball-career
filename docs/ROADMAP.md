# Build roadmap

Only what the career needs to move forward, in the order the career clock reaches it. World model: real league, simulated Miami (option D, see `AGENTS.md`). An item belongs here only if the career stops or plays wrong without it.

Status: `done`, `next`, `blocked: <what is missing>`, `later`.

## Before opening night (career at June 26, 2003)

| # | Item | Why it is needed | Status |
|---|---|---|---|
| 1 | League contracts and cap ledger | Every team's payroll and cap position | done (stage 1, `runtime/contracts.py`) |
| 2 | Free-agent cap holds under the 1999 agreement, for Miami | Miami's real cap room depends on them | done: `library/2003/league/nba_1999_cba_rules.json`, minimum scale, league rights file, `runtime/cba.py`; open: the minimum-contract hold rule (unverified) and the FAQ text for Questions 10 and 22 |
| 3 | Bird-rights tenure for Miami's expiring players | Decides whom Miami can re-sign over the cap | done: `00_Team/Finances/free_agent_rights.json` (built by `scripts/build_miami_free_agent_rights.py`) |
| 4 | Miami's June 30 decisions: team options, Carter's player option, qualifying offers | First events on the clock | built (`runtime/front_office.py`, `scripts/run_june30.py`, engine-drawn `*.decision.json`); ready: runs when the clock reaches June 30 (Carter's years of service recorded: 4) |
| 5 | Wade's rookie contract, with a negotiation log | Wade is unsigned; first user decision | built (`runtime/rookie_contract.py`, `scripts/open_rookie_negotiation.py`); opens on the offer date |
| 6 | Miami's free agency (talks from July 1, cap published July 15, signings from July 16, 2003; `library/2003/league/nba_2003_04_calendar.json`) against a market of real clubs | Decides Miami's roster | designed: `docs/front_office_design.md` (phases A to D). Built so far: the isolated offer/UFA/RFA workflow and the four-offer board (`docs/contract_negotiation_engine.md`), the dated real 2003 market as world data (`nba_2003_offseason_transactions.json`), the calendar and rule corrections (phase A). Phase B built: valuation and price (`runtime/valuation.py`), the market with dated exits and drawn answers (`runtime/market.py`), Miami's ledger, needs, plan, bidding and incumbent-match rule (`runtime/gm.py`), the desk adapter with legality checks and the RFA sheet flow (`runtime/negotiation.py`), the write-back (`runtime/signing.py`), the day-by-day driver (`scripts/run_free_agency.py`) and the results collector. Next: phase C, trades (item 16); phase D, camp |
| 7 | Careers data: player season rates (option C) and real team rosters and minutes (option D) | Every opponent's lineup and every real player's ability | done: `library/careers/nba_player_careers.json` (1,185 players) and `library/<year>/league/nba_<season>_team_rosters.json`, 2003-04 to 2013-14 |
| 8 | Rotations: real minute shares for other clubs (from item 7), Miami's from its own depth chart, plus the conflict rules in `AGENTS.md` | Games need real lineups | done for real clubs: the real roster on the game's date with minutes per game and availability (`runtime/rotations.py`, request `"rotation": "real"`); a traded player is with one club at a time; rules 1-3 applied, including real Miami's between-season signings back on their previous clubs. Rule 2 reads Miami's dated holdings (`00_Team/Team/Roster/holdings.json`). Open: Miami's explicit `players` list from the depth chart (with item 10); players simulated Miami sends to a real club (a dated record the request turns into arrivals, with items 6 and 16); before 2004-05, a list of players real Miami traded away between seasons, since the season tables cannot tell a trade from a free-agent move |
| 9 | Miami's perimeter-defense grade for Wade at camp | Agreed rating decision; until then Wade counts as an average defender (defensive value 0) | at training camp, as part of the camp loop (`docs/front_office_design.md`, section 8, phase D); the grade is mapped onto the engine's defensive value |
| 10 | Game builder: Miami game notes and requests from the schedule, on their dates | No hand-written requests | before October 5 |
| 11 | League slate: Railway plays every non-Miami game from the schedule | Standings need all 1,189 games | before October 28 |
| 12 | Injuries and availability | 82 games with no injuries is not a season | done: real clubs by real availability, Miami by engine-drawn injuries in each result (`runtime/injuries.py`), back-to-back fatigue for all; the game builder (item 10) must leave injured Miami players out (`injured_out`) and the write-back (item 13) record injuries |
| 13 | Write-back: results into game notes, Wade, Miami and league stat pages | Results count only once written into the career record | partial: player identity and source-based season/month/week/game reports built (`scripts/update_player_reports.py`, `docs/player_statistics.md`); remaining before October 28: automated canonical result write-back, Miami/league aggregation and injury-state updates |
| 13a | Wade's requests to the front office: logged, weighed by his standing, engine-drawn where uncertain | Wade's influence on Miami | built for June 30 decisions (`wade_requests.json`, `docs/front_office.md`); extend to later decisions as they are built |

## Engine problems, worst first

Found in the engine review on real 2003-04 rosters. Model and numbers: `docs/engine_model.md`; re-check with `python scripts/engine_diagnostics.py 4` (four seasons of the real schedule).

| # | Problem | Fix | Status |
|---|---|---|---|
| E1 | Defense barely existed: only legacy grades, steals and blocks | Real DBPM in the careers data; the five defenders on the floor move the opponent's shooting and turnovers | done (kernel 2003.3): +5 on the floor allows about 5 fewer points per 100 |
| E2 | Team quality compressed | E1, plus a score effect centred on the margin the rosters should produce, so it removes random swings but not quality | done: spread of club average margins 4.6 within a season (benchmark 4-5) |
| E3 | Stars overplayed (season shares over a top-12 list) | Minutes per game and availability on the game's date, with caps (together with item 8) | done: players with 30+ minutes play 35.3 against an input of 35.3 |
| E4 | Results too random, no late-game logic | Foul when trailing, run the clock when leading, hold for the last shot, closing lineups, garbage time, and the score effect | done: margin SD 13.4, overtime 5.4% |
| E5 | Too many foul-outs | Sit players in foul trouble, bring them back later | done: 0.22 per game |
| E6 | Every club plays at the league pace | Each club's pace from the season before (the same rule as the league averages) | done (kernel 2003.4): `library/<year>/league/nba_<season>_team_pace.json` from `scripts/import_team_pace.py`; a game runs at the average of the two clubs' paces; Miami at the league pace until its coaches set one |
| E7 | No injuries or fatigue | Roadmap item 12 | done (kernel 2003.5): back-to-backs for every club; engine-drawn injuries for Miami |

## During and after 2003-04

| # | Item | Why it is needed | Status |
|---|---|---|---|
| 14 | Standings, tiebreakers, 16-team playoff bracket | Season outcome | before April 2004 |
| 15 | Season awards voting (shortlists exist; winners must be decided) | Awards pages need results | before April 2004 |
| 16 | Miami's trades, including the February 19, 2004 deadline, with a rule-based answer from the real club on the other side | Miami's roster moves during a season | designed (`docs/front_office_design.md`, section 7, phase C): 115% + $100,000 matching, base-year compensation, pick values, posture, acceptance draws, arrivals ledger |
| 17 | Miami's draft picks on draft-night evidence; other clubs' picks follow history unless Miami's moves conflict | 2004 draft | before June 2004 |
| 18 | Season rollover: 2004-05 era rules (hand-check, 30 teams), real 2003-04 league averages, Wade's year-end update (`runtime/protagonist.py`), real players' capped 20% feedback file (`runtime/trajectories.season_feedback`), contracts and cap rollover, 2004 cap publication date | Next season cannot start without them | before July 2004 |
| 19 | Structural rules for each agreement (raise limits, lengths, extension windows): 1999, then 2005 | Every contract after 2003-04 | 1999 now with item 2; 2005 before summer 2005 |

## Far ahead

| # | Item | Plan | Status |
|---|---|---|---|
| 20 | 2011 lockout with Wade negotiating for the players' association | Closed menu of dials, each one number in the 2011 rule file: revenue share, raise limits, contract length, exception amounts, tax and apron level, amnesty, rookie-extension tier, agreement length. Gains cost concessions or lost paychecks. Season length fixed at the real 66 games. Changes apply forward only. One negotiation log plus a term sheet compared with the real 2011 terms. Wade needs a union seat earned through his own earlier choices. Real 2011 terms stay reference-only until the career reaches 2011. | later (decide before summer 2011) |

## Deliberately not on this list

Summer-league games, coaching carousels, media and narrative systems, and anything else that does not change a game result, a roster or a contract. Add one only when the career actually needs it.
