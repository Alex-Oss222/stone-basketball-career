# Integration contract for a simulation engine

This file is guidance only. The standalone build does not touch the simulator.

## Allowed direction of data flow

`public historical source -> raw evidence -> derived real evidence -> gated read by simulator`

There is no supported flow from simulation output back into historical evidence.

## Career-clock read rule

Before any fit, player update, evaluation, roster decision, or game simulation for season `Y`, filter every evidence table to `season <= Y`.

Do not precompute a model on 2010-2014 and then use that fitted object in 2010-2013 unless the model itself was fitted only on data available through the career clock.

## Recommended engine fields

Use `role_class` and `measurement` together. A 2010 starter-depth signal is evidence of role but is not equivalent to an 85% snap share. A 2012 `starter_usage` observation has a stronger workload basis because it is snap-observed.

Use the pass-rush components independently. Do not add them into a pseudo-pressure total because sacks, hits, and TFLs can overlap conceptually.

For OL, use player role/availability plus the team context at deliberately lower individual confidence. Do not attribute the team's sack rate directly to one lineman.

For defensive calls, record the user's call. Keep the call-specific result modifier at zero/disabled. Team defensive strength may still affect results through the measured team-defense evidence.
