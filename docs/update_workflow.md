# Update workflow

## Before advancing

Read Wade's player profile, current state, the Miami organization, team config, roster, depth chart and current event note.

Read player cards required for the event. Read finances when contract, cap, free-agency or trade consequences matter.

## Player milestones

The owning phase READMEs link directly to the full live pages. Use the [working-event and reply guide](live_player_milestones.md) to connect an actual appointment, plan, conversation or review to those screens. Original evidence stays in its phase/week; `milestones.json` adds its response, status and next checkpoint to both browser and Markdown views. Rookie and franchise replies use the existing canonical log/gate, with date and version checks.

Open the [active detailed career desk](../career/Dwyane_Wade/Milestones/README.md), or `/career` on the existing Railway service. The nine live screens are generated from dated career records by `runtime/player_milestones.py`; Shooting and Awards use `runtime/player_cards.py`. They are part of the normal report build, not a separate preview command. Full detail is the default.

When a dated event creates a genuine player decision, use its current milestone page: contract, free agency, training, trade update, exit meeting or camp review. The [milestone templates](templates/player_milestones/README.md) define the detail and the [recording workflow](templates/player_milestones/workflow.md) defines ownership. Show the available choice and next checkpoint, then record the player's response without deciding it for them. Inactive milestones state the missing trigger instead of inventing an offer, appointment, transaction or result.

Club-owned outcomes are notifications unless a verified player right creates a choice. A counteroffer is not an accepted contract, planned training is not completed work, and an expiring contract does not generate a new deal automatically. Existing contract, trade and development workflows own the mechanics; opening a screen never executes them.

The supported event CLIs refresh detailed views after their successful writes. For a manual source-record change, run `python scripts/update_player_reports.py` before committing. `--check` validates freshness without writing. Raw engine sidecars remain noncanonical until the owning game or phase note closes; regeneration does not change that boundary. Missing shot coordinates stay unavailable and never come from the illustrative fixtures.

## Team changes

The AI/GM owns team changes. A user request as Wade does not directly rewrite Miami's roster, depth chart, organization or cap sheet.

Every transaction must update:
- roster/control status;
- depth chart if the playable pool changed;
- affected player cards;
- finance state if a contract/cap fact changed;
- current state when Wade's own status changed.

## Date gate

Do not apply a known historical event until its date. The June 26 snapshot specifically leaves June 30 options and July free agency unresolved.

## External games

Relay may run games. Write the verified output into the correct game record, then update statistics, depth/role consequences and current state as appropriate.

## Validation

```sh
python scripts/validate_repository.py
python -m unittest discover -s tests -v
```
