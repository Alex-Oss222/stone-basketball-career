# Build status

Built October 2, 2026 as a standalone evidence layer. No user repository was opened, read, cloned, edited, committed, or pushed.

## Verified source assets

GitHub release metadata was checked for the following public nflverse assets:

- `stats_player_week_2010.csv` through `stats_player_week_2014.csv`
- `roster_weekly_2010.csv` through `roster_weekly_2014.csv`
- `injuries_2010.csv` through `injuries_2014.csv`
- `depth_charts_2010.csv` through `depth_charts_2014.csv`
- `play_by_play_2010.csv.gz` through `play_by_play_2014.csv.gz`
- `snap_counts_2012.csv` through `snap_counts_2014.csv`
- `players.csv`

## Test result

`10 passed`

Tests cover:

- rejection of 2015+ evidence;
- explicit no-hindsight filtering;
- rejection of simulation-marked inputs;
- refusal to write inside a Git worktree;
- 2010 depth-chart role evidence without fake snap counts;
- no invented pass-rush pressures;
- missing individual coverage assignments remaining null;
- team-defense PBP aggregation;
- 2012 observed snap percentage scale;
- end-to-end 2010 build orchestration.

## Network note

The execution sandbox could verify release metadata and source structure but could not directly download GitHub release binaries into the local runtime. The included downloader is therefore source-verified and unit/integration tested with fixtures, but the full five-season real dataset itself is not bundled in this archive. Running `free-nfl-evidence fetch` on a normal internet-connected machine downloads those public assets directly into the isolated workspace.
