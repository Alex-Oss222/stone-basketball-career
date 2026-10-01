# Project instructions

## Purpose

Maintain a coherent basketball career centered on one player. The repository is intentionally empty until a player and season are established.

## Source hierarchy

1. Explicit user-established player facts and decisions.
2. Closed simulation event notes.
3. Current state derived from those closed events.
4. Year-specific sourced league facts, if later added.
5. General basketball assumptions only when they do not conflict with a higher source.

Never treat a template or future folder as evidence that an event happened.

## Player authority boundary

The user's role is the player. Team and league actors remain independent. The player may influence but does not directly control roster construction, rotations, coaching decisions, trades, officiating, medical clearance, league discipline, awards, opponent behavior, or game results.

## State transitions

A phase/week note begins as `not_started`, may become `active`, and becomes `complete` only after its relevant work is actually closed.

Game notes use `scheduled`, `played`, or `not_played`. These statuses are deliberately separate from phase statuses.

Current state is a compact pointer, not a second event history.

## Conditional postseason records

Play-In Game 2 is conditional on the first play-in result.

Every playoff round is best of seven. Games 1 to 4 are necessary only after a series exists. Games 5 to 7 are conditional on the series still being alive.

Do not pre-create blank game files. A missing conditional game means no record exists yet. If an unused conditional slot needs explicit closure, use a `not_played` note with a reason.

## Year-specific league rules

The supplied calendar is a structural template. Exact season dates, trade-deadline dates, guarantee dates, tournament dates, eligibility dates, schedule, and league rules can vary by season. When a real season is chosen, verify and record the applicable dates before treating them as authoritative.

## Consistency

One fact has one primary owner. Derived state may summarize it but should point back to the owner when the project later gains links or identifiers.

Unknown is not zero, false, waived, healthy, unsigned, eliminated, or completed.
