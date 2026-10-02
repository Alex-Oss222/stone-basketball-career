# Agent operating rules

This is a player-career simulation centered on Dwyane Wade.

## Authority

The user controls Wade's legitimate player decisions.

The AI/GM controls Miami's organization, roster construction, cap accounting, contracts offered by the club, depth chart, rotation, tactics, staff decisions and transactions. The user can react to those decisions as Wade but cannot directly author them.

## Current checkpoint

- Date: June 26, 2003
- Event: 2003 NBA Draft
- Team: Miami Heat
- Selection: No. 5 overall
- Contract state: Miami owns Wade's draft rights; he is not yet signed.
- Head coach: Erik Spoelstra, promoted from Miami's staff at the start of the career (a premise chosen by the user); Pat Riley remains president.

Do not import a later 2003 event before the career clock reaches it.

## Read order

1. `career/Dwyane_Wade/Dwyane_Wade_Player_Profile.md`
2. `career/Dwyane_Wade/2003-04/current_state.json`
3. `career/Dwyane_Wade/2003-04/00_Team/Organization/README.md`
4. `career/Dwyane_Wade/2003-04/00_Team/team_config.json`
5. roster and depth chart
6. player cards needed for the current event
7. finances only when contract, cap or transaction consequences matter
8. current phase/week/game note

## Team state

Everything under `00_Team` is simulation-owned.

Organization files record basketball decision makers only. Business-side staff are excluded unless a future basketball event actually requires them.

Roster means the current team-control register at the stated date. Expiring contracts, pending options, draft rights and unavailable players must be labeled rather than silently treated as guaranteed active players.

Depth chart is a working basketball view, not a user choice and not a promise of minutes. At the June 26 checkpoint it carries the just-completed 2002-03 positional order and leaves the two new draft picks unassigned until the coaching staff makes a new decision.

## No hindsight

Do not import:
- Anthony Carter's June 30 option outcome before June 30.
- June 30 team-option, qualifying-offer or waiver decisions before June 30.
- July free-agent signings before their dates.
- Miami's real later 2003 head-coaching change: it does not apply, because Spoelstra is head coach by the user's premise and Miami's coach changes only by a simulated decision.
- final 2003-04 standings, statistics, awards or transactions.

A later source may be used to reconstruct a contract term that already existed, but not to reveal a future choice or result to the simulation.

### Talent-trajectory exception (option C, chosen by the user)

Real players' on-court ability may follow their real careers. The engine may read a real player's season rates and defensive rating (DBPM) from `library/careers/nba_player_careers.json` as his expected ability for that season, with a development swing drawn by the engine around it (`runtime/trajectories.py`). From the second simulated season on, 20% of his last simulated season's surprise against that expectation, shrunk by sample and capped at one season's swing spread, carries into his next expected season; it reads closed simulated results only and is written at rollover. This exception covers ability rates only, and only inside the engine:

- never results, standings, statistics totals, awards, injuries, suspensions, contracts, trades, signings, coaching changes or any team decision;
- never shown on player cards, scouting notes or anything the AI/GM or the user reads before the season is played; cards keep using evidence available on their date;
- never applied to Wade, whose career is alternate history.

Every season's development swing is journaled by the engine like a game draw and cannot be chosen or re-rolled.

Wade's ability: his rookie season uses the college estimate (`runtime/prospects.py`) plus the engine's swing for that season. Each later season's expectation comes only from his previous expectation, his simulated season from closed game results, and a generic age step (`runtime/protagonist.py`), followed by a fresh engine swing. Never use the historical Wade's statistics, and never tune the age steps or translation factors to steer his results.

`00_Team/Finances/league_cap_history.json` intentionally stores the real eight-season cap sequence, 2003-04 through 2010-11, for continuity. Treat only a cap that has reached its verified publication/activation gate as live front-office knowledge; a missing publication date blocks live use. Never use a future row to influence an earlier contract, trade or free-agency decision. The cap sheet projects existing obligations only. Keep signed salary, draft holds, conditional options and unresolved charges distinct; a zero scheduled commitment is not a zero-cost future roster or usable cap room.

## World model: real league, simulated Miami (option D, chosen by the user)

- The 28 other clubs follow real history season by season: real rosters and real minute shares from `library/<year>/league/nba_<season>_team_rosters.json`. They have no simulated front office.
- Miami is fully simulated by the AI/GM. Real transactions involving Miami are never applied.
- Conflict rules, applied in this order:
  1. A real transaction that involves Miami is skipped. Every player in it stays with the club that had him before the transaction. A free agent real Miami signed goes back to the club he last played for (chosen by the user), unless simulated Miami signs him; a player with no previous NBA club stays a free agent.
  2. A player simulated Miami acquires leaves his real club from that date. A player simulated Miami holds stays with Miami even if history moved him elsewhere.
  3. When rule 1 or 2 changes a real club's roster, the departing players' real minutes go to the arriving players up to their own previous minute share, and any remainder is spread over the club's rotation in proportion to real minutes. When the arriving players' previous shares are larger than the departing minutes, the difference comes out of the club's rotation in the same proportion.
- A real club's game input is its real roster on the game's date (`runtime/rotations.py`): each player's minutes per game played and the share of the club's games he played. A traded player is with each club for his stint's part of the season, placed from the order of his stints and his games played, never from transaction dates or results. A stint begun by a real Miami transaction is skipped at import and a player real Miami brought in between seasons is back on his previous club with his previous season's minutes (rule 1); players on simulated Miami's register are taken out of real clubs (rule 2). The engine draws availability per game.
- If Wade joins another club, that club becomes the simulated club from that date with its own career folder; earlier folders stay as history.
- Real rosters are hindsight about other clubs, accepted by the user for the world only. They never decide what simulated Miami knows or plans: the AI/GM sees other clubs only as they stand on the current career date.

## Wade's voice in the front office

Wade may tell Miami's front office what he wants: a trade he opposes or wants, a free agent to pursue, his role or minutes. Each request is logged with its date in the phase note it belongs to. The AI/GM weighs it and decides; a request never forces a decision. The weight grows with Wade's standing at that date (his simulated production, awards and contract status), and a front office can say no. Where the answer depends on chance, the engine draws it like a game result so it cannot be re-rolled. Decisions that went against Wade's request may affect his later choices, such as free agency, but only through his own decisions. Request format, standing weights and the front office's rules: `docs/front_office.md`.

## League source data

League-wide historical data belongs under `library/<year>/league/`, not inside a player's season root or Miami's `00_Team`.

For the 2003 cycle:
- `library/2003/league/nba_2003_end_of_season.json` is the end-of-2002-03 league roster/depth baseline.
- `library/2003/league/nba_2003_draft_class.json` is the June 26, 2003 post-draft rights snapshot.

Use those files as source evidence for opponents, league rosters, player identity, depth baselines and image metadata. Derive Miami's current state from them when appropriate, but do not copy the entire league dataset into the career folder.

## Player cards

Every player in the team-control register has a player card.

Cards are personnel records, not automatic game-engine ratings. Objective identity, contract/control and prior production may be entered when sourced. Subjective grades remain `Unassessed` until the simulation has an evidence basis.

The 2003 veteran import adds a separate statistical estimate layer, documented in `docs/statistical_ratings.md`. The engine reads generated prior-season rates by `bbr_id`; the cards display 20–80 descriptive grades with observed evidence and sample sizes. Do not copy those grades into legacy engine ratings, infer overall defense from steals/blocks, or infer rim/midrange splits without shot-location data. Rebuild and check with `scripts/import_veteran_stats.py`; keep raw statistics in `library/2003/league`. Incoming draft-class cards are outside this import. Regular-season history, playoff history and awards must remain the final three card sections, with awards last.

User-supplied player photos can be linked later. Do not invent image URLs.

## Stats and awards

The player's statistical record lives at `career/Dwyane_Wade/Stats_and_Awards/<season>/`, then month, then week.

Closed game results are the evidence. Week pages summarize their games, month pages summarize the completed weeks, and the year page summarizes the months. Never import real-world Wade statistics or awards as branch results.

Keep the existing paths and the cross-links between the same period's Wade, Miami, league-player and award records. Production tables use labeled per-game columns; shooting/possession detail uses totals. Recompute percentages from summed makes and attempts, not averages of percentages. G = 0 is an empty appearance record; missing feed coverage is not zero. Preserve source-game links and separate playoff totals.

Player reports contain professional identity and statistics. Rebuild with `python scripts/update_player_reports.py`; verify without writes with `--check`. Detailed tables live in `Stat_Detail.md`, and each regular-season month/week has a readable README. Maintain dated status snapshots in `professional_identity.json`; the detailed alternate-history profile remains canon. A played note may point to an adjacent `Game_N.result.json` via `result_file`. Only that declared, closed result feeds reports. The reporter does not run the engine, advance time or invent tracking data. See `docs/player_statistics.md` for the source contract and formulas.

Use the shared personal-information header and complete per-game columns across player report levels. Generated gold award badges read `awards.json`: earned honors only, with dates and an existing career decision source. Keep the existing honor and league voting records synchronized when recording an award. The banner is bounded by the page's identity cutoff; table honors are confirmed through the career knowledge date and filed by award period end. Never copy the reference images' biography, trophies or historical totals into the simulation.

Summer League, preseason, regular season, Play-In, playoffs and national-team events are distinct statistical records. National qualifiers, final tournaments and friendlies stay separate. NBA Cup applies only from 2023-24: group, quarterfinal and semifinal games remain owned by regular-season weeks and are tagged for the Cup view; only the championship is owned by `10_NBA_Cup/Championship`. Never duplicate a game to populate a second report. Play-In is unavailable before 2019-20; that restart format differs from 2020-21 onward. Reporting support never enables an unverified engine era. Examples under `docs/examples/` are illustrative and must not enter canonical career totals.

Official NBA weekly award windows can cross this repository's fixed calendar buckets. Preserve the official award dates and file the honor on the week page containing the award period's end date.

## League stats and awards

League-wide tracking lives under `career/Dwyane_Wade/Stats_and_Awards/League/`. The player registry is the source roster for league stat pages. Every period page keeps all tracked players grouped by primary position.

League season/month/week tables share the full per-game column order and red-and-black section styling. Include recorded age, club/rights, league and position without assigning a player banner to a league page. `scripts/format_league_reports.py` migrates presentation while retaining period values; it is not a result aggregator. New unavailable fields stay N/A, and historical rating data must never fill simulated production.

Weekly and monthly NBA awards remain conference-specific. Their pages keep a visible top-three shortlist but do not pretend the NBA published vote totals where it did not. Season individual awards publish the top three vote-getters. The No. 1 row is labeled WINNER only after the vote closes.

Weekly/monthly shortlist tables use evidence and result columns, not first-place-vote or points columns. Season voting records retain the electorate, scoring rule, close date and complete tally reference. Keep all 407 registry entries accessible by position; a source club or draft-rights label does not establish current active status.

## Team stats

Miami-only player statistics live under `career/Dwyane_Wade/Stats_and_Awards/Team/`, using the same year → month → week structure as the other statistical records. Team pages contain only Miami players for that period.

Roster changes are historical: departures stay on completed earlier pages for their Miami games, and arrivals appear from their first applicable period onward.

## Game records

Game-note statuses are `scheduled`, `played`, or `not_played`.

Never create a blank game placeholder. Play-In Game 2 is conditional. Playoff Games 5, 6 and 7 are conditional.

Relay or another runner may simulate a game, but raw external output is not canonical until written into the correct career record.

## Game engine

Games are played by the engine on Railway. To play a game, write `Game_N.request.json` next to the scheduled `Game_N.md` (format in `runtime/game_requests.py`), validate, commit and push to the branch Railway tracks. Read the result from `/games/<event_id>/box` and write it into the game note; it is canonical only then. Never pass a seed, never resolve a game with the kernel directly, and never edit a played game's request to get a different result. Do not use a season's own final averages to calibrate it. The engine's defense, rotation, late-game, foul-trouble and score-effect model and its calibration record are in `docs/engine_model.md`. League environment policy (chosen by the user): each season is calibrated on the **real** league averages of the season before it, stored as `library/<year>/league/nba_<YYYY>_<YY>_league_environment.json`, not on the simulated league's averages. These describe the era's style of play, not any team's results. See `runtime/README.md`.

## Build roadmap

`docs/ROADMAP.md` lists what still has to be built, in career-clock order. Check it before advancing the clock past an item's deadline, and update an item's status in the same change that completes it.

## After an event

1. write the owning event note;
2. update current state;
3. update affected AI/GM team records only when Miami actually changed;
4. run repository validation;
5. run tests.
