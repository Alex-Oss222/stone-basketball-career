"""Basketball career runtime: season rules, era calibration and the game engine.

Every game, whether it involves Wade or two background clubs, goes through the
same `run_game`. The engine has no seed parameter: game entropy comes only from
the private engine-state service (deployed on Railway) after the game packet
has been journaled there.
"""

KERNEL_VERSION = "2003.6"
SCHEMA_VERSION = "1"


def run_game(*args, **kwargs):
    from .game_runner import run_game as implementation
    return implementation(*args, **kwargs)
