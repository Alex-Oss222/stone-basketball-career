# nflverse_derived: estimated snap shares, 2010 to 2012

**These are estimates, not source snap counts.** Every estimated column ends in `_est`. Do not treat them as charted data and do not mix them with real counts without keeping the label.

- **Built:** 2026-10-02, by `scripts/research/build_snap_estimates.py` (run as `python build_snap_estimates.py <input folder> <output folder>`; it reads downloaded files only).
- **Football information window:** 2010 to 2014 only. Nothing from 2015 or later is read.
- **Cost and licence:** all inputs are free nflverse releases. No paid data.

## Why 2012 is included

`DATA_REQUEST.md` says public snap counts start in 2012. The nflverse `snap_counts_2012.csv` file has a header and no rows; real counts start in 2013 (already recorded in `library/2012_nfl_injury_calibration.md`). So 2012 needs an estimate too, and only 2013 and 2014 are available to fit on.

## Method

1. For every regular-season team-game, list each player on that week's nflverse depth chart, each player with a box-score line in that game, and each player on that week's nflverse weekly roster.
2. Inputs per player-game: whether the weekly roster marks him a gameday inactive (`status_description_abbr` beginning with `I`), his best listed offensive and defensive slot and string (1, 2, 3), how many players shared the first string in that slot, special-teams listings, the weeks before and after, his share of the team's targets, carries, pass attempts and tackles, sacks, QB hits, passes defended, interceptions, returns, kicks and punts, penalties, and his season-long averages of the same.
3. Target: his real offense, defense and special-teams snap share in 2013 and 2014 (nflverse `snap_counts`, from Pro Football Reference), zero when he did not play.
4. Three gradient-boosted regressions (offense, defense, special teams), fitted on 2013 and 2014 together, applied to 2010, 2011 and 2012. A player marked gameday inactive gets zero on all three; a box-score line overrides the inactive mark.
5. Team snaps per game are estimated from the box score: pass attempts plus sacks plus carries, scaled to real team snaps on 2013 and 2014 (offense: x 1.0210 + 1.42, mean error 1.45 snaps; defense uses the opponent's plays, mean error 1.61). Estimated snaps are share times estimated team snaps.

## Out-of-sample test

Fitted on one season and tested on the other, both directions.

| Test | Fit 2013, test 2014 | Fit 2014, test 2013 |
|---|---:|---:|
| Player-games | 27144 | 27538 |
| Mean error per game, offense share (points) | 4.22 | 4.24 |
| Mean error per game, defense share (points) | 4.99 | 4.95 |
| Mean error per game, special-teams share (points) | 10.54 | 10.37 |
| Same, using only slot and string (offense / defense) | 8.41 / 9.64 | 8.88 / 10.08 |
| Season totals: correlation with real snaps | 0.9834 | 0.9834 |
| Season totals: mean error (snaps) | 37.4 | 38.6 |
| Players with 200+ real snaps | 1134 | 1072 |
| Their median error | 8.5% | 8.2% |
| Share of them within 15% | 65.9% | 66.5% |

Season totals by position group, players with 200+ real snaps, fit 2013 and test 2014:

| Group | Players | Median error | Within 15% |
|---|---:|---:|---:|
| CB | 124 | 8.0% | 71.8% |
| DL | 202 | 14.8% | 50.5% |
| LB | 159 | 11.4% | 57.9% |
| OL | 219 | 4.7% | 77.6% |
| QB | 42 | 1.4% | 90.5% |
| RB | 67 | 11.8% | 67.2% |
| S | 98 | 6.4% | 74.5% |
| TE | 75 | 13.6% | 54.7% |
| WR | 125 | 7.4% | 71.2% |

The same table for the other direction, and everything above, is in `snap_estimates_validation.json`.

## Known weaknesses

- **Special-teams shares are poor** (about 12 points of error per game). `st_snaps_est` is left blank; only `st_pct_est` is given.
- **Defensive linemen, linebackers, tight ends and fullbacks are the weakest groups** at season level, because rotation is not visible in a depth chart.
- **Gameday inactives are taken from the weekly roster status, not from a gamebook.** In 2013 and 2014 every player-game with status `I01` had zero real snaps (4,072 in 2013 and 4,051 in 2014), so the flag tested as exact there. It is assumed, not tested, that the 2010 to 2012 status values were recorded the same way. The 2010 file also has 350 rows with status `I02`, 339 of them quarterbacks, none with a box-score line; this looks like the inactive third quarterback designation that existed through 2010 (an inference from the pattern, not a documented code). They are treated as inactive. Active players who dressed and did not play are still estimated by the model, not known.
- **In-game injuries are invisible.**
- **The model assumes roles map to snaps in 2010 to 2012 as they did in 2013 and 2014.** This cannot be tested, because no real counts exist for those seasons.
- **Rows with no player ID were dropped.**

## Columns

| Column | Meaning |
|---|---|
| season, week, game_date, team, opponent | regular-season game key; team codes as used in that season (STL, SD, OAK) |
| player_name, player_id, position | nflverse name, GSIS ID, listed position |
| offense_snaps_est, defense_snaps_est | estimated share times estimated team snaps |
| offense_pct_est, defense_pct_est, st_pct_est | estimated share, 0 to 100 |
| st_snaps_est | blank |
| team_offense_snaps_est, team_defense_snaps_est | estimated team snaps in that game |
| chart_offense_slot, chart_offense_depth, chart_defense_slot, chart_defense_depth | his depth-chart listing that week; blank if not listed |
| on_depth_chart, has_box_score_line, on_weekly_roster | 1 or 0 |
| gameday_inactive | 1 if the weekly roster status that week begins with `I` and he has no box-score line; his estimates are then zero |

## Files

| File | Rows | Players | Team-games | sha256 |
|---|---:|---:|---:|---|
| `snap_estimates_2010.csv` | 27567 | 2032 | 512 | `f4cb8abb780a6e66bc039c6a6094ac79178cea7e3bc4cef7f92f7a242612ca60` |
| `snap_estimates_2011.csv` | 27502 | 2015 | 512 | `7e705d697a75906039ce797b35531ce8ecf3d56f29cce82d5b4292e0c119a38b` |
| `snap_estimates_2012.csv` | 27539 | 2027 | 512 | `c8bd7e5abf2d059b1bb066cc7dfc4502394c6b4439146849a8bf88333e717d8e` |

## Inputs (downloaded 2026-10-02)

| Local name | URL | sha256 |
|---|---|---|
| `dc_2010.csv` | https://github.com/nflverse/nflverse-data/releases/download/depth_charts/depth_charts_2010.csv | `7771a3116a4518fc4a78fb51fe0850db661cc17fbdc54f666d540b85a04080a6` |
| `dc_2011.csv` | https://github.com/nflverse/nflverse-data/releases/download/depth_charts/depth_charts_2011.csv | `4c32f8cd3c1105d891fe64d98cdc902f2f2ad32e0f56b5088fe12aaaa316224a` |
| `dc_2012.csv` | https://github.com/nflverse/nflverse-data/releases/download/depth_charts/depth_charts_2012.csv | `e091a7fa0343fe3ae0bcee9202e1d8ca1ff859db398d20ab751017df29e85719` |
| `dc_2013.csv` | https://github.com/nflverse/nflverse-data/releases/download/depth_charts/depth_charts_2013.csv | `68a48cb5c3488aa505c2612c21797353c794c9ce5094e5071cc866373e71fd71` |
| `dc_2014.csv` | https://github.com/nflverse/nflverse-data/releases/download/depth_charts/depth_charts_2014.csv | `37c5d02473ebec605aaf68747a50ec77f02347f68f16e69cb5d84862f75c6d3a` |
| `st_2010.csv` | https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_week_2010.csv | `76f33d484781a3bc1852aa8aab5003874ab219dcb6c67a7e2e881be9822c9d13` |
| `st_2011.csv` | https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_week_2011.csv | `c1720e9e5ed59b7def9486ae650ea73ee80dda1fd2ab97d50c5fb4f6565dbeaa` |
| `st_2012.csv` | https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_week_2012.csv | `5c8885d93ec529efa9d729cec1ef255f438ee27a59eba6e156a360fa0045b56b` |
| `st_2013.csv` | https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_week_2013.csv | `f7329a8f15084c9c23d841f14eb117fcc630d6c82913501f3c60f2d8f4e651a4` |
| `st_2014.csv` | https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_week_2014.csv | `a389b10d94eb8e6b9a153223d381aab821b0eff4cd73967835a21032192abc61` |
| `rw_2010.csv` | https://github.com/nflverse/nflverse-data/releases/download/weekly_rosters/roster_weekly_2010.csv | `c415397ed98cbf9b5e038cb9415b9ed0d0b1d2611b09d39a7be521893b7c6533` |
| `rw_2011.csv` | https://github.com/nflverse/nflverse-data/releases/download/weekly_rosters/roster_weekly_2011.csv | `80de7a110233fa7569c26e298d6393b48349263f4dd117cf047612239801bc19` |
| `rw_2012.csv` | https://github.com/nflverse/nflverse-data/releases/download/weekly_rosters/roster_weekly_2012.csv | `262fd2f9a862c3b97275d91c60951f940a4e82989503b8359ac11b12a76c0e2f` |
| `rw_2013.csv` | https://github.com/nflverse/nflverse-data/releases/download/weekly_rosters/roster_weekly_2013.csv | `76c47a629075ffd75f9c4ee49fadb6dad45396be486af897078fee5722969781` |
| `rw_2014.csv` | https://github.com/nflverse/nflverse-data/releases/download/weekly_rosters/roster_weekly_2014.csv | `331022cd3b0c69d99c581f02b6fde6853e87ac431739c4b49841ee6e02893d6c` |
| `sc_2013.csv` | https://github.com/nflverse/nflverse-data/releases/download/snap_counts/snap_counts_2013.csv | `9d1fdd557875b9a2c71d88e583da24a739dfca671edf8223d6171e39a421000e` |
| `sc_2014.csv` | https://github.com/nflverse/nflverse-data/releases/download/snap_counts/snap_counts_2014.csv | `84540709d9483552185c8ca3ef30b2f66fb94b30c3e6c21e7a27205f337f21d3` |
| `players.csv` | https://github.com/nflverse/nflverse-data/releases/download/players/players.csv | `e85b2736908bd6701b038d18d98025e2b31e6e9db7cebf6f21e71fb0c88f9ba1` |
| `games.csv` | https://github.com/nflverse/nflverse-data/releases/download/schedules/games.csv | `d5cd27ca83bdd58cff08e0e03637d726c3b3ca3741708e81727dcaa7194d86ef` |
