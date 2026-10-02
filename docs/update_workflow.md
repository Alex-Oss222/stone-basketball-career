# Update workflow

## Before advancing

Read Wade's player profile, current state, the Miami organization, team config, roster, depth chart and current event note.

Read player cards required for the event. Read finances when contract, cap, free-agency or trade consequences matter.

## Player milestones

When a dated event creates a genuine player decision, use the relevant [milestone template](templates/player_milestones/README.md): contract, free agency, training, trade update, exit meeting or camp review. Follow its [recording workflow](templates/player_milestones/workflow.md). Show the available choice and next checkpoint, then record the player's response without deciding it for them.

Club-owned outcomes are notifications unless a verified player right creates a choice. A counteroffer is not an accepted contract, planned training is not completed work, and an expiring contract does not generate a new deal automatically. These templates do not implement the remaining contract, trade or development mechanics.

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
