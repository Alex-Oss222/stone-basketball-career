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
- the later 2003 head-coaching change before it occurs.
- final 2003-04 standings, statistics, awards or transactions.

A later source may be used to reconstruct a contract term that already existed, but not to reveal a future choice or result to the simulation.

`00_Team/Finances/league_cap_history.json` intentionally stores the real six-season cap sequence for continuity. Treat only a cap that has reached its season/publication gate as live front-office knowledge. Never use a future row to influence an earlier contract, trade or free-agency decision.

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

Official NBA weekly award windows can cross this repository's fixed calendar buckets. Preserve the official award dates and file the honor on the week page containing the award period's end date.

## League stats and awards

League-wide tracking lives under `career/Dwyane_Wade/Stats_and_Awards/League/`. The player registry is the source roster for league stat pages. Every period page keeps all tracked players grouped by primary position.

Weekly and monthly NBA awards remain conference-specific. Their pages keep a visible top-three shortlist but do not pretend the NBA published vote totals where it did not. Season individual awards publish the top three vote-getters. The No. 1 row is labeled WINNER only after the vote closes.

## Team stats

Miami-only player statistics live under `career/Dwyane_Wade/Stats_and_Awards/Team/`, using the same year → month → week structure as the other statistical records. Team pages contain only Miami players for that period.

Roster changes are historical: departures stay on completed earlier pages for their Miami games, and arrivals appear from their first applicable period onward.

## Game records

Game-note statuses are `scheduled`, `played`, or `not_played`.

Never create a blank game placeholder. Play-In Game 2 is conditional. Playoff Games 5, 6 and 7 are conditional.

Relay or another runner may simulate a game, but raw external output is not canonical until written into the correct career record.

## Game engine

Games are played by the engine on Railway. To play a game, write `Game_N.request.json` next to the scheduled `Game_N.md` (format in `runtime/game_requests.py`), validate, commit and push to the branch Railway tracks. Read the result from `/games/<event_id>/box` and write it into the game note; it is canonical only then. Never pass a seed, never resolve a game with the kernel directly, and never edit a played game's request to get a different result. Do not use a season's own final averages to calibrate it. See `runtime/README.md`.

## After an event

1. write the owning event note;
2. update current state;
3. update affected AI/GM team records only when Miami actually changed;
4. run repository validation;
5. run tests.
