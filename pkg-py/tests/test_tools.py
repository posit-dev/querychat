"""Tests for tool functions and utilities."""

import warnings

import narwhals.stable.v1 as nw
import pandas as pd
import pytest
from querychat._datasource import DataFrameSource
from querychat._utils import querychat_tool_starts_open
from querychat.tools import _query_impl


@pytest.fixture
def data_source():
    df = nw.from_native(pd.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]}))
    return DataFrameSource(df, "test_table")


class TestQueryCollapsedParameter:
    """Tests for the query tool's collapsed parameter."""

    def test_collapsed_true_sets_open_false(self, data_source, monkeypatch):
        monkeypatch.delenv("QUERYCHAT_TOOL_DETAILS", raising=False)
        query_fn = _query_impl(data_source)
        result = query_fn("SELECT * FROM test_table", collapsed=True)
        assert result.extra["display"].open is False

    def test_collapsed_false_sets_open_true(self, data_source, monkeypatch):
        monkeypatch.delenv("QUERYCHAT_TOOL_DETAILS", raising=False)
        query_fn = _query_impl(data_source)
        result = query_fn("SELECT * FROM test_table", collapsed=False)
        assert result.extra["display"].open is True

    def test_collapsed_none_falls_back_to_default(self, data_source, monkeypatch):
        monkeypatch.delenv("QUERYCHAT_TOOL_DETAILS", raising=False)
        query_fn = _query_impl(data_source)
        result = query_fn("SELECT * FROM test_table")
        assert result.extra["display"].open is True  # default for query

    def test_collapsed_overrides_env_expanded(self, data_source, monkeypatch):
        monkeypatch.setenv("QUERYCHAT_TOOL_DETAILS", "expanded")
        query_fn = _query_impl(data_source)
        result = query_fn("SELECT * FROM test_table", collapsed=True)
        assert result.extra["display"].open is False

    def test_collapsed_overrides_env_collapsed(self, data_source, monkeypatch):
        monkeypatch.setenv("QUERYCHAT_TOOL_DETAILS", "collapsed")
        query_fn = _query_impl(data_source)
        result = query_fn("SELECT * FROM test_table", collapsed=False)
        assert result.extra["display"].open is True


def test_querychat_tool_starts_open_default_behavior(monkeypatch):
    """Test default behavior when no setting is provided."""
    monkeypatch.delenv("QUERYCHAT_TOOL_DETAILS", raising=False)

    assert querychat_tool_starts_open("query") is True
    assert querychat_tool_starts_open("update") is True
    assert querychat_tool_starts_open("reset") is False
    assert querychat_tool_starts_open("visualize_query") is True


def test_querychat_tool_starts_open_expanded(monkeypatch):
    """Test 'expanded' setting."""
    monkeypatch.setenv("QUERYCHAT_TOOL_DETAILS", "expanded")

    assert querychat_tool_starts_open("query") is True
    assert querychat_tool_starts_open("update") is True
    assert querychat_tool_starts_open("reset") is True
    assert querychat_tool_starts_open("visualize_query") is True


def test_querychat_tool_starts_open_collapsed(monkeypatch):
    """Test 'collapsed' setting."""
    monkeypatch.setenv("QUERYCHAT_TOOL_DETAILS", "collapsed")

    assert querychat_tool_starts_open("query") is False
    assert querychat_tool_starts_open("update") is False
    assert querychat_tool_starts_open("reset") is False
    assert querychat_tool_starts_open("visualize_query") is False


def test_querychat_tool_starts_open_default_setting(monkeypatch):
    """Test 'default' setting."""
    monkeypatch.setenv("QUERYCHAT_TOOL_DETAILS", "default")

    assert querychat_tool_starts_open("query") is True
    assert querychat_tool_starts_open("update") is True
    assert querychat_tool_starts_open("reset") is False
    assert querychat_tool_starts_open("visualize_query") is True


def test_querychat_tool_starts_open_case_insensitive(monkeypatch):
    """Test that setting is case-insensitive."""
    monkeypatch.setenv("QUERYCHAT_TOOL_DETAILS", "EXPANDED")
    assert querychat_tool_starts_open("query") is True

    monkeypatch.setenv("QUERYCHAT_TOOL_DETAILS", "Collapsed")
    assert querychat_tool_starts_open("query") is False

    monkeypatch.setenv("QUERYCHAT_TOOL_DETAILS", "DeFaUlT")
    assert querychat_tool_starts_open("query") is True


def test_querychat_tool_starts_open_invalid_setting(monkeypatch):
    """Test warning on invalid setting."""
    monkeypatch.setenv("QUERYCHAT_TOOL_DETAILS", "invalid")

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        result = querychat_tool_starts_open("query")

        assert len(w) == 1
        assert "Invalid value" in str(w[0].message)
        assert result is True  # Falls back to default behavior
