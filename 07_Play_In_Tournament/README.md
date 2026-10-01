# Play-In Tournament

Do not pre-create blank game notes.

Create `Game_1.md` when the first play-in game is actually scheduled.

After Game 1 is played, set its metadata field `next_game_required` to `true` only if the team's path requires a second play-in game. Create `Game_2.md` only in that case.

Use `scripts/create_game_note.py` to create scheduled or explicit `not_played` records.
