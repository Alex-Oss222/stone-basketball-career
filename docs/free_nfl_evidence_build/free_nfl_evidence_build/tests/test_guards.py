import pandas as pd
import pytest

from free_nfl_evidence.guards import DataGuardError, assert_allowed_seasons, reject_simulation_frame, slice_as_of


def test_rejects_future_season():
    with pytest.raises(DataGuardError):
        assert_allowed_seasons([2014, 2015])


def test_as_of_gate():
    df = pd.DataFrame({"season": [2010, 2011, 2012, 2014], "x": [1, 2, 3, 4]})
    out = slice_as_of(df, 2012)
    assert out["season"].tolist() == [2010, 2011, 2012]


def test_rejects_explicit_simulation_marker():
    df = pd.DataFrame({"season": [2010], "data_origin": ["SIMULATED"]})
    with pytest.raises(DataGuardError):
        reject_simulation_frame(df)


def test_refuses_git_worktree_output(tmp_path):
    from free_nfl_evidence.guards import assert_output_isolated

    (tmp_path / ".git").mkdir()
    with pytest.raises(DataGuardError):
        assert_output_isolated(tmp_path / "real_evidence")
