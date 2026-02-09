"""Tests for maybe_truncate helper."""

import warnings

import narwhals.stable.v1 as nw
import pandas as pd
import pytest
from querychat._utils import maybe_truncate


@pytest.fixture
def large_df():
    return nw.from_native(pd.DataFrame({"x": range(200), "y": range(200)}))


@pytest.fixture
def small_df():
    return nw.from_native(pd.DataFrame({"x": range(5), "y": range(5)}))


class TestMaybeTruncate:
    def test_truncates_when_exceeds_max(self, large_df):
        result = maybe_truncate(large_df, max_rows=50)
        assert len(result.df) == 50
        assert result.total_rows == 200
        assert result.total_cols == 2
        assert result.truncated is True

    def test_no_truncation_when_under_max(self, small_df):
        result = maybe_truncate(small_df, max_rows=50)
        assert len(result.df) == 5
        assert result.total_rows == 5
        assert result.truncated is False

    def test_no_truncation_when_max_is_none(self, large_df):
        result = maybe_truncate(large_df, max_rows=None)
        assert len(result.df) == 200
        assert result.truncated is False

    def test_no_truncation_when_exactly_at_max(self, large_df):
        result = maybe_truncate(large_df, max_rows=200)
        assert len(result.df) == 200
        assert result.truncated is False

    def test_info_message_when_truncated(self, large_df):
        result = maybe_truncate(large_df, max_rows=50)
        assert result.info_message == "Showing first 50 of 200 rows (2 columns)."

    def test_info_message_when_not_truncated(self, small_df):
        result = maybe_truncate(small_df, max_rows=50)
        assert result.info_message == "Data has 5 rows and 2 columns."

    def test_emits_warning_when_truncated(self, large_df):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            maybe_truncate(large_df, max_rows=50)
            assert len(w) == 1
            assert "Displaying 50 of 200 rows" in str(w[0].message)
            assert "max_rows" in str(w[0].message)

    def test_no_warning_when_not_truncated(self, small_df):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            maybe_truncate(small_df, max_rows=50)
            assert len(w) == 0

    def test_no_warning_when_warn_false(self, large_df):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            maybe_truncate(large_df, max_rows=50, warn=False)
            assert len(w) == 0
