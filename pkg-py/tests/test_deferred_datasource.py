"""Tests for deferred data source initialization."""

import os

import pandas as pd
import pytest
from querychat._querychat_base import QueryChatBase


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
    """Create a sample pandas DataFrame for testing."""
    return pd.DataFrame(
        {
            "id": [1, 2, 3],
            "name": ["Alice", "Bob", "Charlie"],
            "age": [25, 30, 35],
        },
    )


class TestDeferredDataSourceInit:
    """Tests for initializing QueryChatBase with None data_source."""

    def test_init_with_none_data_source(self):
        """QueryChatBase should accept None data_source with table_name."""
        qc = QueryChatBase(None, "users")
        assert qc._data_source is None
        assert qc._table_name == "users"

    def test_init_with_none_requires_table_name(self):
        """QueryChatBase with None data_source must have explicit table_name."""
        # This should work - table_name is explicitly provided
        qc = QueryChatBase(None, "users")
        assert qc._table_name == "users"


class TestDataSourceProperty:
    """Tests for the data_source property setter."""

    def test_data_source_setter(self, sample_df):
        """Setting data_source should normalize and build system prompt."""
        qc = QueryChatBase(None, "users")
        qc.data_source = sample_df

        assert qc._data_source is not None
        assert qc._data_source.table_name == "users"
        # System prompt should now be built
        assert "users" in qc.system_prompt

    def test_data_source_can_be_changed(self, sample_df):
        """data_source can be changed after initial set."""
        qc = QueryChatBase(sample_df, "original")

        new_df = pd.DataFrame({"x": [1, 2], "y": [3, 4]})
        qc.data_source = new_df

        # Should have new data source with original table_name
        assert qc._data_source is not None
        # System prompt should be rebuilt
        assert "original" in qc.system_prompt

    def test_data_source_getter_returns_none_when_not_set(self):
        """data_source property returns None when not set."""
        qc = QueryChatBase(None, "users")
        assert qc.data_source is None


class TestMethodRequirements:
    """Tests that methods properly require data_source to be set."""

    def test_client_requires_data_source(self):
        """client() should raise if data_source not set."""
        qc = QueryChatBase(None, "users")

        with pytest.raises(RuntimeError, match="data_source must be set"):
            qc.client()

    def test_console_requires_data_source(self):
        """console() should raise if data_source not set."""
        qc = QueryChatBase(None, "users")

        with pytest.raises(RuntimeError, match="data_source must be set"):
            qc.console()

    def test_generate_greeting_requires_data_source(self):
        """generate_greeting() should raise if data_source not set."""
        qc = QueryChatBase(None, "users")

        with pytest.raises(RuntimeError, match="data_source must be set"):
            qc.generate_greeting()

    def test_system_prompt_requires_data_source(self):
        """system_prompt property should raise if data_source not set."""
        qc = QueryChatBase(None, "users")

        with pytest.raises(RuntimeError, match="data_source must be set"):
            _ = qc.system_prompt

    def test_cleanup_safe_when_data_source_not_set(self):
        """cleanup() should not raise when data_source is None."""
        qc = QueryChatBase(None, "users")
        # Should not raise
        qc.cleanup()


class TestBackwardCompatibility:
    """Tests that existing patterns continue to work."""

    def test_immediate_pattern_unchanged(self, sample_df):
        """Existing code with data_source continues to work."""
        qc = QueryChatBase(sample_df, "test_table")

        assert qc.data_source is not None
        assert qc.data_source.table_name == "test_table"

        # All methods should work immediately
        client = qc.client()
        assert client is not None

        prompt = qc.system_prompt
        assert "test_table" in prompt


class TestDeferredPatternIntegration:
    """Integration tests for the full deferred pattern workflow."""

    def test_deferred_then_set_property(self, sample_df):
        """Test setting data_source via property after init."""
        # Create with None
        qc = QueryChatBase(None, "users")
        assert qc.data_source is None

        # Set via property
        qc.data_source = sample_df
        assert qc.data_source is not None

        # Now methods should work
        client = qc.client()
        assert client is not None
        assert "users" in qc.system_prompt

    def test_data_source_change_rebuilds_prompt(self, sample_df):
        """Test that changing data_source rebuilds system prompt."""
        qc = QueryChatBase(sample_df, "original")
        original_prompt = qc.system_prompt

        # Change data source (same table name)
        new_df = pd.DataFrame({"different": [1, 2], "columns": [3, 4]})
        qc.data_source = new_df

        new_prompt = qc.system_prompt

        # Prompt should be different (different schema)
        assert original_prompt != new_prompt
        # But table name should be preserved
        assert "original" in new_prompt
