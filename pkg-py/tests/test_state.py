"""Tests for AppState and message processing."""

import os
from typing import Any
from unittest.mock import MagicMock

import narwhals.stable.v1 as nw
import pandas as pd
import pytest
from querychat._datasource import DataFrameSource
from querychat._querychat_core import (
    AppState,
    create_app_state,
    stream_response,
)


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
    pdf = pd.DataFrame(
        {
            "id": [1, 2, 3],
            "name": ["Alice", "Bob", "Charlie"],
            "age": [25, 30, 35],
        },
    )
    return nw.from_native(pdf)


@pytest.fixture
def data_source(sample_df):
    return DataFrameSource(sample_df, "test_table")


@pytest.fixture
def mock_client():
    return MagicMock()


class TestAppState:
    def test_initial_state(self, data_source, mock_client):
        state = AppState(data_source=data_source, client=mock_client)
        assert state.data_source is data_source
        assert state.client is mock_client
        assert state.greeting is None
        assert state.sql is None
        assert state.title is None

    def test_with_greeting(self, data_source, mock_client):
        state = AppState(
            data_source=data_source, client=mock_client, greeting="Welcome!"
        )
        assert state.greeting == "Welcome!"

    def test_update_dashboard(self, data_source, mock_client):
        state = AppState(data_source=data_source, client=mock_client)
        state.update_dashboard(
            {"query": "SELECT * FROM test_table", "title": "All Data"}
        )
        assert state.sql == "SELECT * FROM test_table"
        assert state.title == "All Data"

    def test_reset_dashboard(self, data_source, mock_client):
        state = AppState(data_source=data_source, client=mock_client)
        state.sql = "SELECT * FROM test_table"
        state.title = "Test"
        state.reset_dashboard()
        assert state.sql is None
        assert state.title is None

    def test_get_current_data_without_sql(self, data_source, mock_client, sample_df):
        state = AppState(data_source=data_source, client=mock_client)
        result = state.get_current_data()
        # Result is now native pandas DataFrame
        pd.testing.assert_frame_equal(result, sample_df.to_pandas())

    def test_get_current_data_with_valid_sql(self, data_source, mock_client):
        state = AppState(data_source=data_source, client=mock_client)
        state.sql = "SELECT * FROM test_table WHERE age > 25"
        result = state.get_current_data()
        assert len(result) == 2
        # Result is now native pandas DataFrame
        assert result["name"].tolist() == ["Bob", "Charlie"]

    def test_get_current_data_with_invalid_sql_resets(
        self, data_source, mock_client, sample_df
    ):
        state = AppState(data_source=data_source, client=mock_client)
        state.sql = "INVALID SQL QUERY"
        state.title = "Will be cleared"
        result = state.get_current_data()
        # Result is now native pandas DataFrame
        pd.testing.assert_frame_equal(result, sample_df.to_pandas())
        assert state.sql is None
        assert state.title is None
        assert state.error is not None
        assert "Query syntax error:" in state.error

    def test_error_cleared_on_successful_query(self, data_source, mock_client):
        state = AppState(data_source=data_source, client=mock_client)
        state.error = "Previous error"
        state.sql = "SELECT * FROM test_table WHERE age > 25"
        result = state.get_current_data()
        assert len(result) == 2
        assert state.error is None

    def test_error_cleared_on_update_dashboard(self, data_source, mock_client):
        state = AppState(data_source=data_source, client=mock_client)
        state.error = "Previous error"
        state.update_dashboard({"query": "SELECT * FROM test_table", "title": "Test"})
        assert state.error is None

    def test_error_cleared_on_reset_dashboard(self, data_source, mock_client):
        state = AppState(data_source=data_source, client=mock_client)
        state.error = "Previous error"
        state.reset_dashboard()
        assert state.error is None

    def test_get_display_sql_without_sql(self, data_source, mock_client):
        state = AppState(data_source=data_source, client=mock_client)
        assert state.get_display_sql() == "SELECT * FROM test_table"

    def test_get_display_sql_with_sql(self, data_source, mock_client):
        state = AppState(data_source=data_source, client=mock_client)
        state.sql = "SELECT name FROM test_table"
        assert state.get_display_sql() == "SELECT name FROM test_table"


class TestCreateAppState:
    def test_creates_state_with_callbacks(self, data_source):
        callback_data: dict[str, Any] = {}

        def client_factory(update_callback, reset_callback):
            # Store the callbacks for testing
            callback_data["update_callback"] = update_callback
            callback_data["reset_callback"] = reset_callback
            return MagicMock()

        state = create_app_state(data_source, client_factory, greeting="Welcome!")
        assert state.greeting == "Welcome!"
        assert state.data_source is data_source

        # Test that the update callback works
        callback_data["update_callback"]({"query": "SELECT 1", "title": "Test"})
        assert state.sql == "SELECT 1"
        assert state.title == "Test"

        # Test that the reset callback works
        callback_data["reset_callback"]()
        assert state.sql is None
        assert state.title is None


class TestStreamResponse:
    def test_stream_response_yields_strings(self):
        mock_client = MagicMock()
        mock_client.stream.return_value = iter(["Hello", " world"])

        chunks = list(stream_response(mock_client, "Test prompt"))

        assert len(chunks) == 2
        assert chunks[0] == "Hello"
        assert chunks[1] == " world"
        mock_client.stream.assert_called_once_with(
            "Test prompt", echo="none", content="all"
        )

    def test_stream_response_empty_stream(self):
        mock_client = MagicMock()
        mock_client.stream.return_value = iter([])

        chunks = list(stream_response(mock_client, "Test prompt"))

        assert len(chunks) == 0
        mock_client.stream.assert_called_once()

    def test_stream_response_single_chunk(self):
        mock_client = MagicMock()
        mock_client.stream.return_value = iter(["Single response"])

        chunks = list(stream_response(mock_client, "Test prompt"))

        assert len(chunks) == 1
        assert chunks[0] == "Single response"

    def test_stream_response_propagates_exception(self):
        mock_client = MagicMock()
        mock_client.stream.side_effect = RuntimeError("API error")

        with pytest.raises(RuntimeError, match="API error"):
            list(stream_response(mock_client, "Test prompt"))

    def test_stream_response_handles_generator_exception(self):
        mock_client = MagicMock()

        def failing_generator():
            yield "First chunk"
            raise ConnectionError("Stream interrupted")

        mock_client.stream.return_value = failing_generator()

        with pytest.raises(ConnectionError, match="Stream interrupted"):
            list(stream_response(mock_client, "Test prompt"))


class TestGetDisplayMessages:
    def test_empty_turns(self, data_source, mock_client):
        mock_client.get_turns.return_value = []
        state = AppState(data_source=data_source, client=mock_client)
        assert state.get_display_messages() == []

    def test_user_message(self, data_source, mock_client):
        from chatlas import Turn

        user_turn = Turn(role="user", contents="Hello world")
        mock_client.get_turns.return_value = [user_turn]
        state = AppState(data_source=data_source, client=mock_client)
        messages = state.get_display_messages()
        assert len(messages) == 1
        assert messages[0] == {"role": "user", "content": "Hello world"}

    def test_assistant_message(self, data_source, mock_client):
        from chatlas import Turn

        assistant_turn = Turn(role="assistant", contents="Hi there!")
        mock_client.get_turns.return_value = [assistant_turn]
        state = AppState(data_source=data_source, client=mock_client)
        messages = state.get_display_messages()
        assert len(messages) == 1
        assert messages[0] == {"role": "assistant", "content": "Hi there!"}

    def test_multiple_messages(self, data_source, mock_client):
        from chatlas import Turn

        turns = [
            Turn(role="user", contents="Question"),
            Turn(role="assistant", contents="Answer"),
        ]
        mock_client.get_turns.return_value = turns
        state = AppState(data_source=data_source, client=mock_client)
        messages = state.get_display_messages()
        assert len(messages) == 2
        assert messages[0] == {"role": "user", "content": "Question"}
        assert messages[1] == {"role": "assistant", "content": "Answer"}


class TestTypedDicts:
    def test_app_state_dict_structure(self):
        from querychat._querychat_core import AppStateDict

        state: AppStateDict = {
            "sql": "SELECT * FROM test",
            "title": "Test",
            "error": None,
            "turns": [
                {"role": "user", "contents": [{"content_type": "text", "text": "hi"}]}
            ],
        }
        assert state["sql"] == "SELECT * FROM test"
        assert len(state["turns"]) == 1


class TestAppStateSerialization:
    def test_to_dict_includes_turns(self, data_source, mock_client):
        from chatlas import Turn

        user_turn = Turn(role="user", contents="Hello")
        assistant_turn = Turn(role="assistant", contents="Hi!")
        mock_client.get_turns.return_value = [user_turn, assistant_turn]

        state = AppState(data_source=data_source, client=mock_client)
        state.sql = "SELECT * FROM test"
        state.title = "Test"

        result = state.to_dict()

        assert result["sql"] == "SELECT * FROM test"
        assert result["title"] == "Test"
        assert "turns" in result
        assert len(result["turns"]) == 2
        assert result["turns"][0]["role"] == "user"
        assert result["turns"][1]["role"] == "assistant"
        assert "chat_history" not in result

    def test_to_dict_empty_turns(self, data_source, mock_client):
        mock_client.get_turns.return_value = []
        state = AppState(data_source=data_source, client=mock_client)
        result = state.to_dict()
        assert result["turns"] == []


class TestAppStateDeserialization:
    def test_update_from_dict_restores_turns(self, data_source, mock_client):
        state = AppState(data_source=data_source, client=mock_client)

        state.update_from_dict(
            {
                "sql": "SELECT name FROM test",
                "title": "Names Only",
                "error": None,
                "turns": [
                    {
                        "role": "user",
                        "contents": [{"content_type": "text", "text": "Show names"}],
                    },
                    {
                        "role": "assistant",
                        "contents": [
                            {"content_type": "text", "text": "Here are names"}
                        ],
                    },
                ],
            }
        )

        assert state.sql == "SELECT name FROM test"
        assert state.title == "Names Only"
        mock_client.set_turns.assert_called_once()
        turns_arg = mock_client.set_turns.call_args[0][0]
        assert len(turns_arg) == 2
        assert turns_arg[0].role == "user"
        assert turns_arg[1].role == "assistant"

    def test_update_from_dict_empty_turns(self, data_source, mock_client):
        state = AppState(data_source=data_source, client=mock_client)
        state.update_from_dict({"sql": None, "title": None, "error": None, "turns": []})
        mock_client.set_turns.assert_called_with([])
