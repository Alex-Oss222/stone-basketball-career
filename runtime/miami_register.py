"""Dated facts on Miami's register rows (`<season>/00_Team/Team/Roster/roster.json`).

A register row is read by played games' frozen inputs (`game_requests.freeze`), the staff's rotation reviews and the
front office's need score, so a fact found wrong after games were played is never rewritten in place: the row keeps
the value those games read and carries the correction with the date it takes effect, the way `date_of_birth_from`
already does for a birth date recorded later (`injuries.simulated_ages`). Every reader that selects by position asks
`positions_on(row, day)`; a reader with no date (a page) asks it with the career date.

- **Position corrections:** `positions_corrected` (the corrected list), `positions_corrected_from` (the first date it is
  in force) and `positions_correction_basis`. Before that date the row's `positions` stand; from it, the correction.
  The season rollover carries the corrected list into the next season's register (`rollover.Rollover.register`).
- **Missing positions:** a writer that once filled a missing position with "SF" (an arrival's register row, a
  departing player's previous share, a re-signing or sign-and-trade plan) asks `required_position`: through
  POSITION_GUESS_UNTIL it still answers "SF", so every recorded decision replays unchanged; from the day after, a
  missing position stops the writer with the player's name instead of being guessed (the audit of 2006-06-20). A
  ranking by positional fit (free-agent targets, refill and camp candidates) asks `ranked_position`, which leaves such
  a candidate unranked instead; the front office's position table (`gm.FrontOffice._positions`) reads a registry row
  with no recorded position (`write_back.known_position`) as none from the same day.
"""
from __future__ import annotations

POSITION_GUESS_UNTIL = "2006-06-20"       # the last career date on which a missing position was filled with "SF"
GUESSED_POSITION = "SF"
# Register statuses of rights Miami holds without a contract: on the register, never under contract, available, in a
# rotation role or a Team-page player row (`team_status.register`, `write_back.team_page`).
RIGHTS_ONLY = ("free_agent_rights_held", "unsigned_draft_rights")


def positions_on(row, day):
    """The row's positions on `day` (ISO date): its dated correction from `positions_corrected_from`, else `positions`."""
    start = row.get("positions_corrected_from")
    if start and day and day >= start and row.get("positions_corrected"):
        return list(row["positions_corrected"])
    return list(row.get("positions") or [])


def with_positions_on(rows, day):
    """Register rows with each row's `positions` as they stand on `day` (copies; the rows themselves are unchanged)."""
    return [dict(r, positions=positions_on(r, day)) if r.get("positions_corrected_from") else r for r in rows]


def carried(row, day):
    """A register row carried into a new season on `day`: a correction in force by then becomes its `positions`."""
    out = dict(row)
    if row.get("positions_corrected_from") and day >= row["positions_corrected_from"]:
        out["positions"] = positions_on(row, day)
        for key in ("positions_corrected", "positions_corrected_from", "positions_correction_basis"):
            out.pop(key, None)
    return out


def ranked_position(value, day):
    """A candidate's position in a ranking by positional fit (the front office's free-agent targets, refill and camp
    candidates): `value`; on or before POSITION_GUESS_UNTIL the old "SF" guess (recorded rankings replay as made); later
    None, and the ranking leaves him out: fit needs a position, and one pool player without a source must not stop a
    summer or reach a negotiation that `required_position` would stop at signing."""
    if value:
        return value
    return GUESSED_POSITION if day and day <= POSITION_GUESS_UNTIL else None


def required_position(value, day, who):
    """`value` when a source gave one; on or before POSITION_GUESS_UNTIL the old "SF" guess (recorded decisions replay
    as they were made); later a ValueError naming the player, so the gap is filled from a source instead of guessed."""
    if value:
        return value
    if day and day <= POSITION_GUESS_UNTIL:
        return GUESSED_POSITION
    raise ValueError(f"{who}: no position in any identity source on {day}; record his position (registry, rosters or "
                     "prospect evidence) instead of guessing one")
