# Contract extensions

Every club, Miami included, may extend a contract in its final season (`runtime/extensions.py`, the user's request of
October 2026: without extensions, players history kept off the market, such as Allen Iverson and Andrei Kirilenko,
reached free agency). Wade's own extension is his decision.

## Gate

Extension days start on **2005-10-31**, the 2002 draft class's rookie-scale deadline and the career date the rule was
built on. The days that had already passed (2003-10-31, 2004-06-29, 2004-10-31, 2005-06-29) belong to markets, options
and trades that are recorded and replay unchanged; they are never decided. A contract entry without an `extension` key
reads exactly as before, so every earlier record and its tests are unchanged.

## Rules (the agreement in force)

The 2005 agreement's terms are in `library/2005/league/nba_2005_cba_rules.json` under `extensions` (cbafaq05 Q52; the
numeric form is `extensions.terms`, with Q11's 105% free-agent maximum). `extensions.rules(season)` reads them for the
decision day's league year, keyed by `agreement.terms(season)`; under the 1999 agreement there is no extension day.

| Contract | When | Length | First year | Raises |
| --- | --- | --- | --- | --- |
| Rookie scale, option on the last scale season picked up | to October 31 before that season | up to 5 more seasons | any amount up to his maximum | up to 10.5% of the first extension year |
| Four or five seasons; six signed from July 1, 2005 | 3 years after signing, to June 30 | 5 seasons including those remaining | up to 110.5% of the last salary and his free-agent maximum (tier maximum or 105% of the last salary) | up to 10.5% of the last salary |
| Six or seven seasons signed before July 1, 2005 | 4 years after signing | as above | as above | as above |
| An extended contract | 3 years after the extension | as above | as above | as above |
| Under four seasons | never | | | |

The October 31 weekend rule (next business day) is not modelled; the career decides on October 31, as options do.

## Days

- **October 31** every year: rookie-scale contracts on their deadline, veterans in a pre-season review.
- **June 29** from 2006: veterans, the last day before free agency (the options' veteran deadline). From June 1 the
  valuation reads the season just closed, so a veteran turned down in October is asked again on his final season.

Each day is decided once (`scripts/extension_day.py --write DATE`), on its own date: the career clock is on the day,
and the holders, evidence and payrolls are those of its start. The driver must run the step every day, before the
day's other club steps (the market day, the trade scan and the option step), then draw its packets and run it again to
apply them. That driver step is `extension_day` in `scripts/advance.py`, called on camp days, in-season days and the
summer's playoff-path days, each time before `option_day`; until it runs, every extension day the clock passes is
missed, and validation and the rollover say so.

A day is never decided late or ahead of the clock. `extensions.run` refuses (`ExtensionError`; the CLI prints
"extensions refused: ..." and exits 1, so the driver stops with the reason on screen):

- a day the clock has passed without deciding it: later systems (trades, waivers, options, the next market) have used
  the contracts since, so a late decision could contradict them. A missed day is reported by validation and the
  rollover and needs a decision; it is never caught up by a late run;
- a day the clock has not reached;
- a day whose league year is not live yet (an October day before its rollover);
- a day while a decision of an earlier day is not applied (its draw or Wade's answer pending).

The rollover out of a league year waits for every extension of it to be settled (`extensions.rollover_blockers`). While
other gates still hold the rollover back the extension items are listed with them; once the rollover is due they are
raised (`Rollover.blockers`), so a missed or unresolved extension stops the driver visibly instead of holding the season
in the summer.

## Eligibility

Only repository records: an unknown signing date or length is never eligible.

- The contract in force ends with the decision season (no later season, no option on the next one), and a club holds
  the player at the start of the day (the end of the day before, so a same-day trade never precedes the decision).
- A waived contract is not the one in force: a `waive` in the league's dated moves (`League/league_moves.json`) after
  the contract's signing that no `claim` took up ends it. The club that waived him still owes it (its salary stays in
  that club's payroll), and the ten-day, rest-of-season or market deal he plays on with a later club is a new one.
  A claim assigns the contract, as a trade does.
- Rookie scale: the team option on the decision season was exercised on the October 31 a year before
  (`League/option_decisions.json`), and the contract in force is still that rookie-scale contract (its dated origin, or
  the ledger's rookie-scale flag when no record dates it). A declined option is never eligible.
- Veteran: no option decision on the next season cut the contract short; not a rookie-scale contract; signing date and
  length from the latest extension, else the summer market record that signed it (traced back season by season through
  the ledgers), else the June 2003 inventory (its contract history marks an extension, which makes an extended contract)
  or the real 2003 summer signing a 2004-05 entry was built from; Miami's own sheet for a contract Miami signed.

On 2005-10-31: 24 eligible (18 rookie-scale contracts of the 2002 class, including Miami's Caron Butler; 6 veterans:
Ben Wallace, Cuttino Mobley, Tony Delk, Tony Battie, Al Harrington and Shaquille O'Neal, whose 2000 contract is an
extension). `python scripts/extension_day.py --eligible DATE` prints the set and why the other final-season contracts
are not eligible.

## The club's call

One rule for every club (judgement constants in `runtime/extensions.py`):

- **Price**: the market price of his closed-season production (`Valuation.market_price`, honors included) inside the
  minimum and his free-agent maximum for his service next season, under the cap rules published by the day (the
  planning season in `league_cap_history.json`; never a later cap). **Worth**: the price, x1.25 at 24 or younger.
- **Core ratio** r = worth / (1.0 x the mid-level). r >= 1.2: offer. r <= 0.8: no offer. In between: an engine draw,
  P(offer) = (r - 0.8) / 0.4 (the options' close band).
- **No offer** before any call when his real career has no next season, there is no valuation, no legal first year
  exists, or next season's committed payroll plus the club's earlier offers that day plus this one passes the summer
  market's ceiling (the tax line; 10% over for a contender; for a player priced at two mid-levels, 35% over the tax line
  or 17.5% over the committed payroll). Players are taken by worth, highest first.
- **Terms**: the years he wants by age (5 to 26, 4 to 29, 3 to 32, 2 to 34, then 1) within the limit; the first year at
  his price (rookie scale) or held to 110.5% of his last salary (veteran); flat raises at the limit.

## The player's answer

An engine draw for every player but Wade. The 2003 factor model (`runtime/player_utility.py`, no drawn priority)
scores the extension at his club against free agency next summer at his price with a league-average club; P(sign) is the
model's accept odds on the utility gap, with the counter share folded into a decline. A clear offer is one packet
(`signed`, `declined`); a close call is one packet holding the club's call and his answer (`signed`, `declined`,
`no_offer`). Packets: `<season>/League/Extension_Draws/<day>-extension-<bbr_id>.decision.json`, drawn once by
`scripts/draw_decisions.py`, never re-rolled.

## Wade

Miami's AI/GM calls by the same rule as every club, the close band included: there the engine draws Miami's call alone
(a packet `<day>-extension-wadedw01` with `offer` and `no_offer`, P(offer) = (r - 0.8) / 0.4), since his answer is his
own. A clear offer opens on the decision day; a drawn offer opens on the run that reads the draw (the same day, after
the driver draws). An offer writes `<season>/01_Free_Agency/Wade_Extension/<day>-dwyane_wade-extension.json` and its
milestone page, and adds `wade_extension:<id>` to `current_state.pending_player_decisions`, which stops the clock. A
drawn `no_offer` closes the decision with no question to him. Wade answers with
`python scripts/player_milestone.py --reply reply.json --expected-version <version of the offer file>`:

```json
{"kind": "extension", "season": "2006-07", "event_id": "2006-10-31-dwyane_wade-extension", "action": "accept",
 "date": "2006-10-31", "text": "Wade's own words", "source_ref": "career/Dwyane_Wade/..."}
```

The reply never signs anything; the next `scripts/extension_day.py --write DATE` applies it (accept: signed; decline: no
contract changes). Wade is first eligible on 2006-10-31 (his 2006-07 option was exercised on 2005-10-31).

## Wade's own terms

Wade may file the terms he wants (a request with `subject` `extension_terms` in any season folder's
`*/wade_requests.json`, for example `2005-06/04_Training_Camp/wade_requests.json` of 2005-10-31: 20% under his fair
market value, five additional seasons, the first four fully guaranteed, the fifth a Miami team option, raises at the
limit, no no-trade clause; if Miami does not offer, he plays out his rookie contract).

- **Reader** (`extensions.terms_request`): his latest `extension_terms` row dated on or before the decision day, from any
  season folder (filed in 2005-06, read in 2006-07); a same-day tie goes to the later file and row. A filing is one
  negotiation's terms: once a Wade decision day on or after its date has passed, it is spent, so a filing for the
  rookie-scale extension never sets a later veteran extension. Only Wade's own decision reads it, and every recorded day
  (2005-10-31: Wade was not eligible) is unchanged.
- **The worth call is unchanged**: offer or no offer, and the close-band draw, read his full worth exactly as for every
  club. His terms shape the offer Miami makes once it offers. With no offer he plays out his contract, as filed.
- **The payroll test reads what Miami would pay**: his offered first year, which also counts toward Miami's later offers
  that day (`spent`). So his discount can let Miami's offer to him fit under its payroll ceiling where the rule's first
  year would not, and leaves that much more room for a Miami player decided after him the same day (candidates are
  decided in order of worth); that player's decision reads the room, never Wade's terms.

Miami's answer (`extensions.shape`, one rule, no draw): a requested term is adopted when it is legal and at least as
favourable to Miami as its rule's term; otherwise the rule's term stands and the reason is recorded.

| Term | Adopted when | The offer |
| --- | --- | --- |
| `discount_from_market` d | the discounted figure is at or under the rule's first year | first year = his price (the market benchmark the call computes, inside his minimum and maximum) x (1 - d), held to his minimum |
| `additional_seasons` | within the agreement's limit (5 for a rookie-scale extension, Q52) | his seasons; the rule's length is the years he wants by age, so the seasons he names take its place |
| `raise` | "maximum" (the rule's own raise) or a share at or under the limit | flat raises of that share of the first year (a veteran's base: the smaller of the first year and his last salary) |
| `team_option_final_season` | an option clause is recorded (Q51: one option season, the last) | a Miami team option on the final season, inside the five seasons |
| `guaranteed_seasons` | it equals the seasons less the option season | every season but the option season fully guaranteed |
| `no_trade_clause` false, `player_option_final_season` false | always (the rule's form) | no clause, no player option |
| a higher salary (a premium), a player option, a no-trade clause, seasons or raises over the limit, any other term | never: less favourable to Miami or not legal | the rule's term |

A term less favourable to Miami is simply not adopted, never drawn (`front_office.request_override` is not used): the
call already went his way, and his remedy is his own answer (decline). The payroll test counts the offered first year
(the ceiling keeps reading his price).

- **Records**: the decision names the request (`request`: path, row, date, words, terms, source); its offer adds
  `options` ({season: "team_option"}), `guaranteed_seasons`, `team_option_season` and `terms_basis` (the benchmark, the
  discount, the rule's own terms and each term adopted or not with its reason). Wade's offer record carries the same
  and the benchmark and discount in its evidence; his page shows his words, the benchmark and discount, the term table
  and the schedule with each season guaranteed or the option season and its deadline, and keeps accept and decline.
- **The option once signed** is an option season like every other, in the same form: `options` on the league ledger
  entry, `amount_kind` "team_option" on Miami's cap sheet (counted as a conditional amount; left out of a `guaranteed`
  map, so the guarantee review never reads it), "team_option" with guaranteed 0 and `option_deadline` in the contract
  archive and on the contract pages (the option's outcome once decided). `runtime/options.py` decides it on the veteran
  deadline, June 29 before the season (2011-06-29 for 2011-12), never as a rookie-scale option, though the extended row
  keeps its rookie-scale route; a decline cuts the season from the sheet and the ledger (Wade's ledger key too) and the
  extension stays valid. The rollover carries the sheet entry and the ledger's `options`; continuity compares schedules.

The legal limits are sourced: Q52 (the five additional seasons and the 10.5% raises, `extensions.terms`) and Q51 (one
option season, the last, `extensions.option_clause` in `library/2005/league/nba_2005_cba_rules.json`).

## Records and application

- `<season>/League/extension_decisions.json`: `days` (each decided day, its kinds and eligible count) and `decisions`
  (contract, evidence, payroll, club call, offer, answer, packet, outcome, recorded and applied dates).
- A signed extension: the league ledger entry's schedule gains its seasons and an `extension` record (every later ledger
  already written too); for Miami, its cap sheet (`extension`, schedule, amount kinds; status and signing date stay the
  agreement's in force), the schedule totals, the contract archive (`<player_id>-<day>`) and the phase note; for Wade,
  his dated identity and contract status. An option season his terms put in is written in each place's own option form
  (see Wade's own terms).
- Carry-over: `league_contracts.carried` and `build` keep the `extension` record (a rookie-scale flag ends at the first
  extension season), `extensions.reapply` re-applies a season's signed extensions on a rebuild, the rollover sets
  Miami's carried entry `under_contract` from the first extension season and refuses to run while an extension day of
  the closing season is undecided or unresolved (`extensions.rollover_blockers`).
- Continuity leaves out the seasons of an extension signed in the new league year; any other added season is refused.
- Contract pages show each extension as its own agreement from its signing date; the agreement it extends stays current
  until July 1 of the first extension season.
- A trade assigns the extended agreement whole: a summer trade to Miami (`rollover.traded_in`) copies the extension
  record (`extensions.carry_fields`) and counts the original term without the extension's seasons; a Miami row an
  in-season trade copied without it gains it from the records when it is read (`extensions.with_recorded`: contract
  pages, origin, payroll, the rollover).
- The next summer's market reads the extended schedule: the player is under contract, never a free agent or a
  qualifying-offer case.

## Validation

`runtime.extensions.extension_errors(root)`, called by `scripts/validate_repository.py` with the other career checks:
well-formed records; every extension day before the clock decided, each
on its own date (`recorded_on` is the day); a clear call never drawn and a close call always drawn (Miami's on Wade
too, as its own `offer`/`no_offer` packet); packet chances equal to the recorded call and answer; outcomes equal to the
draws or Wade's answer; offers within the agreement's limits; an offer shaped by terms only Wade's, with one team
option season at most (the last), the guaranteed seasons following it and the first year following the benchmark and
the adopted discount; every Wade decision recording exactly his terms on file for its day (`terms_request`, None when
none: a row edited or removed since, or filed for the day afterwards, is refused) and a shaped offer equal to `shape`
recomputed from the recorded evidence, contract and terms (years, first year, raise, schedule, option, `terms_basis`);
Wade's offer record agreeing with his decision; a signed extension's option season missing from a schedule only once
its decline is applied (`League/option_decisions.json`);
signed extensions present (and unsigned ones absent) in every ledger, Miami's sheet and archive; no expiring-contract
treatment in the next market; Wade's offer, page, answer and pending entry in agreement; and each day's eligible set
replayed from its start-of-day holders.
