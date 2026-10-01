# Update workflow

## Before advancing

Read Wade's player profile, current state, the Miami organization, team config, roster, depth chart and current event note.

Read player cards required for the event. Read finances when contract, cap, free-agency or trade consequences matter.

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
