# Miami Heat finances

**Live checkpoint:** June 26, 2003  
**Owner:** AI/GM

This folder now carries a six-season cap horizon so salary-cap continuity does not have to be rebuilt every offseason.

| File | Purpose |
|---|---|
| [cap_tracker.md](cap_tracker.md) | Readable six-season Miami cap sheet and current reconciliation |
| [finance.json](finance.json) | Compact live finance state used by the simulation |
| [contract_schedules.json](contract_schedules.json) | Existing contract schedules, pending options and Wade's draft hold as of June 26 |
| [league_cap_history.json](league_cap_history.json) | Real NBA salary-cap limits from 2003-04 through 2008-09 |

## Critical distinction

The historical actual 2003-04 salary cap was **$43,840,000**, but it was not announced until July 15, 2003. The live simulation clock is June 26. Therefore:

- the real cap is stored so the project never drifts to a fake number;
- `live_official_salary_cap` remains null until the announcement reaches the career clock;
- the difference between known salary and $43.84M is **not** labeled cap room;
- free-agent holds, option decisions, renouncements and incomplete-roster charges must be reconciled before usable room is certified.

The same rule applies to the five future cap rows. They are historical continuity data, not advance information for the 2003 front office.

## Current known counted baseline

Existing contract salaries plus Wade's mandatory unsigned first-round scale hold total **$28,466,078**:

| Item | 2003-04 amount |
|---|---:|
| Eddie Jones | $12,333,750 |
| Brian Grant | $12,130,648 |
| Caron Butler | $1,804,680 |
| Dwyane Wade unsigned No. 5 scale hold | $2,197,000 |
| **Known baseline** | **$28,466,078** |

Anthony Carter's $4.1M player option and Rasual Butler's $563,679 team option are tracked separately as pending. Sean Lampley's team option is also pending, but its exact amount remains unresolved rather than guessed.
