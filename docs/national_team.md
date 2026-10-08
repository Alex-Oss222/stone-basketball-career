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
| Medals | `runtime/national_medals.py` | The medal register of a closed tournament: the team's medal for every player on a medal team's locked roster, its readers and its validation. |
| Pages | `runtime/national_pages.py` | `career/Dwyane_Wade/FIBA/README.md` and one page per tournament, with the final ranking and each medal team's roster. Wade's own national statistics go on his `National_Team` pages through `scripts/update_player_reports.py`. |
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
6. **Close.** After the last game (`closed`, `closed_on`, `ranking` and `medal_identities` in the tournament record):
   - **Final ranking:** medal and classification games first, then second-round and group places.
   - **MVP and All-Tournament Team:** Game Score per game times the team's finish (1.0, 0.85, 0.75 for the medallists, 0.6 for the rest), with at least three games.
   - **Medals:** the medal register (below) for every player on the top three teams' locked rosters.
   - **Wade's honors and medal** go to `awards.json`.
   - **Selection snapshot:** a selected Wade gets a dated snapshot in `professional_identity.json`.

## Medals

The user's rule (2005 offseason framework, section 6), in `runtime/national_medals.py` for every simulated edition, with no user step:

- **Places.** Once the tournament is closed and its final ranking is canonical, 1st place wins gold, 2nd silver and 3rd bronze. 4th place and below win no medal.
- **Who receives one.** Every player on that team's locked roster for the tournament (locked the day before the first game) receives the medal, including a roster member who played no minutes. A player who was never selected, withdrew before the lock or is not on that roster receives none.
- **Separate awards.** A medal never implies the MVP or the All-Tournament Team, which stay the tournament's performance awards.
- **The register.** `FIBA/<family>/<edition>/medals.json`, beside the tournament record, written at the close by `national.after_games`. It is derived from the closed record and its frozen identities: a rebuild (`python scripts/national_day.py --medals`) writes the same file, so a medal is never duplicated. That command also freezes the identities of a closed record that lacks them, resolved on its close day. Each medal has:
  - a stable id, `<edition_id>-<country slug>-<bbr_id or FIBA identity>-<medal>`;
  - the player's name, NBA id where he has one, FIBA identity and country;
  - the tournament, edition and the team's final place;
  - the award date, the day the tournament closed;
  - the source result: the final for gold and silver, the third-place game for bronze, or the record's ranking when no single game decided the place;
  - the games he played in the tournament, as evidence only.
- **Identity.** The order is:
  1. the locked roster's NBA id (an NBA player with a season behind him on the date);
  2. the researched roster's id, when the league player registry already tracks him;
  3. the registry's one player with the same name and birth date;
  4. otherwise no NBA id.

  The registry is read as the league knew it on the close: its original rows and the rows added on or before that day (`added_on`).
  The identities are resolved once, at the close, and frozen into the tournament record (`medal_identities`). Every rebuild reads them from there, so a registry row added or repaired later (a medallist's later NBA debut, `write_back.extend_registry` and `repair_registry`) never renames a medal or changes its id.
  The NBA nationality file never names a player here: it lists NBA careers through 2007-08, later than the clock.
- **Where medals show.**
  - The tournament page: the final ranking and each medal team's locked roster, with any player who did not play marked.
  - The league player card's awards section, for a registry player matched by NBA id.
  - A followed player's career honors (`runtime/followed_players.py`).
  - Wade's medal stays in `awards.json` exactly as before (`national.record_wade_honors`, id `<edition_id>-<medal>`).
- **Readers.** `national_medals.medals_for(bbr_id or name, on=date)` and `register_medals(on=date)` return medals awarded on or before the date. None appears before its tournament closed.
- **Validation** (`national_errors`):
  - A closed edition needs a complete register equal to a fresh build.
  - A medal for a player not on the team's locked roster is an error, and so is a medal for a team placed 4th or lower.
  - A register before the close, or a medal dated before the close or after the clock, is an error.
  - A closed record needs its frozen identities: exactly the medal teams, one per locked player in locked order, each keeping the locked roster's NBA id and FIBA key. Identities frozen before the close are an error.
  - Wade's register medal must also be in `awards.json`, and a Wade medal in `awards.json` (`<edition_id>-gold`, `-silver` or `-bronze`) must be his medal in the register.

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
- **USA's 2006 place (the user's decision, 2005-06-16):** the 2006 World Championship's Americas places, the USA's included, come only from the simulated 2005 FIBA Americas, where the USA plays its real non-NBA roster, and the existing slot and wildcard rules. No place, spot or medal is assigned in advance and no real result overrides the simulation.

## Editions

| Edition | Status |
| --- | --- |
| 2005 FIBA Americas Championship (Santo Domingo) | built; USA plays its real (non-NBA) roster |
| 2006 FIBA World Championship (Japan) | built; Americas places from the simulated 2005 Americas; USA by committee |
| 2007 FIBA Americas, 2008 Olympic qualifying tournament, 2008 Olympics | researched; pending the 2006 World Championship and 2007 continental player statistics (roadmap N1) |
| 2010, 2011, 2012, 2014 | format and calendar researched; rosters pending (roadmap N1) |
