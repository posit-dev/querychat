"""Tests for deferred data source patterns using add_table()."""

import os

import pandas as pd
import pytest
from querychat._querychat_base import QueryChatBase


@pytest.fixture(autouse=True)
def set_dummy_api_key():
    old_api_key = os.environ.get("OPENAI_API_KEY")
    os.environ["OPENAI_API_KEY"] = "sk-dummy-api-key-for-testing"
    yield
    if old_api_key is not None:
        os.environ["OPENAI_API_KEY"] = old_api_key
    else:
        del os.environ["OPENAI_API_KEY"]


@pytest.fixture
def sample_df():
    return pd.DataFrame(
        {
            "id": [1, 2, 3],
            "name": ["Alice", "Bob", "Charlie"],
            "age": [25, 30, 35],
        }
    )


class TestAddTableDeferred:
    """Tests for deferred data source using add_table()."""

    def test_add_table_after_deferred_init(self, sample_df):
        """add_table should work after deferred __init__(None)."""
        qc = QueryChatBase(None, "users")
        qc.add_table(sample_df, "users")

        assert "users" in qc.table_names()
        assert qc.table("users").data_source.table_name == "users"
        assert "users" in qc.system_prompt

    def test_add_table_replace(self, sample_df):
        """add_table(replace=True) should replace an existing table."""
        qc = QueryChatBase(sample_df, "original")

        new_df = pd.DataFrame({"x": [1, 2], "y": [3, 4]})
        qc.add_table(new_df, "original", replace=True)

        assert "original" in qc.table_names()
        assert "original" in qc.system_prompt

    def test_no_tables_when_deferred(self):
        """table_names() should return empty list when deferred."""
        qc = QueryChatBase(None, "users")
        assert qc.table_names() == []


class TestMethodRequirements:
    """Tests that methods properly require at least one data source."""

    def test_client_requires_data_source(self):
        qc = QueryChatBase(None, "users")

        with pytest.raises(RuntimeError, match="At least one data source"):
            qc.client()

    def test_console_requires_data_source(self):
        qc = QueryChatBase(None, "users")

        with pytest.raises(RuntimeError, match="At least one data source"):
            qc.console()

    def test_generate_greeting_requires_data_source(self):
        qc = QueryChatBase(None, "users")

        with pytest.raises(RuntimeError, match="At least one data source"):
            qc.generate_greeting()

    def test_system_prompt_requires_data_source(self):
        qc = QueryChatBase(None, "users")

        with pytest.raises(RuntimeError, match="At least one data source"):
            _ = qc.system_prompt

    def test_cleanup_safe_when_no_data_sources(self):
        qc = QueryChatBase(None, "users")
        qc.cleanup()


class TestBackwardCompatibility:
    """Tests that existing patterns continue to work."""

    def test_immediate_pattern_unchanged(self, sample_df):
        qc = QueryChatBase(sample_df, "test_table")

        assert len(qc.table_names()) > 0
        assert qc.table("test_table").data_source.table_name == "test_table"

        client = qc.client()
        assert client is not None

        prompt = qc.system_prompt
        assert "test_table" in prompt


class TestDeferredPatternIntegration:
    """Integration tests for the full deferred pattern workflow."""

    def test_deferred_then_add_table(self, sample_df):
        qc = QueryChatBase(None, "users")
        assert len(qc.table_names()) == 0
        assert qc._client_spec is None

        qc.add_table(sample_df, "users")
        assert len(qc.table_names()) > 0

        client = qc.client()
        assert client is not None
        assert "users" in qc.system_prompt

    def test_replace_table_rebuilds_prompt(self, sample_df):
        qc = QueryChatBase(sample_df, "original")

        new_df = pd.DataFrame({"different": [1, 2], "columns": [3, 4]})
        qc.add_table(new_df, "original", replace=True)

        new_prompt = qc.system_prompt
        assert "original" in new_prompt
