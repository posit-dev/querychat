"""Tests for _base.py - QueryChatBase and normalization functions."""

import os
from typing import Any

import chatlas
import narwhals.stable.v1 as nw
import pandas as pd
import pytest
from querychat._datasource import DataFrameSource, SQLAlchemySource
from querychat._querychat_base import (
    QueryChatBase,
    normalize_client,
    normalize_data_source,
    normalize_tools,
)
from querychat._utils import MISSING
from sqlalchemy import create_engine, text


@pytest.fixture(autouse=True)
def set_dummy_api_key():
    """Set a dummy OpenAI API key for testing."""
    old_api_key = os.environ.get("OPENAI_API_KEY")
    os.environ["OPENAI_API_KEY"] = "sk-dummy-api-key-for-testing"
    yield
    if old_api_key is not None:
        os.environ["OPENAI_API_KEY"] = old_api_key
    else:
        del os.environ["OPENAI_API_KEY"]


@pytest.fixture
def sample_df():
    """Create a sample narwhals DataFrame for testing."""
    pdf = pd.DataFrame(
        {
            "id": [1, 2, 3],
            "name": ["Alice", "Bob", "Charlie"],
            "age": [25, 30, 35],
        },
    )
    return nw.from_native(pdf)


@pytest.fixture
def sqlite_engine():
    """Create an in-memory SQLite engine with test data."""
    engine = create_engine("sqlite:///:memory:")
    with engine.connect() as conn:
        conn.execute(
            text(
                """
            CREATE TABLE test_table (
                id INTEGER PRIMARY KEY,
                name TEXT,
                age INTEGER
            )
        """
            )
        )
        conn.execute(
            text("INSERT INTO test_table VALUES (1, 'Alice', 25), (2, 'Bob', 30)")
        )
        conn.commit()
    return engine


# Tests for normalize_data_source
class TestNormalizeDataSource:
    def test_with_dataframe(self, sample_df):
        """Test normalization with a pandas DataFrame."""
        result = normalize_data_source(sample_df, "my_table")
        assert isinstance(result, DataFrameSource)
        assert result.table_name == "my_table"

    def test_with_sqlalchemy_engine(self, sqlite_engine):
        """Test normalization with a SQLAlchemy Engine."""
        result = normalize_data_source(sqlite_engine, "test_table")
        assert isinstance(result, SQLAlchemySource)
        assert result.table_name == "test_table"

    def test_with_existing_datasource(self, sample_df):
        """Test that existing DataSource is returned as-is."""
        existing = DataFrameSource(sample_df, "original_table")
        result = normalize_data_source(existing, "ignored_table")
        assert result is existing
        assert result.table_name == "original_table"

    def test_with_empty_dataframe(self):
        """Test normalization with an empty DataFrame."""
        empty_pdf = pd.DataFrame({"col1": [], "col2": []})
        empty_df = nw.from_native(empty_pdf)
        result = normalize_data_source(empty_df, "empty_table")
        assert isinstance(result, DataFrameSource)
        assert result.table_name == "empty_table"
        # Should still be able to get schema
        schema = result.get_schema(categorical_threshold=10)
        assert "col1" in schema
        assert "col2" in schema

    def test_with_special_column_names(self):
        """Test DataFrame with special characters in column names."""
        pdf = pd.DataFrame(
            {
                "column with spaces": [1, 2],
                "column-with-dashes": [3, 4],
                "column.with.dots": [5, 6],
            }
        )
        df = nw.from_native(pdf)
        result = normalize_data_source(df, "special_cols")
        assert isinstance(result, DataFrameSource)
        schema = result.get_schema(categorical_threshold=10)
        assert "column with spaces" in schema
        assert "column-with-dashes" in schema
        assert "column.with.dots" in schema


# Tests for normalize_client
class TestNormalizeClient:
    def test_with_none_uses_default(self):
        """Test that None defaults to OpenAI."""
        result = normalize_client(None)
        assert isinstance(result, chatlas.Chat)

    def test_with_string_provider(self):
        """Test with string provider name."""
        result = normalize_client("openai")
        assert isinstance(result, chatlas.Chat)

    def test_with_chat_instance(self):
        """Test with existing Chat instance."""
        chat = chatlas.ChatOpenAI()
        result = normalize_client(chat)
        assert isinstance(result, chatlas.Chat)

    def test_respects_env_variable(self, monkeypatch):
        """Test that QUERYCHAT_CLIENT env var is respected."""
        monkeypatch.setenv("QUERYCHAT_CLIENT", "openai")
        result = normalize_client(None)
        assert isinstance(result, chatlas.Chat)

    def test_with_invalid_provider_raises(self):
        """Test that invalid provider string raises an error."""
        with pytest.raises(ValueError, match="Unknown provider"):
            normalize_client("not_a_real_provider_xyz123")


# Tests for normalize_tools
class TestNormalizeTools:
    def test_with_none_returns_none(self):
        """Test that None input returns None."""
        assert normalize_tools(None, default=("update",)) is None

    def test_with_empty_tuple_returns_none(self):
        """Test that empty tuple returns None."""
        assert normalize_tools((), default=("update",)) is None

    def test_with_missing_returns_default(self):
        """Test that MISSING returns the default."""
        result = normalize_tools(MISSING, default=("update", "query"))
        assert result == ("update", "query")

    def test_with_string_returns_tuple(self):
        """Test that single string is wrapped in tuple."""
        result = normalize_tools("update", default=None)
        assert result == ("update",)

    def test_with_tuple_returns_same(self):
        """Test that tuple is returned as-is."""
        result = normalize_tools(("update", "query"), default=None)
        assert result == ("update", "query")

    def test_with_list_returns_tuple(self):
        """Test that list is converted to tuple."""
        # Using Any to bypass type checker for this edge case test
        tools_list: Any = ["update", "query"]
        result = normalize_tools(tools_list, default=None)
        assert result == ("update", "query")


# Tests for QueryChatBase
class TestQueryChatBase:
    def test_init_with_dataframe(self, sample_df):
        """Test initialization with a DataFrame."""
        qc = QueryChatBase(sample_df, "test_table")
        assert isinstance(qc.data_source, DataFrameSource)
        assert qc.tools == ("update", "query")

    def test_init_with_custom_greeting(self, sample_df):
        """Test initialization with custom greeting."""
        qc = QueryChatBase(sample_df, "test_table", greeting="Hello!")
        assert qc.greeting == "Hello!"

    def test_init_with_tools_none(self, sample_df):
        """Test initialization with tools=None."""
        qc = QueryChatBase(sample_df, "test_table", tools=None)
        assert qc.tools is None

    def test_init_with_single_tool(self, sample_df):
        """Test initialization with single tool string."""
        qc = QueryChatBase(sample_df, "test_table", tools="query")
        assert qc.tools == ("query",)

    def test_invalid_table_name_raises(self, sample_df):
        """Test that invalid table name raises ValueError."""
        with pytest.raises(ValueError, match="Table name must begin with a letter"):
            QueryChatBase(sample_df, "123_invalid")

        with pytest.raises(ValueError, match="Table name must begin with a letter"):
            QueryChatBase(sample_df, "table-with-dash")

    def test_data_source_property(self, sample_df):
        """Test that data_source property returns the data source."""
        qc = QueryChatBase(sample_df, "test_table")
        assert qc.data_source is qc._data_source

    def test_system_prompt_property(self, sample_df):
        """Test that system_prompt property returns rendered prompt."""
        qc = QueryChatBase(sample_df, "test_table")
        prompt = qc.system_prompt
        assert isinstance(prompt, str)
        assert "test_table" in prompt

    def test_client_method_returns_chat(self, sample_df):
        """Test that client() returns a Chat instance."""
        qc = QueryChatBase(sample_df, "test_table")
        client = qc.client()
        assert isinstance(client, chatlas.Chat)

    def test_client_with_tools_none(self, sample_df):
        """Test client() with tools=None doesn't register tools."""
        qc = QueryChatBase(sample_df, "test_table")
        client = qc.client(tools=None)
        # With no tools, the chat should have no registered tools
        assert isinstance(client, chatlas.Chat)

    def test_client_with_callbacks(self, sample_df):
        """Test client() with update and reset callbacks."""
        qc = QueryChatBase(sample_df, "test_table")
        update_called = []
        reset_called = []

        client = qc.client(
            update_dashboard=lambda data: update_called.append(data),
            reset_dashboard=lambda: reset_called.append(True),
        )
        assert isinstance(client, chatlas.Chat)

    def test_cleanup(self, sample_df):
        """Test cleanup method calls data source cleanup."""
        qc = QueryChatBase(sample_df, "test_table")
        qc.cleanup()  # Should not raise
