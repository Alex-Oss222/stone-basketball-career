# Season structure

The numbered folders are the main career areas.

| Area | Intended window | Notes |
|---|---|---|
| 01 Free Agency | June 30 to early July | Player market, contract offers, decisions, signings |
| 02 Summer League | July | Participation, games, evaluation, development |
| 03 Offseason | August to mid September | Individual training and player-life decisions |
| 04 Training Camp | Late September | Camp participation, role competition, team evaluation |
| 05 Preseason | Early to mid October | Preseason games and roster/role consequences |
| 06 Regular Season | Mid/late October to mid April | Month/week notes |
| 07 Play-In Tournament | After regular season | Game 1, then Game 2 only if required |
| 08 Playoffs | April to June | Four best-of-seven rounds |
| 09 Draft | Lottery/combine in May, draft in late June | Draft-related events for the next cycle |

The draft overlaps the postseason in real calendar time. Folder numbering is a navigation cycle, not a claim that every event in folder 09 occurs after every event in folder 08.

## Regular-season weeks

A month always uses four buckets:

- Week 1: days 1 to 7
- Week 2: days 8 to 14
- Week 3: days 15 to 21
- Week 4: days 22 to the final day of the month

Required regular-season note folders are:

- October: Weeks 3 and 4
- November: Weeks 1 to 4, with NBA Cup group-game tracking when applicable
- December: Weeks 1 to 4, with NBA Cup knockout tracking when applicable and a December 15 trade-eligibility marker
- January: Weeks 1 to 4, with the contract-guarantee marker in Week 2
- February: Weeks 1 to 4, with the trade-deadline marker in Week 1 and All-Star break marker in Week 3
- March: Weeks 1 to 4, with the playoff-eligibility waiver marker in Week 1
- April: Weeks 1 and 2, with the regular season ending in the middle of the month

These are structural markers from the requested template. When a specific NBA season is chosen, actual dates must be verified before use.

## Play-In

Create `Game_1.md` only when Game 1 is scheduled.

After Game 1 is played, set `next_game_required: true` only when the team's path requires a second play-in game. Only then may `Game_2.md` exist.

## Playoffs

Round folders:

- First Round
- Conference Semifinals
- Conference Finals
- Finals

Each is best of seven. Do not create empty game notes. Create a game note when the game is scheduled. Unused conditional Games 5 to 7 may be absent or explicitly marked `not_played`.

## Draft

Keep lottery, combine, interviews/workouts if later used, and the late-June draft in this area. Do not assume the player is draft-eligible until the career state establishes that.
