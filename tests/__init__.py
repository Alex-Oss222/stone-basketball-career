"""The regression suite: scenarios of the career's first season, replayed from its checkpoint.

Every module here runs with the live season pinned to 2003-04 (`runtime.seasons.active`), so a scenario keeps testing
the season it was written for after the career rolls on. The live season's own records are checked by
`scripts/validate_repository.py`; tests of later seasons pass their season explicitly.
"""
import os

os.environ.setdefault("CAREER_TEST_SEASON", "2003-04")


def live_season():
    """A context in which the career's real live season applies (for tests of the repository's current outputs)."""
    from contextlib import contextmanager
    from unittest import mock

    @contextmanager
    def unpinned():
        with mock.patch.dict(os.environ):
            os.environ.pop("CAREER_TEST_SEASON", None)
            yield
    return unpinned()
