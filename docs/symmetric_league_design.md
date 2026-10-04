# Symmetric league: design

Status: phases 1, 3 and 4 built and tested, switched off; phase 2 partly built; phase 5 planned. The switch is the user's decision.

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
| 2. League market | In-season free agents with researched availability, waivers, 10-day contracts from January 5 (1999 CBA), minimum and exception signings for every club | partly built: the pool and replacement signing (`club_replacements.py`) |
| 3. AI-to-AI trades | `runtime/league_trades.py`: weekly (Mondays) to the February 19, 2004 deadline, one-for-one swaps of rotation players both clubs gain at least 10% from on their own objectives. Values are stance weights, skill fit (symmetric), a 1.15 status-quo premium, the whole contract's burden by cash weight, current form and post-contract control. Legality is the 1999 salary rule. Untouchables stay. At most one deal a week, one engine decision packet each | built |
| 4. Simulated rosters | `runtime/league_moves.py`: each club starts from its real roster on the activation date. Real moves after it are not applied; `league_moves.json` moves apply from their dates; Miami's rules and the replacements apply on top. `game_requests._club`, `trades.dated_inventory` and the league desk all read it. Each player keeps his whole-season real role | built |
| 5. Rollover | Draft for all clubs, summer free agency for all clubs, owner ceilings by market, calibration of league-wide transaction volume against 2002-04 history | planned |

## Activation

`runtime/league_book.SYMMETRIC_FROM = None`. Setting a date turns the league symmetric from that date. Played games keep their inputs. A date mid-season is allowed only after phases 3 and 4 are complete.

## Calibration targets (phase 5)

These are season-level observations from 2002-03 and 2003-04, used only as targets for volume, never as decisions:
- trades per season;
- in-season signings;
- waivers;
- 10-day contracts.

## Shared valuation changes (live from December 1, 2003, for every club including Miami)

- **Current form.** A player's production is 2002-03 blended with his closed 2003-04 games (`trades.FORM_FROM`; each new game counts against 20 games of last season's).
- **Control after the contract.** A player 25 or younger is valued for two seasons beyond his contract, and one up to 29, through restricted free agency or Bird rights (`CONTROL_AFTER_CONTRACT`).
- **Injury discount.** See docs/front_office.md, Distressed assets.

## Known limits

- The real rosters place a traded player's stints by order and games, not by date, so the activation roster can hold both halves of a real trade (Toronto on December 1 has Donyell Marshall but not Jalen Rose).
- Phase 2 still lacks waivers, 10-day contracts and roster-minimum signings for every club. Phase 5 (draft, summer free agency for all clubs, calibration) is not built.
- The free-agent pool reads a researched status snapshot (`nba_2003_04_unsigned_status.json`, as of December 1, 2003) and refuses dates more than 30 days past it.
