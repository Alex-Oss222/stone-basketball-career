# Prior-season league shot locations

`library/2003/league/nba_2002_03_shot_environment.json` supplies a league spatial
prior for the 2003-04 simulation. It uses the completed **2002-03 NBA regular
season only**. It does not import historical Wade NBA production, replace an
individual's existing two-/three-point rates, or assert that a player's own
shot-location tendencies were observed.

The six source categories are distances of 0–3 feet, 3–10 feet, 10–16 feet,
16 feet to the three-point line, corner threes, and other threes. The first two
are distance bands; neither is a measured restricted-area or paint category.
Reporting can classify the engine's simulated coordinates into physical court
zones, but those classifications do not change what the source measured.

## Sources and reproduction

Basketball-Reference's [2002-03 player shooting table](https://www.basketball-reference.com/leagues/NBA_2003_shooting.html)
is available through the same `sumitrodatta/nba-alt-awards` mirror used by the
repository's other historical imports. The bytes actually retrieved and
verified for this import are pinned at revision
`7f9b3375439b79cb4e62f66ae7d12160275c2863`:

| Table | Pinned source | SHA-256 of complete downloaded source |
| --- | --- | --- |
| Shooting | [Player Shooting.csv](https://raw.githubusercontent.com/sumitrodatta/nba-alt-awards/7f9b3375439b79cb4e62f66ae7d12160275c2863/2025/Data/Player%20Shooting.csv) | `e7d16e3a1bc2fcb9bb07ee89310b438f27e12b25afa53f4e22c67c739ec08c5f` |
| Totals | [Player Totals.csv](https://raw.githubusercontent.com/sumitrodatta/nba-alt-awards/7f9b3375439b79cb4e62f66ae7d12160275c2863/2025/Data/Player%20Totals.csv) | `3406548a8be421dfd248edceb7efa8a7eba02aaf5eae26d1121e7f2484068cea` |

Retrieved October 3, 2026. The upstream path says `2025`; the importer keeps
only rows with `season=2003` and `lg=NBA`. Later seasons are excluded from the
checked-in snapshots and from every calculation. The original field values,
column order and row order are retained, with UTF-8 and LF line endings.

| Retained snapshot | SHA-256 |
| --- | --- |
| `library/2003/league/sources/nba_2002_03_player_shooting.csv` | `fae8dcc21e67302e0b112d993efdceabfe6cb576ef7620b36d41a345b69d579b` |
| `library/2003/league/sources/nba_2002_03_player_totals.csv` | `2971a07163924f75133d9c2daa16ffa040f12a07cad1329bbe35c3d7cfe88ae5` |

`python scripts/import_shot_environment.py --check` verifies snapshot hashes
and reconstructs the JSON without network access or writes. `--write`
regenerates the JSON from the verified snapshots. `--fetch --write`
redownloads both pinned sources with normal TLS verification, verifies their
complete hashes, filters the season, verifies both snapshot hashes, and then
writes the snapshots and JSON. A mismatched hash is an error; the importer
does not replace the expected hash or silently accept changed data.

Each snapshot contains 483 rows representing 428 players. For the 27 traded
players, a single `TOT` row replaces the individual team stints. Shooting and
totals must agree on player, player ID, season, season ID, team label and
league. The resulting exact aggregate box totals are 192,109 FGA, 84,937 FGM,
157,197 2PA, 72,737 2PM, 34,912 3PA and 12,200 3PM.

## What the estimates mean

The source supplies rounded attempt shares and shooting percentages rather
than exact integer counts for each spatial category. The importer therefore
records **estimated** attempts and makes:

- Distance-band attempts = player FGA × the source's band share; makes = those
  estimated attempts × the source's band FG percentage.
- Corner-three attempts = player 3PA × the source's corner share; makes =
  those estimated attempts × corner FG percentage.
- Other-three attempts and makes = exact player 3PA and 3PM minus the corner
  estimates. This residual includes non-corner heaves in the source.

The four two-point categories reconstruct 157,188.488 attempts, 8.512 fewer
than the exact box total because the source shares are rounded. This residual
is disclosed in the JSON. Attempt weights are normalized separately within
two-pointers and three-pointers. Zone FG percentages are weighted by their
estimated attempts, rather than averaging percentages across players.

The engine should keep the player's existing probability of taking a two or
three and the player's aggregate accuracy for that value. The JSON's
`two_point_fg_pct` is the weighted reconstructed zone baseline; its
`three_point_fg_pct` matches the exact league three-point total. Relative zone
effects can therefore be centered on these baselines without the rounded
source data introducing a second, unintended aggregate shooting boost.
Missing player location profiles use the **league prior conditioned on that
player's current two-/three-point rates**, including Wade. They are not labeled
player-specific measured spatial ability.

The `published_after: 2003-04-16` field uses the same completed-prior-season
availability gate as `nba_2002_03_league_environment.json`. It denotes the
engine's restriction to a completed regular season. It is not an assertion
that these retrospectively retrieved CSV files were published on that day.

## Geometry is a separate modeling assumption

The source has no individual coordinates, left/right preference, within-band
radial distribution or exact shot type. The suggested coordinate sampler uses
area-uniform radius and a uniform front-half angle for two-point bands, with
court and three-point-line rejection; corner threes use legal corner strips;
other threes use a 23.75–28-foot arc with court and corner rejection. These
distributions and the 28-foot cutoff are provisional structural assumptions.
They do not reconstruct deep heaves or claim empirical fine-location precision.

The source's corner-three label maps to the court's straight three-point-line
regions. Individual coordinates are unavailable to independently verify that
mapping at the boundary. Every generated coordinate must remain explicitly
identified as simulated. Existing games without shot events retain missing
location coverage; this prior provides no basis for backfilling them.
