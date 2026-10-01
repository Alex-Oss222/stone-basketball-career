# Update workflow

## Before an event

Read current state, player profile, season structure, and the current owning note. Confirm that the event is actually due and that the player has a real decision to make.

## When an event is scheduled

For play-in or playoff games, use:

```sh
python scripts/create_game_note.py ...
```

A scheduled game requires a date and opponent. Do not use a blank file as a placeholder.

Regular-season and phase notes already exist as empty state containers. Change `status` from `not_started` to `active` only when the period begins.

## When an event closes

Record the result in the owning note, then update only the current-state fields affected by that result. Do not manufacture unrelated changes.

For a played game, change the game-note status to `played` and record a result.

If a best-of-seven series ends before Game 5, 6, or 7, leave unscheduled files absent or create explicit `not_played` notes with a reason.

For Play-In Game 1, update `next_game_required` after the result. Do not create Game 2 unless that value is true.

## Validate

Run:

```sh
python scripts/validate_repository.py
python -m unittest discover -s tests -v
```

A structural failure means the repository should not be treated as a valid advanced state.
