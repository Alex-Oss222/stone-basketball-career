# Symmetric league: design

Status: phases 1 to 4 built, tested and calibrated; **switched on from December 3, 2003** (the user's decision); phase 5 planned. Run `python scripts/league_day.py --write DATE` every day, before that day's games are built.

## What changes

Under option D the 28 other clubs follow history: real rosters, real minute shares, no front office. A symmetric league gives every club the front office Miami has. Clubs sign, waive and trade on their own objectives, and game inputs read each club's simulated roster on the date.

## What does not change

- **Ability follows real careers.** The talent-trajectory exception (option C) and career continuity are unchanged: every real player's ability each season follows his real career, wherever he plays. Only his club can drift.
- **Nobody with real minutes goes unsigned.** No rule may leave a real player without a club while history gave him minutes. A symmetric market must place every such player each season.
- **No hindsight in decisions.** Every club decides only on evidence dated on or before the date, exactly as Miami does. Real later rosters stay world data for continuity and are never a reason for a move.
- **No re-rolls.** Every chance answer is an engine decision draw.
- **The off switch reproduces today.** With `SYMMETRIC_FROM` unset, every game input, card and page is exactly what option D produces.

## Phases

| Phase | Scope | State |
| --- | --- | --- |
| 1. League cap book | Every club's dated contracts, payroll, cap room, tax position, exceptions used, roster count and owner ceiling (`runtime/league_book.py`) | built, read-only |
| 2. League market | `runtime/league_market.py`, rules from the researched `nba_1999_in_season_rules.json`: 12-15 under contract, 48-hour waivers (a waived player is on nobody's roster and in nobody's pool for two days, then claimed by the worst record on that day's standings or cleared into the pool) (cap room or a minimum contract), 10-day contracts from January 5 (two per player with a club, then rest of season or release), the January 7 guarantee cut, injury-depth signings, upgrades at fifteen. The pool is researched unsigned players (December 1 and monthly snapshots to April 1), players left off at activation, cleared waivers and ended 10-days | built |
| 3. AI-to-AI trades | `runtime/league_trades.py`: weekly (Mondays) to the February 19, 2004 deadline, one or two rotation players for one, both clubs gaining at least 6% on their own objectives (star premium on packages); a club or player in at most one deal a week. Values are stance weights, skill fit (symmetric), a 1.15 status-quo premium, the whole contract's burden by cash weight, current form and post-contract control. Legality is the 1999 salary rule. Untouchables stay. At most two deals a week, one engine decision packet each | built |
| 4. Simulated rosters | `runtime/league_moves.py`: each club starts from its real roster on the activation date. Real moves after it are not applied; `league_moves.json` moves apply from their dates; Miami's rules and the replacements apply on top. `game_requests._club`, `trades.dated_inventory` and the league desk all read it. Each player keeps his whole-season real role | built |
| 5. Rollover | `runtime/offseason.py`: the 2004-05 opening book. Per real player, in order: Miami holds him (rule 2); no real 2004-05 minutes (leaves with history); real Miami sent him away (`nba_2004_miami_transactions.json`, skipped by rule 1, stays); undrifted (follows history: re-signings, options, summer trades, free agency, expansion and draft); drifted (a 2004-05 salary stays with his simulated club, else he signs where history did); new to the league (his real club, or the club a Miami draft choice displaced). Fifteen largest real 2004-05 roles per club, the rest to the pool | book built; Miami draft and free agency, owner ceilings and volume calibration open |

## Activation

`runtime/league_book.SYMMETRIC_FROM = "2003-12-03"`. Setting a date turns the league symmetric from that date; `None` restores option D. Played games keep their inputs. A date mid-season is allowed only after phases 3 and 4 are complete.

## Activation roster

On the activation date each club holds the players whose real stint covers it. A real trade whose next stint begins within 8 games after the date is completed (the Rose-Davis trade of December 1, 2003). Each club keeps its fifteen largest real roles, never letting go of a rookie-scale contract, a 2003 first-round pick or a salary above the highest minimum. The others start as free agents in the market's pool.

## 10-day contracts from January 20, 2004

The first rule signed a 10-day whenever one regular was injured: 20 in the first 14 days, about 2.5 times the real 2003-04 rate (about 60 from January 5 to the season's end). From January 20 a 10-day is an emergency fill: a club signs one only when its healthy players under contract fall below twelve (`NEED_RULE_FROM`). When a 10-day ends, a player who averaged `CONTRIBUTOR_MINUTES` (10, judgement) per club game is kept for the rest of the season; otherwise he gets a second 10-day only while the club is still short, or goes. Moves before January 20 stand.

## Calibration (against `nba_1999_in_season_rules.json`, calibration_2003_04)

These are volume targets only, never decisions.

| Measure | 2003-04 real | Dry run, December 3 to April 14 (no new games) |
| --- | ---: | ---: |
| Trades, December 3 to February 19 | 16 | 8 (two-a-week cap, 6% mutual gain) |
| 10-day contracts | about 60 | 62 |
| Waivers, regular season | 55 | 13 |

The dry run holds values and injuries fixed at December 1, so it understates trades: live form changes weekly and opens new deals. Waivers are low because the pool lacks the minor-league call-ups (CBA, NBDL) clubs churned through in 2003-04. Importing them needs researched records. Compare live volume after a month and adjust the constants prospectively.

## Shared valuation changes (live from December 1, 2003, for every club including Miami)

- **Current form.** A player's production is 2002-03 blended with his closed 2003-04 games (`trades.FORM_FROM`; each new game counts against 20 games of last season's).
- **Control after the contract.** A player 25 or younger is valued for two seasons beyond his contract, and one up to 29, through restricted free agency or Bird rights (`CONTROL_AFTER_CONTRACT`).
- **Injury discount.** See docs/front_office.md, Distressed assets.

## Known limits

- The real rosters place a traded player's stints by order and games, not by date, so the activation roster can hold both halves of a real trade (Toronto on December 1 has Donyell Marshall but not Jalen Rose).
- Phase 5 (draft, summer free agency for all clubs) is not built; it is needed before the 2004 offseason.
- The free-agent pool reads researched status snapshots (December 1, 2003 and the first of each month to April 1, 2004) and refuses a date more than 31 days past the newest.
