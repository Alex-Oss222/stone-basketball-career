# Spatial shooting calibration — kernel 2003.7

The four-season diagnostic check passed on October 3, 2026, with no adjustment to league, team or player constants. Every one of the 4,428 non-Miami games had a complete spatial feed: 716,138 field-goal attempts and 313,910 makes reconciled with their player and team boxes. These are diagnostic aggregates, not career results or evidence for the front office. No canonical game was played, rewritten or given retrospective locations.

## Inputs and reproducibility

The calibration uses the established real 2003-04 non-Miami schedule and dated real rotations, with deterministic stand-in diagnostic entropy and development swings. Its targets are the completed **2002-03** league environment, never 2003-04 results. The new spatial prior is [nba_2002_03_shot_environment.json](../library/2003/league/nba_2002_03_shot_environment.json), model `spatial-2003.1`.

The exact prior's canonical SHA-256, embedded in every diagnostic game, is:

```text
129841cc576449f8ebb7542a7cae22d4bd9cb5c5429ba956893eb95791ea43d6
```

The source is Basketball-Reference's 2002-03 player shooting and totals tables through the pinned `sumitrodatta/nba-alt-awards` mirror, revision `7f9b3375439b79cb4e62f66ae7d12160275c2863`. The committed prior records the upstream and local snapshot hashes, joins, trade-row handling, rounded-count reconstruction and geometric assumptions. Only prior-season league aggregates shape the spatial model; historical Wade NBA rates and individual spatial profiles are not imported.

Run:

```bash
python scripts/engine_diagnostics.py 4 --check --summary-json /tmp/spatial-calibration.json
python -m unittest tests.test_spatial_diagnostics -q
```

The summary contains league aggregates, source provenance, fingerprint and native-zone counts. The diagnostic script never saves individual game results. The six focused diagnostics tests passed; they cover complete aggregation, missing and mismatched provenance, omitted attempts, concentrated sampling drift and empty samples.

## League results

Per team per game, including overtime:

| Measure | Simulated | Prior-season target |
| --- | ---: | ---: |
| Points | 94.942 | 95.1 |
| FGA | 80.865 | 80.8 |
| 3PA | 15.058 | 14.7 |
| FTA | 24.881 | 24.4 |
| Turnovers | 15.089 | 14.9 |
| Offensive rebounds | 12.117 | 12.0 |
| Defensive rebounds | 30.500 | 30.3 |
| Assists | 21.614 | 21.5 |
| Steals | 8.190 | 7.9 |
| Blocks | 5.139 | 5.0 |
| Personal fouls | 22.164 | 21.8 |
| FG% | 43.834% | 44.2% |
| 3P% | 34.993% | 34.9% |
| FT% | 75.482% | 75.8% |

All eleven box-count targets pass the existing tolerances: 3% relative for points/FGA and 6% for the remaining counts. All three shooting percentages pass the existing one-percentage-point absolute tolerance.

The final-margin standard deviation was 13.279, overtime rate 5.036%, home win rate 59.237%, home margin 3.276 points, foul-outs per game 0.217 and standard deviation of club season-average margins 4.721. These fall within the existing era benchmarks. Box-counted possessions were 95.056; this is a different definition from the source's published pace estimate of 91.0. Recorded transition possessions were 9.828 per team, with 7.026 seconds per transition possession.

## Native spatial bands

The source measures distance bands and corner/arc threes. It does not measure the chart's custom restricted-area or paint regions. The chart derives those physical reporting zones from simulated coordinates.

| Native source band | Attempts | Makes | Share of all FGA | Share within 2PA or 3PA | Source conditional share | Simulated FG% | Source FG% |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0–3 feet | 203,725 | 121,966 | 28.448% | 34.957% | 34.968% | 59.868% | 60.276% |
| 3–10 feet | 106,471 | 40,325 | 14.867% | 18.269% | 18.305% | 37.874% | 38.381% |
| 10–16 feet | 103,880 | 39,905 | 14.506% | 17.825% | 17.849% | 38.415% | 38.807% |
| 16 feet to the three-point line | 168,708 | 65,050 | 23.558% | 28.949% | 28.879% | 38.558% | 38.932% |
| Corner three | 34,163 | 12,586 | 4.770% | 25.618% | 25.701% | 36.841% | 36.883% |
| Arc three | 99,191 | 34,078 | 13.851% | 74.382% | 74.299% | 34.356% | 34.275% |

All six conditional-share checks pass. The denominator is the appropriate shot value: 582,784 two-point attempts or 133,354 three-point attempts. For source conditional share `p` and sample `n`, the allowed sampling difference is `5 * sqrt(p * (1-p) / n) + 1/n`. This is five binomial standard errors plus one attempt, chosen before observing the diagnostic output. At this sample size the normal approximation gives a combined false-alarm probability below four in a million across six checks. It is not a fitted tolerance.

Each player's established two-/three-point attempt rates remain in control of that split. Native-zone make probabilities preserve the sourced efficiency differences while shifting their weighted mean to the player's situational base make probability. Water filling handles clipping at zero and one. An analytic check over both shot values and fifteen base targets spanning zero to one found a maximum weighted-mean error of `1.11e-16`. Thus zone FG% in the table is descriptive: it reflects the simulated population's own ability, defense, transition and other existing effects, rather than forcing every band to the league source percentage.

## Integrity and limits

Every diagnostic result passed the ordinary box-score validation and the spatial validator. Checks require unique ordered shot IDs, legal coordinates and native zones, consistent shot value and make/miss type, valid period/clocks, the correct shooter/side, player and team reconciliation, transition reconciliation and complete versioned provenance. Diagnostics additionally reject any game with missing tracking or a different prior fingerprint before adding it to the aggregate.

These checks establish consistency and aggregate calibration. They do not establish individual shot tendencies or validate within-band coordinates against historical tracking. Every player currently shares the same prior-season conditional spatial shape, conditioned on his existing two-/three-point rates; within-band coordinates are explicitly modeled geometric assumptions. Closed legacy games remain without invented locations.
