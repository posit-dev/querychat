"""Tests for the TableSet value object."""

import duckdb
import pandas as pd
import pytest
from querychat._query_executor import DataSourceExecutor, DuckDBExecutor
from querychat._querychat_base import normalize_data_source
from querychat._system_prompt import QueryChatSystemPrompt
from querychat._table_set import TableSet


def make_table_set(**frames: pd.DataFrame) -> TableSet:
    sources = {name: normalize_data_source(df, name) for name, df in frames.items()}
    prompt = QueryChatSystemPrompt(prompt_template=None, data_sources=sources)
    return TableSet(sources, prompt)


@pytest.fixture
def users():
    return pd.DataFrame({"id": [1, 2], "name": ["a", "b"]})


@pytest.fixture
def orders():
    return pd.DataFrame({"id": [1], "user_id": [2]})


def test_requires_at_least_one_source():
    prompt = QueryChatSystemPrompt(prompt_template=None, data_sources={})
    with pytest.raises(ValueError, match="at least one"):
        TableSet({}, prompt)


def test_data_sources_is_read_only(users):
    ts = make_table_set(users=users)
    with pytest.raises(TypeError):
        ts.data_sources["other"] = ts.data_sources["users"]  # type: ignore[index]


def test_table_names_preserve_insertion_order(users, orders):
    with pytest.warns(UserWarning, match="without a data_dict"):
        ts = make_table_set(users=users, orders=orders)
    assert ts.table_names == ["users", "orders"]


def test_executor_is_lazy_and_cached(users):
    ts = make_table_set(users=users)
    assert ts.executor_built is False
    first = ts.executor
    assert ts.executor_built is True
    assert ts.executor is first


def test_single_table_uses_data_source_executor(users):
    assert isinstance(make_table_set(users=users).executor, DataSourceExecutor)


def test_multi_dataframe_uses_duckdb_executor(users, orders):
    with pytest.warns(UserWarning, match="without a data_dict"):
        ts = make_table_set(users=users, orders=orders)
    assert isinstance(ts.executor, DuckDBExecutor)


def test_cleanup_executor_is_noop_when_never_built(users):
    ts = make_table_set(users=users)
    ts.cleanup_executor()
    assert ts.executor_built is False


def test_cleanup_executor_closes_built_duckdb_executor(users, orders):
    with pytest.warns(UserWarning, match="without a data_dict"):
        ts = make_table_set(users=users, orders=orders)
    executor = ts.executor
    ts.cleanup_executor()
    with pytest.raises(duckdb.ConnectionException):
        executor.execute_query("SELECT 1")
