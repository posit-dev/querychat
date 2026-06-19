"""Tests for tool functions and utilities."""

import html as html_module
import warnings

import narwhals.stable.v1 as nw
import pandas as pd
import polars as pl
import pytest
from htmltools import TagList
from querychat._data_dict import ColumnRange, ColumnSpec, DataDict, TableSpec
from querychat._datasource import DataFrameSource
from querychat._query_executor import DataSourceExecutor
from querychat._utils import querychat_tool_starts_open
from querychat.tools import (
    GetSchemaResult,
    UpdateDashboardData,
    _get_schema_impl,
    _query_impl,
    tool_reset_dashboard,
)
from shinychat import message_content_chunk


@pytest.fixture
def data_source():
    df = nw.from_native(pd.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]}))
    return DataFrameSource(df, "test_table")


@pytest.fixture
def executor(data_source):
    return DataSourceExecutor({"test_table": data_source})


class TestQueryCollapsedParameter:
    """Tests for the query tool's collapsed parameter."""

    def test_collapsed_true_sets_open_false(self, executor, monkeypatch):
        monkeypatch.delenv("QUERYCHAT_TOOL_DETAILS", raising=False)
        query_fn = _query_impl(executor)
        result = query_fn("SELECT * FROM test_table", collapsed=True)
        assert result.extra["display"].open is False

    def test_collapsed_false_sets_open_true(self, executor, monkeypatch):
        monkeypatch.delenv("QUERYCHAT_TOOL_DETAILS", raising=False)
        query_fn = _query_impl(executor)
        result = query_fn("SELECT * FROM test_table", collapsed=False)
        assert result.extra["display"].open is True

    def test_collapsed_none_falls_back_to_default(self, executor, monkeypatch):
        monkeypatch.delenv("QUERYCHAT_TOOL_DETAILS", raising=False)
        query_fn = _query_impl(executor)
        result = query_fn("SELECT * FROM test_table")
        assert result.extra["display"].open is False  # default for query

    def test_collapsed_overrides_env_expanded(self, executor, monkeypatch):
        monkeypatch.setenv("QUERYCHAT_TOOL_DETAILS", "expanded")
        query_fn = _query_impl(executor)
        result = query_fn("SELECT * FROM test_table", collapsed=True)
        assert result.extra["display"].open is False

    def test_collapsed_overrides_env_collapsed(self, executor, monkeypatch):
        monkeypatch.setenv("QUERYCHAT_TOOL_DETAILS", "collapsed")
        query_fn = _query_impl(executor)
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


def test_update_dashboard_data_has_table_field():
    """Test that UpdateDashboardData includes table field."""
    # TypedDict should have table as a key
    assert "table" in UpdateDashboardData.__annotations__


def test_reset_dashboard_accepts_table_parameter():
    """Test that reset_dashboard tool accepts table parameter."""
    reset_tables = []

    def callback(table: str):
        reset_tables.append(table)

    tool = tool_reset_dashboard(callback, ["orders"])

    # The tool function should accept table parameter
    tool.func(table="orders")

    assert reset_tables == ["orders"]


def test_reset_dashboard_rejects_unknown_table():
    """Reset dashboard should fail fast for an unknown table name."""
    reset_tables = []

    def callback(table: str):
        reset_tables.append(table)

    tool = tool_reset_dashboard(callback, ["orders"])

    result = tool.func(table="customers")

    assert reset_tables == []
    assert result.error is not None
    assert "Table 'customers' not found" in str(result.error)


def test_reset_dashboard_without_table_names_preserves_legacy_signature():
    """Public helper should still work without passing table_names."""
    reset_tables = []

    def callback(table: str):
        reset_tables.append(table)

    tool = tool_reset_dashboard(callback)

    tool.func(table="customers")

    assert reset_tables == ["customers"]


def _make_executor_and_table(
    df: pl.DataFrame, table_name: str
) -> tuple[DataSourceExecutor, list[str]]:
    source = DataFrameSource(nw.from_native(df), table_name)
    executor = DataSourceExecutor({table_name: source})
    return executor, [table_name]


def test_get_schema_impl_with_data_dict() -> None:
    dd = DataDict(
        tables={
            "orders": TableSpec(
                columns=[ColumnSpec(name="amount", range=ColumnRange(min=0, max=100))]
            )
        },
    )
    df = pl.DataFrame({"amount": [10, 20]})
    executor, table_names = _make_executor_and_table(df, "orders")
    fn = _get_schema_impl([dd], executor, table_names, categorical_threshold=10)
    result = fn("orders")
    assert "amount" in str(result.value)
    assert "Range: 0 to 100" in str(result.value)


def test_get_schema_impl_without_data_dict() -> None:
    df = pl.DataFrame({"amount": [10, 20, 30]})
    executor, table_names = _make_executor_and_table(df, "orders")
    fn = _get_schema_impl([], executor, table_names, categorical_threshold=10)
    result = fn("orders")
    assert "amount" in str(result.value)


def test_get_schema_impl_unknown_table_returns_error() -> None:
    df = pl.DataFrame({"amount": [1]})
    executor, table_names = _make_executor_and_table(df, "orders")
    fn = _get_schema_impl([], executor, table_names, categorical_threshold=10)
    result = fn("nonexistent")
    assert result.error is not None
    assert "nonexistent" in str(result.error)


def test_get_schema_result_sentinel_has_data_attributes():
    result = GetSchemaResult(
        value="Table: orders\nColumns:\n- id (INTEGER)",
        table_name="orders",
    )
    msg = message_content_chunk(result)
    # msg.content is a pre-rendered HTML string; wrap in TagList to render again
    rendered = TagList(msg.content).render()
    html = rendered["html"]
    assert "qc-schema-collector" in html
    assert 'data-table="orders"' in html
    assert "display:none" in html


def test_get_schema_result_sentinel_embeds_schema():
    schema = "Table: orders\nColumns:\n- id (INTEGER)"
    result = GetSchemaResult(value=schema, table_name="orders")
    msg = message_content_chunk(result)
    # ChatMessage pre-renders TagList to a string; unescape HTML entities to check schema
    assert schema in html_module.unescape(msg.content)


def test_get_schema_result_includes_js_dependency():
    result = GetSchemaResult(value="Table: t\nColumns:\n- x (TEXT)", table_name="t")
    msg = message_content_chunk(result)
    # ChatMessage extracts HTMLDependency objects into html_deps
    dep_names = [d.name for d in msg.html_deps]
    assert "querychat-schema-display" in dep_names
