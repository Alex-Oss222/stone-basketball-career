# Symmetric league: design

Status: phases 1 and 2 built and switched off; phases 3 to 5 planned. The switch is the user's decision.

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
| 3. AI-to-AI trades | `trades.py` club objectives with both sides real clubs; salary matching; untouchables; floor; deadline February 19, 2004; one engine draw per side | planned |
| 4. Simulated rosters | `game_requests._club` reads each club's simulated roster; minutes from each player's real per-game role, renormalized to his new club's depth | planned |
| 5. Rollover | Draft for all clubs, summer free agency for all clubs, owner ceilings by market, calibration of league-wide transaction volume against 2002-04 history | planned |

## Activation

`runtime/league_book.SYMMETRIC_FROM = None`. Setting a date turns the league symmetric from that date. Played games keep their inputs. A date mid-season is allowed only after phases 3 and 4 are complete.

## Calibration targets (phase 5)

These are season-level observations from 2002-03 and 2003-04, used only as targets for volume, never as decisions:
- trades per season;
- in-season signings;
- waivers;
- 10-day contracts.
