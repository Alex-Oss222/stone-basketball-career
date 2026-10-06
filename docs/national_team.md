# National-team tournaments (FIBA)

The user's premises, December 31, 2004 on the career clock (`career/Dwyane_Wade/National_Team/wade_standing_rule.json`):

- **USA roster: simulated committee.** USA Basketball ranks every USA-eligible NBA player by his closed simulated season and picks twelve with positional needs; the same rule applies to every player, Wade included.
- **Scope: every game.** The engine plays every game of every tournament the pipeline runs, under FIBA rules.
- **Invitations: standing rule.** Wade accepts every invitation unless he is injured, so no invitation stops the clock.
- **Athens 2004: not played.** The 2004 Olympic tournament passed before the pipeline existed. It has no record.

## The parts

| Part | File | What it does |
| --- | --- | --- |
| Research | `library/<year>/fiba/*.json`, `library/fiba/` | Each edition's format, calendar, schedule (knockout games as bracket slots, never as teams), the real rosters, the qualification rules, the per-player statistics of past tournaments, the FIBA rules and the nationality of NBA players. No result of a simulated event is stored. |
| Editions | `runtime/fiba_editions.py`, `scripts/build_fiba_engine.py` | Researched files normalized into one form, plus the engine layers, written to `library/fiba/engine/<edition id>.json`. |
| Engine | `runtime/era.py`, `runtime/kernel.py`, `runtime/game_runner.py`, `runtime/national_engine.py`, `runtime/shot_chart.py` | FIBA rules by date, the FIBA court, the FIBA environment and every player's FIBA profile. NBA games are unchanged and replay identically. |
| Tournament | `runtime/fiba_tournament.py`, `runtime/national.py` | Field, USA selection, roster lock, coach's rotation, game requests, FIBA standings and tiebreaks, carry-over groups, bracket, final ranking, honors. |
| Pages | `runtime/national_pages.py` | `career/Dwyane_Wade/FIBA/README.md` and one page per tournament. Wade's own national statistics go on his `National_Team` pages through `scripts/update_player_reports.py`. |
| Driver | `scripts/national_day.py`, `scripts/advance.py` | Runs every day in the summer, in training camp and in the season. |

## How a tournament runs

1. **Field.** The record opens on the selection date, which defaults to 30 days before the first game. Places earned in an earlier simulated edition (`qualification` in `CONFIG`) are filled from that edition's final ranking:
   - The k-th simulated qualifier takes the k-th real qualifier's group slot. The real team only names the slot.
   - A wildcard stays with its real recipient unless that team qualified on court. In that case it passes to the best-placed team from the same event that did not qualify.
   - A team with no real roster for the edition plays its latest real roster.
   - Zones the simulation does not play keep their real qualifiers.
2. **USA selection** (`committee`), for an edition with the USA in its field:
   - **Score:** the closed-season Game Score per game, times min(1, games/70), plus an honors bonus (MVP 4, All-NBA 3, 2 or 1.5, All-Star 1).
   - **Eligibility:** `library/fiba/nba_player_nationality.json`. Players on another country's real roster are excluded.
   - **Invitation order:** the best players are invited by positional need first (four guards, four forwards, two centers), then the best remaining.
   - **Answers:** each invitee's answer is an engine draw (accept 0.7). Wade answers by his standing rule. Invitations continue until twelve accept.
   - **2005 FIBA Americas Championship:** the USA plays its real roster. USA Basketball sent no NBA players that summer.
3. **Roster lock**, the day before the first game:
   - **Player type:** a player with a season profile for the ability season plays on his translated NBA profile. Everyone else plays on his FIBA profile.
   - **Coach's trust:** production, measured as Game Score per 40 minutes. For an NBA player it comes from his closed simulated season, discounted below 24 minutes a game. For a FIBA player it comes from his past tournaments, discounted below 20 minutes, and is 0 with no record.
   - **Minutes:** the rotation gives 32, 30, 28, 26, 24, 20, 16, 10, 6, 4, 2 and 2 minutes by rank.
4. **Games.** Each game day's requests are written once both teams are known, with frozen inputs.
   - **Venue:** neutral, except the host's games.
   - **Paths:** Wade's games go beside his notes under `National_Team/<family>/<edition>/<stage>/<round>/`. Every other game goes under `FIBA/<family>/<edition>/Games/`.
   - **Play:** the engine plays them exactly like NBA games: journaled, never re-rolled.
5. **Standings and bracket.** Group tables follow the edition's rule book (`fiba_2004` until 2010):
   - 2 points for a win and 1 for a loss.
   - Ties are broken among the tied teams first, by points and then goal average.
   - Any tie still level is settled by one engine draw.
   - Second rounds that carry over earlier results (the Americas championships) are supported.
   - Knockout slots fill from the tables and from game winners and losers.
6. **Close.** After the last game:
   - **Final ranking:** medal and classification games first, then second-round and group places.
   - **MVP and All-Tournament Team:** Game Score per game times the team's finish (1.0, 0.85, 0.75 for the medallists, 0.6 for the rest), with at least three games.
   - **Wade's honors and medal** go to `awards.json`.
   - **Selection snapshot:** a selected Wade gets a dated snapshot in `professional_identity.json`.

## Ability in a FIBA game

- **Rules.** The kernel takes game length, fouls and the three-point line from `era.national_rules(date)`:
  - four 10-minute quarters, five-minute overtimes, a 24-second clock and five fouls;
  - 6.25 m until September 30, 2010, then 6.75 m.
  - Minute caps scale with game length. Shots are drawn on the FIBA court of the date.
- **Calibration.** Each edition uses the real per-game averages of the last senior FIBA tournament published before it (the repository's environment policy). The FIBA statistics service supplies the team totals. Player-rate baselines come from that tournament's players.
- **NBA players.** The NBA expectation for the ability season is the season just closed for a summer event. It gets the player's journaled development swing, then a translation fitted on anchors: players with an NBA season and the FIBA tournament after it, all before the edition.
  - **Two- and three-point percentages:** a logit shift.
  - **Every other rate:** a ratio.
  - Both are shrunk toward no change by the anchors' sample. Defense keeps the player's DBPM.
- **Other players.** Their real statistics in senior FIBA tournaments are used.
  - **Recency:** tournaments in the 15 months before the edition count in full. Older ones within three years count at half weight.
  - **Shrinkage:** rates are shrunk toward a prior one point below the tournament's average shooting, with usage, assist, rebound, steal and block rates at 95% of average.
  - **Defense:** a fifth of his team's defensive margin per 100 possessions, shrunk by games.
  - **Partial records:** FIBA Asia 2003 and 2005 hold free throws only, so other rates use the prior.
- **Calibration check** (scratch run of the 2005 Americas, never canonical):
  - **Simulated:** 79.1 points per team-game at 44.5% shooting, against a target of 79.5.
  - **Real event:** 83.3 points at 44.3% shooting. It played faster than the 2004 Olympic baseline.

## Judgements and limits

- **Rotation:** the minutes template and the coach's trust rule. Ranking by minutes was tried first and dropped: on an all-star USA roster everyone played heavy NBA minutes, and the order was arbitrary.
- **Committee:** the score, quotas and acceptance chance.
- **Prior:** the prior level for players without records.
- **Finish weights:** the multipliers used for the honors.
- **Opponent totals:** the tournament's average team stands in for each player's opponents in his rate formulas.
- **Injuries:** national games draw no injuries, as with every club but Miami. The injury pause also applies.
- **Fouled-out teams:** a team that runs out of eligible players keeps its last five, the NBA engine's rule.

## Editions

| Edition | Status |
| --- | --- |
| 2005 FIBA Americas Championship (Santo Domingo) | built; USA plays its real (non-NBA) roster |
| 2006 FIBA World Championship (Japan) | built; Americas places from the simulated 2005 Americas; USA by committee |
| 2007 FIBA Americas, 2008 Olympic qualifying tournament, 2008 Olympics | researched; pending the 2006 World Championship and 2007 continental player statistics (roadmap N1) |
| 2010, 2011, 2012, 2014 | format and calendar researched; rosters pending (roadmap N1) |
