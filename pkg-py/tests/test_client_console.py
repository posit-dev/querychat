"""Tests for QueryChat.client() and QueryChat.console() methods."""

import os
from unittest.mock import patch

import chatlas
import pandas as pd
import pytest
from querychat import QueryChat
from querychat.types import UpdateDashboardData


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
            "salary": [50000, 60000, 70000],
        },
    )


class TestClientMethod:
    """Tests for QueryChat.client() method."""

    def test_client_returns_chat_instance(self, sample_df):
        """Test that client() returns a chatlas.Chat instance."""
        qc = QueryChat(sample_df, "test_table", greeting="Hello!")
        client = qc.client()

        assert client is not None
        assert hasattr(client, "chat")
        assert hasattr(client, "register_tool")

    def test_client_uses_default_tools(self, sample_df):
        """Test that client() uses default tools from initialization."""
        qc = QueryChat(sample_df, "test_table", greeting="Hello!")
        client = qc.client()

        # Check that system prompt includes both tool sections
        prompt = client.system_prompt
        assert "Filtering and Sorting Data" in prompt
        assert "Answering Questions About Data" in prompt

    def test_client_override_tools_query_only(self, sample_df):
        """Test that client() can override tools to query-only."""
        qc = QueryChat(sample_df, "test_table", greeting="Hello!")
        client = qc.client(tools="query")

        # Check that system prompt excludes update tool section
        prompt = client.system_prompt
        assert "Filtering and Sorting Data" not in prompt
        assert "Answering Questions About Data" in prompt

    def test_client_override_tools_update_only(self, sample_df):
        """Test that client() can override tools to update-only."""
        qc = QueryChat(sample_df, "test_table", greeting="Hello!")
        client = qc.client(tools="update")

        # Check that system prompt excludes query tool section
        prompt = client.system_prompt
        assert "Filtering and Sorting Data" in prompt
        assert "Answering Questions About Data" not in prompt

    def test_client_no_tools(self, sample_df):
        """Test that client() can be created with no tools."""
        qc = QueryChat(sample_df, "test_table", greeting="Hello!")
        client = qc.client(tools=None)

        prompt = client.system_prompt
        # Should not include tool-specific sections
        assert "Filtering and Sorting Data" not in prompt
        assert "Answering Questions About Data" not in prompt

    def test_client_independent_copies(self, sample_df):
        """Test that each client() call returns independent instances."""
        qc = QueryChat(sample_df, "test_table", greeting="Hello!")

        client1 = qc.client()
        client2 = qc.client()

        # Should be different instances
        assert client1 is not client2

        # Modifying one shouldn't affect the other
        client1.set_turns([{"role": "user", "content": "test"}])
        assert len(client1.get_turns()) == 1
        assert len(client2.get_turns()) == 0

    def test_client_custom_update_callback(self, sample_df):
        """Test that client() accepts custom update_dashboard callback."""
        qc = QueryChat(sample_df, "test_table", greeting="Hello!")

        callback_data = {}

        def my_update(data: UpdateDashboardData):
            callback_data["query"] = data["query"]
            callback_data["title"] = data["title"]

        client = qc.client(update_dashboard=my_update)

        # Callback should be registered (we can't easily test execution without
        # mocking the LLM, but we can verify the client was created)
        assert client is not None

    def test_client_custom_reset_callback(self, sample_df):
        """Test that client() accepts custom reset_dashboard callback."""
        qc = QueryChat(sample_df, "test_table", greeting="Hello!")

        reset_called = {"called": False}

        def my_reset():
            reset_called["called"] = True

        client = qc.client(reset_dashboard=my_reset)

        # Callback should be registered
        assert client is not None

    def test_client_respects_initialization_tools(self, sample_df):
        """Test that client() respects tools set at initialization."""
        qc = QueryChat(sample_df, "test_table", greeting="Hello!", tools="query")

        # Should default to query-only
        client = qc.client()
        prompt = client.system_prompt

        assert "Filtering and Sorting Data" not in prompt
        assert "Answering Questions About Data" in prompt

    def test_client_can_override_initialization_tools(self, sample_df):
        """Test that client() can override tools set at initialization."""
        qc = QueryChat(sample_df, "test_table", greeting="Hello!", tools="query")

        # Override to include update
        client = qc.client(tools=("update", "query"))
        prompt = client.system_prompt

        assert "Filtering and Sorting Data" in prompt
        assert "Answering Questions About Data" in prompt


class TestConsoleMethod:
    """Tests for QueryChat.console() method."""

    def test_console_defaults_to_query_only(self, sample_df):
        """Test that console() defaults to query-only tools."""
        with patch.object(chatlas.Chat, "console"):
            qc = QueryChat(sample_df, "test_table", greeting="Hello!")

            qc.console()

            # Check the console client's system prompt
            prompt = qc._client_console.system_prompt
            assert "Filtering and Sorting Data" not in prompt
            assert "Answering Questions About Data" in prompt

    @patch.object(chatlas.Chat, "console")
    def test_console_persists_across_calls(self, mock_console, sample_df):
        """Test that console() persists the same client across calls."""
        qc = QueryChat(sample_df, "test_table", greeting="Hello!")

        qc.console()
        first_client = qc._client_console

        qc.console()
        second_client = qc._client_console

        # Should be the same instance
        assert first_client is second_client

        # Should have been called twice (once per console() call)
        assert mock_console.call_count == 2  # noqa: PLR2004

    def test_console_new_creates_fresh_client(self, sample_df):
        """Test that console(new=True) creates a fresh client."""
        with patch.object(chatlas.Chat, "console"):
            qc = QueryChat(sample_df, "test_table", greeting="Hello!")

            qc.console()
            first_client = qc._client_console

            qc.console(new=True)
            second_client = qc._client_console

            # Should be different instances
            assert first_client is not second_client

    def test_console_can_specify_tools(self, sample_df):
        """Test that console() can specify tools."""
        with patch.object(chatlas.Chat, "console"):
            qc = QueryChat(sample_df, "test_table", greeting="Hello!")

            qc.console(tools=("update", "query"))

            # Check the console client includes both tools
            prompt = qc._client_console.system_prompt
            assert "Filtering and Sorting Data" in prompt
            assert "Answering Questions About Data" in prompt


class TestPromptConditionalSections:
    """Tests for conditional tool sections in system prompt."""

    def test_prompt_includes_both_tools_by_default(self, sample_df):
        """Test that system prompt includes both tool sections by default."""
        qc = QueryChat(sample_df, "test_table", greeting="Hello!")

        prompt = qc.system_prompt

        assert "Filtering and Sorting Data" in prompt
        assert "Answering Questions About Data" in prompt
        assert "querychat_update_dashboard" in prompt
        assert "querychat_query" in prompt

    def test_prompt_excludes_update_when_query_only(self, sample_df):
        """Test that system prompt excludes update section with query-only tools."""
        qc = QueryChat(sample_df, "test_table", greeting="Hello!", tools="query")

        prompt = qc.system_prompt

        assert "Filtering and Sorting Data" not in prompt
        assert "Answering Questions About Data" in prompt

    def test_prompt_excludes_query_when_update_only(self, sample_df):
        """Test that system prompt excludes query section with update-only tools."""
        qc = QueryChat(sample_df, "test_table", greeting="Hello!", tools="update")

        prompt = qc.system_prompt

        assert "Filtering and Sorting Data" in prompt
        assert "Answering Questions About Data" not in prompt

    def test_prompt_assembly_respects_client_tools(self, sample_df):
        """Test that _assemble_system_prompt respects tools parameter."""
        qc = QueryChat(sample_df, "test_table", greeting="Hello!")

        # Test with query-only
        prompt_query = qc._assemble_system_prompt(tools="query")
        assert "Answering Questions About Data" in prompt_query
        assert "Filtering and Sorting Data" not in prompt_query

        # Test with update-only
        prompt_update = qc._assemble_system_prompt(tools="update")
        assert "Filtering and Sorting Data" in prompt_update
        assert "Answering Questions About Data" not in prompt_update


class TestBackwardCompatibility:
    """Tests for backward compatibility with existing code."""

    def test_default_tools_maintain_current_behavior(self, sample_df):
        """Test that default tools parameter maintains current behavior."""
        # Without tools parameter, should include both tools (like before)
        qc = QueryChat(sample_df, "test_table", greeting="Hello!")

        assert qc.tools == ("update", "query")

        prompt = qc.system_prompt
        assert "Filtering and Sorting Data" in prompt
        assert "Answering Questions About Data" in prompt

    def test_existing_initialization_still_works(self, sample_df):
        """Test that existing QueryChat initialization patterns still work."""
        # This should work exactly as before
        qc = QueryChat(
            data_source=sample_df,
            table_name="test_table",
            greeting="Hello!",
            data_description="Test data",
            extra_instructions="Test instructions",
        )

        assert qc is not None
        assert qc.id == "test_table"
        assert qc.tools == ("update", "query")
