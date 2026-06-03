"""Tests for tool functions and utilities."""

import warnings

import narwhals.stable.v1 as nw
import pandas as pd
import pytest
from chatlas import ContentToolResult, Tool
from querychat._datasource import DataFrameSource
from querychat._tool_names import (
    TOOL_QUERY,
    TOOL_REQUEST_ARTIFACT,
    TOOL_RESET_DASHBOARD,
    TOOL_UPDATE_DASHBOARD,
    TOOL_VISUALIZE,
)
from querychat._utils import querychat_tool_starts_open
from querychat.tools import (
    _query_impl,
    _request_artifact_impl,
    tool_query,
    tool_request_artifact,
    tool_reset_dashboard,
    tool_update_dashboard,
    tool_visualize,
)


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
        assert result.extra["display"].open is False  # default for query

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

    assert querychat_tool_starts_open("query") is False
    assert querychat_tool_starts_open("update") is True
    assert querychat_tool_starts_open("reset") is False
    assert querychat_tool_starts_open("visualize") is True


def test_querychat_tool_starts_open_expanded(monkeypatch):
    """Test 'expanded' setting."""
    monkeypatch.setenv("QUERYCHAT_TOOL_DETAILS", "expanded")

    assert querychat_tool_starts_open("query") is True
    assert querychat_tool_starts_open("update") is True
    assert querychat_tool_starts_open("reset") is True
    assert querychat_tool_starts_open("visualize") is True


def test_querychat_tool_starts_open_collapsed(monkeypatch):
    """Test 'collapsed' setting."""
    monkeypatch.setenv("QUERYCHAT_TOOL_DETAILS", "collapsed")

    assert querychat_tool_starts_open("query") is False
    assert querychat_tool_starts_open("update") is False
    assert querychat_tool_starts_open("reset") is False
    assert querychat_tool_starts_open("visualize") is False


def test_querychat_tool_starts_open_default_setting(monkeypatch):
    """Test 'default' setting."""
    monkeypatch.setenv("QUERYCHAT_TOOL_DETAILS", "default")

    assert querychat_tool_starts_open("query") is False
    assert querychat_tool_starts_open("update") is True
    assert querychat_tool_starts_open("reset") is False
    assert querychat_tool_starts_open("visualize") is True


def test_querychat_tool_starts_open_case_insensitive(monkeypatch):
    """Test that setting is case-insensitive."""
    monkeypatch.setenv("QUERYCHAT_TOOL_DETAILS", "EXPANDED")
    assert querychat_tool_starts_open("query") is True

    monkeypatch.setenv("QUERYCHAT_TOOL_DETAILS", "Collapsed")
    assert querychat_tool_starts_open("query") is False

    monkeypatch.setenv("QUERYCHAT_TOOL_DETAILS", "DeFaUlT")
    assert querychat_tool_starts_open("query") is False


def test_querychat_tool_starts_open_invalid_setting(monkeypatch):
    """Test warning on invalid setting."""
    monkeypatch.setenv("QUERYCHAT_TOOL_DETAILS", "invalid")

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        result = querychat_tool_starts_open("query")

        assert len(w) == 1
        assert "Invalid value" in str(w[0].message)
        assert result is False  # Falls back to default behavior


def test_request_artifact_impl_invokes_callback():
    called = []
    impl = _request_artifact_impl(lambda: called.append(True))
    result = impl()
    assert called == [True]
    assert isinstance(result, ContentToolResult)
    assert "artifact" in str(result.value).lower()


def test_request_artifact_impl_result_has_no_error():
    impl = _request_artifact_impl(lambda: None)
    result = impl()
    assert result.error is None
    assert "artifact creator" in str(result.value).lower()


def test_tool_request_artifact_has_expected_name():
    tool = tool_request_artifact(lambda: None)
    assert isinstance(tool, Tool)
    assert tool.name == TOOL_REQUEST_ARTIFACT


class TestToolNameContract:
    """
    The tool-name constants are the single source of truth shared between tool
    registration and gallery extraction; pin their values and verify each tool
    registers under its constant.
    """

    def test_constants_have_expected_values(self):
        assert TOOL_QUERY == "querychat_query"
        assert TOOL_VISUALIZE == "querychat_visualize"
        assert TOOL_UPDATE_DASHBOARD == "querychat_update_dashboard"
        assert TOOL_RESET_DASHBOARD == "querychat_reset_dashboard"
        assert TOOL_REQUEST_ARTIFACT == "querychat_request_artifact"

    def test_tools_register_under_their_constants(self, data_source):
        assert tool_query(data_source).name == TOOL_QUERY
        assert tool_visualize(data_source, lambda _: None).name == TOOL_VISUALIZE
        assert (
            tool_update_dashboard(data_source, lambda _: None).name
            == TOOL_UPDATE_DASHBOARD
        )
        assert tool_reset_dashboard(lambda: None).name == TOOL_RESET_DASHBOARD
        assert tool_request_artifact(lambda: None).name == TOOL_REQUEST_ARTIFACT
