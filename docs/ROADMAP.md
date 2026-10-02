# Build roadmap

Only what the career needs to move forward, in the order the career clock reaches it. World model: real league, simulated Miami (option D, see `AGENTS.md`). An item belongs here only if the career stops or plays wrong without it.

Status: `done`, `next`, `blocked: <what is missing>`, `later`.

## Before opening night (career at June 26, 2003)

| # | Item | Why it is needed | Status |
|---|---|---|---|
| 1 | League contracts and cap ledger | Every team's payroll and cap position | done (stage 1, `runtime/contracts.py`) |
| 2 | Free-agent cap holds under the 1999 agreement, for Miami | Miami's real cap room depends on them | blocked: sourced cap-hold rules |
| 3 | Bird-rights tenure for Miami's expiring players | Decides whom Miami can re-sign over the cap | blocked: years-with-team data for Miami's seven expiring players |
| 4 | Miami's June 30 decisions: team options, Carter's player option, qualifying offers | First events on the clock | next |
| 5 | Wade's rookie contract, with a negotiation log | Wade is unsigned; first user decision | next |
| 6 | Miami's free agency (July 1 to 14 talks, signings from July 15), against a market of real clubs | Decides Miami's roster | after 2-5 |
| 7 | Careers data: player season rates (option C) and real team rosters and minutes (option D), from 22 Basketball-Reference CSVs | Every opponent's lineup and every real player's ability | blocked: data upload; instructions in `library/incoming/CAREERS_DATA_INSTRUCTIONS.md` |
| 8 | Rotations: real minute shares for other clubs (from item 7), Miami's from its own depth chart, plus the conflict rules in `AGENTS.md` | Games need real lineups | after 6 and 7 |
| 9 | Miami's perimeter-defense grade for Wade at camp | Agreed rating decision | at training camp |
| 10 | Game builder: Miami game notes and requests from the schedule, on their dates | No hand-written requests | before October 5 |
| 11 | League slate: Railway plays every non-Miami game from the schedule | Standings need all 1,189 games | before October 28 |
| 12 | Injuries and availability | 82 games with no injuries is not a season | before October 28 |
| 13 | Write-back: results into game notes, Wade, Miami and league stat pages | Results count only once written into the career record | before October 28 |
| 13a | Wade's requests to the front office: logged, weighed by his standing, engine-drawn where uncertain | Wade's influence on Miami | with item 4 |

## During and after 2003-04

| # | Item | Why it is needed | Status |
|---|---|---|---|
| 14 | Standings, tiebreakers, 16-team playoff bracket | Season outcome | before April 2004 |
| 15 | Season awards voting (shortlists exist; winners must be decided) | Awards pages need results | before April 2004 |
| 16 | Miami's trades, including the February deadline, with a simple acceptance rule for the real club on the other side | Miami's roster moves during a season | later (2003-04 season) |
| 17 | Miami's draft picks on draft-night evidence; other clubs' picks follow history unless Miami's moves conflict | 2004 draft | before June 2004 |
| 18 | Season rollover: 2004-05 era rules (hand-check, 30 teams), real 2003-04 league averages, Wade's year-end update (`runtime/protagonist.py`), contracts and cap rollover, 2004 cap publication date | Next season cannot start without them | before July 2004 |
| 19 | Structural rules for each agreement (raise limits, lengths, extension windows): 1999, then 2005 | Every contract after 2003-04 | 1999 now with item 2; 2005 before summer 2005 |

## Far ahead

| # | Item | Plan | Status |
|---|---|---|---|
| 20 | 2011 lockout with Wade negotiating for the players' association | Closed menu of dials, each one number in the 2011 rule file: revenue share, raise limits, contract length, exception amounts, tax and apron level, amnesty, rookie-extension tier, agreement length. Gains cost concessions or lost paychecks. Season length fixed at the real 66 games. Changes apply forward only. One negotiation log plus a term sheet compared with the real 2011 terms. Wade needs a union seat earned through his own earlier choices. Real 2011 terms stay reference-only until the career reaches 2011. | later (decide before summer 2011) |

## Deliberately not on this list

Summer-league games, coaching carousels, media and narrative systems, and anything else that does not change a game result, a roster or a contract. Add one only when the career actually needs it.
