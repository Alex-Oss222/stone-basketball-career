"""Free public NFL evidence layer, isolated from simulation data."""

from .guards import ALLOWED_SEASONS, DataGuardError, assert_allowed_seasons, slice_as_of

__all__ = [
    "ALLOWED_SEASONS",
    "DataGuardError",
    "assert_allowed_seasons",
    "slice_as_of",
]
