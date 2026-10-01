# Update workflow

## Before advancing

Read the player profile, current state, team config, and the current phase/week/game.

Read roster and rotation for games. Read finance state only when a financial or transaction question requires it.

## Team state

The AI/GM owns `00_Team`. Update it only after an actual simulated team decision or verified team-state change.

A user preference does not directly rewrite the rotation, roster, cap sheet or team strategy.

## External games

If Relay or another runner produces a game, record the matchup in the correct game file and then write the result there. Do not treat raw external output as canonical before it is attached to the career.

## Validation

```sh
python scripts/validate_repository.py
python -m unittest discover -s tests -v
```
