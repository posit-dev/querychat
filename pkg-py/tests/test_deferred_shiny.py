"""Tests for deferred data source in Shiny QueryChat."""

import os

import pandas as pd
import pytest
from querychat import QueryChat


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


class TestShinyDeferredDataSource:
    """Tests for deferred data source in Shiny QueryChat."""

    def test_init_with_none(self):
        """Shiny QueryChat should accept None data_source."""
        qc = QueryChat(None, "users")
        assert qc._data_source is None
        assert qc._table_name == "users"
        # ID should use table_name even with None data_source
        assert qc.id == "querychat_users"

    def test_ui_works_without_data_source(self):
        """ui() should work without data_source set."""
        qc = QueryChat(None, "users")
        # Should not raise
        ui = qc.ui()
        assert ui is not None

    def test_sidebar_works_without_data_source(self):
        """sidebar() should work without data_source set."""
        qc = QueryChat(None, "users")
        # Should not raise
        sidebar = qc.sidebar()
        assert sidebar is not None

    def test_app_requires_data_source(self):
        """app() should raise if data_source not set."""
        qc = QueryChat(None, "users")
        with pytest.raises(RuntimeError, match="data_source must be set"):
            qc.app()
