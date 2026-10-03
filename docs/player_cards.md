# League player cards

[League record guide](../career/Dwyane_Wade/Stats_and_Awards/League/README.md) · [Card index](../career/Dwyane_Wade/Stats_and_Awards/League/Players/README.md) · [Player statistics](player_statistics.md) · [Statistical ratings](statistical_ratings.md)

Every one of the 407 players in the league player registry (`career/Dwyane_Wade/Stats_and_Awards/League/player_registry.json`) has a dated personnel card under `career/Dwyane_Wade/Stats_and_Awards/League/Players/`: `<registry_id>.md`, which renders on GitHub, and `<registry_id>.html`, the interactive detailed card. The registry id is the player's Basketball-Reference id. Every Player cell on the league statistics pages (season, month and week) links to the Markdown card. Miami's players also link from their league card to their Miami card under `00_Team/Team/Player_Cards/`; Wade's links to his career page. The Miami cards themselves are untouched by this build.

## What a card shows

A card shows only evidence dated on or before its date, which is the career clock (`current_state.json`, June 26, 2003 at the opening checkpoint). It never shows later-career facts, real 2003-04 statistics or the historical Wade's statistics.

| Section | Content | Source |
| --- | --- | --- |
| Header image | Club-colour SVG with name, jersey, position and the club holding the player on the card date | `assets/<registry_id>_header.svg`, built from the colour file below |
| Photo | Sourced headshot with credit and licence, or the shared neutral silhouette (`assets/silhouette.svg`) | `headshot_*` fields of `library/2003/league/nba_2003_end_of_season.json`, then `nba_2003_draft_class.json`; a photo URL is never invented |
| Identity | Position, jersey, birth date, age on the card date, registry id, Basketball-Reference page, ESPN id; Wade's measurements and prior program come from his career profile | Registry and the baseline roster entry; `professional_identity.json` for Wade |
| Contract/control | Terms that already existed at the checkpoint, or the unsigned draft rights and their pick | `library/2003/league/nba_2003_contracts.json` (status legend in that file) |
| Prior season | Recorded 2002-03 line, or the 2003 draft entry for the 58 rookies | `nba_2002_03_player_stats.json`; draft rights from the contract inventory |
| Simulated statistics | Season, month and week per-game tables in the repository's column order, N/A until closed games exist, never zero | Closed regular-season results written into the career record by the write-back (`runtime.write_back.closed_lines`: Miami's played notes and the league slate results, matched by bbr_id then name) |
| Shooting zones | Zone table from `runtime/shot_chart.py` (`aggregate_shots`) over closed results; coverage `unavailable` until located attempts exist | Closed results only; nothing is estimated onto the court |
| Regular-season statistics by year, Playoff statistics by year, Awards and honors | The same final three sections as the Miami cards, awards last | 2002-03 line; simulated 2003-04 rows; honors only from a closed award decision |

The interactive card embeds the same data as JSON in a copy of the preview's HTML/JS (`docs/templates/player_cards_preview.html`, adapted so its example-only wording comes from the data). It offers the period selectors, the shot chart (which says coverage is unavailable until located attempts exist) and the annual-awards view. GitHub shows an HTML file as source, so open it in a browser from a checkout; the Markdown card says so and links to it.

## Colours and the dated club

`library/2003/league/nba_team_colors_2002_2014.json` holds user-supplied club colours by era: a row covers the seasons whose starting year is at least `from_year` and under `to_year` (2003-04 uses 2003). Colours are presentation only.

A card's header uses the colours of the club holding the player on the card date, found by `runtime/league_cards.club_on(player, date)`:

1. the registry's source club (end of 2002-03) or 2003 draft rights;
2. the world's real moves in `nba_2003_offseason_transactions.json` up to the date, with rule 1 of `AGENTS.md`: a real move to Miami never happens and a trade involving Miami is skipped, so the player stays with his previous club; signings, sign-and-trades, declined matches, waivers and trades move a player; offer sheets, matches, re-signings and rookie signings do not;
3. Miami's departures ledger (`00_Team/Team/Roster/departures.json`, rule 3): a player Miami sent to a real club is that club's for the dates recorded;
4. Miami's holdings (`00_Team/Team/Roster/holdings.json`, rule 2): a player Miami holds on the date is Miami's, and a real move cannot take him away while he is held. A Miami player whose holding has ended with no later club is a free agent.

A free agent, and unsigned rights with no club, use the placeholder: white text on near-black (`#1d1d1f`) with grey (`#c5c7cb`) accents.

## Regeneration and checks

```
python scripts/build_league_cards.py --write   # regenerate every card from the dated records
python scripts/build_league_cards.py --check   # verify the cards on disk without writing
python scripts/format_league_reports.py        # relink the Player cells of every league page
```

The build is idempotent. Repository validation (`scripts/validate_repository.py`) requires a Markdown and an HTML card for every registry player, every league-page player link to resolve, the three final sections in order, and no photo URL outside the league baseline. Tests: `tests/test_league_cards.py`.

The cards are rebuilt when the clock, the holdings, the departures ledger or closed results change; `scripts/write_back_results.py --write` rebuilds them after writing results. They do not run the engine, advance time or decide anything.
