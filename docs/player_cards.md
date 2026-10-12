# League player cards

[League record guide](../career/Dwyane_Wade/Stats_and_Awards/League/README.md) · [Card index](../career/Dwyane_Wade/Stats_and_Awards/League/Players/README.md) · [Player statistics](player_statistics.md) · [Statistical ratings](statistical_ratings.md)

Every player in the league player registry (`career/Dwyane_Wade/Stats_and_Awards/League/player_registry.json`) has a dated personnel card under `career/Dwyane_Wade/Stats_and_Awards/League/Players/`: `<registry_id>.md`, which renders on GitHub, and `<registry_id>.html`, the interactive detailed card. The registry id is normally the player's Basketball-Reference id; a dated addition registered before his id was known keeps a name-based id, and every identity lookup on the card (jersey, baseline roster entry, photo, 2002-03 line) reads his `bbr_id`. Every Player cell on the league statistics pages (season, month and week) links to the Markdown card. Miami's players also link from their league card to their Miami card under `00_Team/Team/Player_Cards/`; Wade's links to his career page. The Miami cards themselves are untouched by this build.

## What a card shows

A card shows only evidence dated on or before its date, which is the career clock (`current_state.json`, June 26, 2003 at the opening checkpoint). It never shows later-career facts, real 2003-04 statistics or the historical Wade's statistics.

| Section | Content | Source |
| --- | --- | --- |
| Header image | Club-colour SVG with name, jersey, position and the club holding the player on the card date | `assets/<registry_id>_header.svg`, built from the colour file below |
| Photo | Sourced headshot with credit and licence, or the shared neutral silhouette (`assets/silhouette.svg`) | `headshot_*` fields of `library/2003/league/nba_2003_end_of_season.json`, then `nba_2003_draft_class.json`; a photo URL is never invented |
| Identity | Position, jersey, birth date, age on the card date, registry id, Basketball-Reference page, ESPN id; Wade's measurements and prior program come from his career profile | Registry and the baseline roster entry; `professional_identity.json` for Wade |
| Contract/control | Terms that already existed at the checkpoint, or the unsigned draft rights and their pick | `library/2003/league/nba_2003_contracts.json` (status legend in that file) |
| Prior season | Recorded 2002-03 line, or the 2003 draft entry for the 58 rookies | `nba_2002_03_player_stats.json`; draft rights from the contract inventory |
| Simulated statistics | Season, month and week per-game tables in the repository's column order, N/A until closed games exist, never zero. Each row reads as the League_Stats page it links to: Age on that page's label date (the period's end on the page, capped at the card date) and Team the clubs he appeared for in the period, in stint order and joined with "/", else his dated club on the label date (`league_cards.period_label`) | Closed regular-season results written into the career record by the write-back (`runtime.write_back.closed_lines`: Miami's played notes and the league slate results, matched by bbr_id then name) |
| Shooting zones | Zone table from `runtime/shot_chart.py` (`aggregate_shots`) over closed results; separate tracked-games cohort when old games have no locations | Validated prospective engine events, explicitly labeled simulated locations; no backfilled coordinates |
| Regular-season statistics by year, Playoff statistics by year, Awards and honors | The same final three sections as the Miami cards, awards last. Awards and honors also lists the player's FIBA team medals, with country and team place, linked to the tournament's medal table | 2002-03 line; simulated 2003-04 rows; honors only from a closed award decision; medals only from a closed tournament's medal register (`runtime/national_medals.py`), matched by NBA id, from the day it closed |

The interactive card embeds the same data as JSON in the shared live renderer (`runtime/assets/player_cards.html`). It offers period selectors, **All games / Tracked games only**, the shot chart and annual awards. A tracked cohort has its own appearance count, dates, boxes and source links. Full-period totals retain missing-location coverage for older games. Each closed engine result is validated once per build, then events are matched to their exact side/player identity through the existing registry mapping. GitHub shows HTML as source; use the live site or open the generated card in a browser.

## Colours and the dated club

`library/2003/league/nba_team_colors_2002_2014.json` holds user-supplied club colours by era: a row covers the seasons whose starting year is at least `from_year` and under `to_year` (2003-04 uses 2003). Colours are presentation only.

A card's header uses the colours of the club holding the player on the card date, found by `runtime/league_cards.club_on(player, date)`:

1. the registry's source club (end of 2002-03) or 2003 draft rights;
2. the world's real moves in `nba_2003_offseason_transactions.json` up to the date, with rule 1 of `AGENTS.md`: a real move to Miami never happens and a trade involving Miami is skipped, so the player stays with his previous club; signings, sign-and-trades, declined matches, waivers and trades move a player; offer sheets, matches, re-signings and rookie signings do not;
3. Miami's departures ledger (`00_Team/Team/Roster/departures.json`, rule 3): a player Miami sent to a real club is that club's for the dates recorded;
4. Miami's holdings (`00_Team/Team/Roster/holdings.json`, rule 2): a player Miami holds on the date is Miami's, and a real move cannot take him away while he is held. A Miami player whose holding has ended goes back to his real path: the club whose stint in the season's real roster file covers the date (the games' own roster rule), unless a real move dated after the release placed him; with neither, he is a free agent. A void holding (a camp contract that was never valid) is ignored.

From 2004-05 the dated club is `runtime/club_truth.holder`, the engine's own rosters (AGENTS.md, One club answer); the steps above are the 2003-04 rules.

A 2003 pick holds a contract, not rights, from the first dated evidence of it (`signed_evidence`): a signing in `career/Dwyane_Wade/Contracts/contract_records.json` from its date, or else the first closed game whose box score lists him on a club's roster (played, DNP or inactive). The world data does not record real clubs' rookie signing dates or terms, so the card says so. From 2004-05 the only record of a club's unsigned pick is Miami's: a holding recorded as draft rights, until the same evidence of a contract (`holds_rights`).

## The Club / rights cell of the league statistics pages

The design change of October 2026 (the user's decision after the June 2006 audit): the cell is a dated club, no longer the registry's frozen 2002-03 source label. For each row of a season, month or week page (`runtime/write_back.club_cell`, `league_cards.period_label`):

1. a player who appeared (played, not DNP) in the period's closed results shows the club or clubs he appeared for, in stint order, joined with "/" (`MIA/BOS`);
2. otherwise his club on the page's label date, the period's end or the career date while the period runs (`club_on`: the 2003-04 rules above, then `club_truth.holder`): its code, `<code> rights` only while that club holds his unsigned draft rights, `FA` when no club holds him;
3. a registry player the league had not reached on the label date (his registry `added_on` is later and no closed record of his is dated by then) shows `—` as club and league.

Codes are the 2003 baselines' (`league_cards.club_code`), and a later club takes its code from the season's real roster file (Charlotte Bobcats `CHA`, New Orleans/Oklahoma City Hornets `NOK`). The cards' period rows use the same rule, and a closed season's history row (`League/<season>/card_lines.json`) names the clubs of that season's appearances (`write_card_lines` at the close; the 2003-04 and 2004-05 files, written with the club on the close date, were rewritten to this rule by `repair_card_lines` in the June 2006 audit, every other cell as written).

A free agent, and unsigned rights with no club, use the placeholder: white text on near-black (`#1d1d1f`) with grey (`#c5c7cb`) accents.

## Regeneration and checks

```
python scripts/build_league_cards.py --write   # regenerate every card from the dated records
python scripts/build_league_cards.py --check   # verify the cards on disk without writing
python scripts/format_league_reports.py        # relink the Player cells of every league page
```

The build is idempotent. Repository validation (`scripts/validate_repository.py`) requires a Markdown and an HTML card for every registry player, every league-page player link to resolve, the three final sections in order, and no photo URL outside the league baseline. Tests: `tests/test_league_cards.py`.

The cards are rebuilt when the clock, the holdings, the departures ledger or closed results change; `scripts/write_back_results.py --write` rebuilds them after writing results. They do not run the engine, advance time or decide anything.
