# Free NFL Evidence Layer, 2010-2014

This is a standalone build. It does **not** read, modify, or write to the user's simulation repository.
It is designed specifically to keep real historical evidence separate from simulated career data.

## What it builds

The pipeline uses public nflverse release files and produces six derived evidence products:

1. `role_availability.csv`
   - 2010-2011: weekly depth-chart role plus weekly roster/injury evidence.
   - 2012-2014: the same evidence plus observed PFR snap counts when PFR-to-GSIS ID mapping succeeds. nflverse snap-share fields are treated as fractions (1.00 = 100%), with a scale check for compatibility.
   - It never back-fills or estimates 2010-2011 snap counts.

2. `pass_disruption.csv`
   - Sacks, non-sack QB hits as supplied by nflverse, tackles for loss, and forced fumbles.
   - Per-100-defensive-snap rates only when real snap counts exist.
   - It never creates a synthetic `pressures` or `hurries` statistic.

3. `coverage_observables.csv`
   - Interceptions, passes defended, tackles, and snap-normalized rates where available.
   - Individual targets/receptions/yards allowed are left null because the approved free sources do not identify the primary coverage defender for 2010-2014.

4. `team_defense.csv`
   - Play-by-play-derived team defensive performance including EPA, sack rate, QB-hit rate, interception rate, completion rate allowed, explosive-play rates, rushing EPA, and third-down conversion rate allowed.

5. `offensive_line_evidence.csv`
   - Individual line role/availability evidence joined to team protection and rushing context.
   - Team outcomes are explicitly labeled as team context, not individual blocking credit.

6. `defensive_call_policy.csv`
   - A hard guard declaring coverage-shell/blitz call effect modifiers `NOT_ESTIMATED`.
   - The simulator may record calls, but should apply no call-specific modifier until charted evidence exists.

Every derived CSV is tagged:

- `data_origin = REAL_PUBLIC_HISTORICAL`
- `source_dataset = ...`

The output contract also records `simulation_data_used = false`.

## Data sources

The downloader points only at public nflverse GitHub release assets. Relevant upstream coverage includes:

- play-by-play from 1999 onward;
- weekly player statistics;
- weekly rosters back to 2002;
- weekly depth charts back to 2001;
- injury reports back to 2009;
- PFR snap counts beginning in 2012;
- the nflverse player-ID crosswalk for GSIS/PFR IDs.

No PFF, SIS, Football Outsiders premium, or other paid charting is used.

## Safety boundary from simulation data

The downloader has no code path for reading the user's repository. By default, both `fetch` and `build` also refuse to write into any directory located inside a Git worktree. Run it in a separate folder such as:

```text
C:\Users\alexl\OneDrive\Desktop\NFL_REAL_EVIDENCE\
```

Inputs explicitly marked `SIMULATED`, `SIM`, `SYNTHETIC`, or similar are rejected.

## Install

From this extracted folder:

```bash
python -m pip install -e .
```

## See the public URLs without downloading

```bash
free-nfl-evidence urls --seasons 2010:2014
```

## Download public data

Use a folder that is **not inside the simulation repo**:

```bash
free-nfl-evidence fetch --workspace "C:\Users\alexl\OneDrive\Desktop\NFL_REAL_EVIDENCE" --seasons 2010:2014
```

The command writes a SHA-256 `source_manifest.json` beside the `raw/` folder.

## Build evidence

```bash
free-nfl-evidence build --workspace "C:\Users\alexl\OneDrive\Desktop\NFL_REAL_EVIDENCE" --seasons 2010:2014
```

Outputs go under `derived/`.

## No-hindsight gate

Even if all five historical seasons are stored in the evidence workspace, a career at 2012 must not read 2013 or 2014. The package includes an explicit export gate:

```bash
free-nfl-evidence as-of \
  --input "...\derived\team_defense.csv" \
  --output "...\exports\team_defense_through_2012.csv" \
  --season 2012
```

The same `slice_as_of()` function can be called from Python before fitting or evaluating a season.

## Team-code normalization

To make joins consistent across nflverse source families, historical relocation aliases are normalized internally: `STL -> LA`, `SD -> LAC`, `OAK -> LV`, and `JAC -> JAX`. The evidence layer does not assume the simulator uses those codes; map them at the eventual integration boundary if the simulator preserves historical abbreviations.

## Important interpretation rules

- `DEPTH_CHART_PROXY` is a real role indicator, not a snap estimate.
- `SNAP_OBSERVED` means actual snap data was present.
- Missing charting remains missing. Blank/null does not mean zero.
- Team offensive-line context is not individual player credit.
- Sacks + QB hits are not renamed to `pressures`.
- Defensive-call effect size remains disabled when no charted evidence supports it.
- Seasons after 2014 are rejected by the evidence builder.

## Tests

```bash
pytest -q
```

The tests cover the 2015+ guard, no-hindsight filter, simulation-data rejection, no fake 2010 snap counts, no invented pressures, missing coverage assignment data, and play-by-play team-defense aggregation.
