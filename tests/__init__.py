"""The regression suite: scenarios of the career's first season, replayed from its checkpoint.

Every module here runs with the live season pinned to 2003-04 (`runtime.seasons.active`), so a scenario keeps testing
the season it was written for after the career rolls on. The live season's own records are checked by
`scripts/validate_repository.py`; tests of later seasons pass their season explicitly.
"""
import os

os.environ.setdefault("CAREER_TEST_SEASON", "2003-04")
