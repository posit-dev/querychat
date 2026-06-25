"""Tests for AppState and message processing."""

import os
from typing import Any
from unittest.mock import MagicMock

import narwhals.stable.v1 as nw
import pandas as pd
import pytest
from querychat import QueryChat
from querychat._datasource import DataFrameSource
from querychat._querychat_base import StateDictQueryChat
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
        state = AppState(data_sources={"test_table": data_source}, client=mock_client)
        assert state.data_sources["test_table"] is data_source
        assert state.client is mock_client
        assert state.greeting is None
        assert state.active_table == "test_table"
        assert state.sql is None
        assert state.title is None

    def test_with_greeting(self, data_source, mock_client):
        state = AppState(
            data_sources={"test_table": data_source},
            client=mock_client,
            greeting="Welcome!",
        )
        assert state.greeting == "Welcome!"

    def test_update_dashboard(self, data_source, mock_client):
        state = AppState(data_sources={"test_table": data_source}, client=mock_client)
        state.update_dashboard(
            {
                "table": "test_table",
                "query": "SELECT * FROM test_table",
                "title": "All Data",
            }
        )
        assert state.active_table == "test_table"
        assert state.sql == "SELECT * FROM test_table"
        assert state.title == "All Data"

    def test_reset_dashboard(self, data_source, mock_client):
        state = AppState(data_sources={"test_table": data_source}, client=mock_client)
        state.sql = "SELECT * FROM test_table"
        state.title = "Test"
        state.reset_dashboard()
        assert state.active_table == "test_table"
        assert state.sql is None
        assert state.title is None

    def test_get_current_data_without_sql(self, data_source, mock_client, sample_df):
        state = AppState(data_sources={"test_table": data_source}, client=mock_client)
        result = state.get_current_data()
        # Result is now native pandas DataFrame
        pd.testing.assert_frame_equal(result, sample_df.to_pandas())

    def test_get_current_data_with_valid_sql(self, data_source, mock_client):
        state = AppState(data_sources={"test_table": data_source}, client=mock_client)
        state.sql = "SELECT * FROM test_table WHERE age > 25"
        result = state.get_current_data()
        assert len(result) == 2
        # Result is now native pandas DataFrame
        assert result["name"].tolist() == ["Bob", "Charlie"]

    def test_get_current_data_with_invalid_sql_resets(
        self, data_source, mock_client, sample_df
    ):
        state = AppState(data_sources={"test_table": data_source}, client=mock_client)
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
        state = AppState(data_sources={"test_table": data_source}, client=mock_client)
        state.error = "Previous error"
        state.sql = "SELECT * FROM test_table WHERE age > 25"
        result = state.get_current_data()
        assert len(result) == 2
        assert state.error is None

    def test_get_current_data_without_sql_preserves_existing_error(
        self, data_source, mock_client, sample_df
    ):
        state = AppState(data_sources={"test_table": data_source}, client=mock_client)
        state.error = "Previous error"

        result = state.get_current_data()

        pd.testing.assert_frame_equal(result, sample_df.to_pandas())
        assert state.error == "Previous error"

    def test_error_cleared_on_update_dashboard(self, data_source, mock_client):
        state = AppState(data_sources={"test_table": data_source}, client=mock_client)
        state.error = "Previous error"
        state.update_dashboard(
            {
                "table": "test_table",
                "query": "SELECT * FROM test_table",
                "title": "Test",
            }
        )
        assert state.error is None

    def test_get_current_data_uses_query_executor_for_multi_table_dashboard_sql(
        self, mock_client
    ):
        orders = pd.DataFrame(
            {
                "id": [1, 2, 3],
                "customer_id": [101, 102, 101],
                "amount": [100.0, 200.0, 150.0],
            }
        )
        customers = pd.DataFrame(
            {
                "id": [101, 102],
                "state": ["CA", "NY"],
            }
        )
        qc = QueryChat(orders, "orders")
        qc.add_table(customers, "customers")

        state = AppState(
            data_sources=dict(qc._data_sources),
            client=mock_client,
            query_executor=qc._require_query_executor("test"),
        )
        state.update_dashboard(
            {
                "table": "orders",
                "query": (
                    "SELECT orders.* "
                    "FROM orders "
                    "JOIN customers ON orders.customer_id = customers.id "
                    "WHERE customers.state = 'CA'"
                ),
                "title": "California orders",
            }
        )

        result = state.get_current_data()

        assert result["id"].tolist() == [1, 3]
        assert state.error is None

    def test_get_current_data_with_invalid_sql_falls_back_to_active_table(
        self, mock_client
    ):
        orders = pd.DataFrame(
            {
                "id": [1, 2, 3],
                "customer_id": [101, 102, 101],
                "amount": [100.0, 200.0, 150.0],
            }
        )
        customers = pd.DataFrame(
            {
                "id": [101, 102],
                "state": ["CA", "NY"],
            }
        )
        qc = QueryChat(orders, "orders")
        qc.add_table(customers, "customers")

        state = AppState(
            data_sources=dict(qc._data_sources),
            client=mock_client,
            query_executor=qc._require_query_executor("test"),
        )
        state.update_dashboard(
            {
                "table": "customers",
                "query": "SELECT missing_column FROM customers",
                "title": "Broken customer query",
            }
        )

        result = state.get_current_data()

        assert result["id"].tolist() == [101, 102]
        assert result["state"].tolist() == ["CA", "NY"]
        assert state.active_table == "customers"
        assert state.sql is None
        assert state.title is None
        assert state.error is not None

    def test_error_cleared_on_reset_dashboard(self, data_source, mock_client):
        state = AppState(data_sources={"test_table": data_source}, client=mock_client)
        state.error = "Previous error"
        state.reset_dashboard()
        assert state.error is None

    def test_get_display_sql_without_sql(self, data_source, mock_client):
        state = AppState(data_sources={"test_table": data_source}, client=mock_client)
        assert state.get_display_sql() == "SELECT * FROM test_table"

    def test_get_display_sql_with_sql(self, data_source, mock_client):
        state = AppState(data_sources={"test_table": data_source}, client=mock_client)
        state.sql = "SELECT name FROM test_table"
        assert state.get_display_sql() == "SELECT name FROM test_table"

    def test_update_dashboard_preserves_other_table_state(self, mock_client):
        """Updating table B should not clobber table A's sql/title."""
        orders = pd.DataFrame({"id": [1, 2], "amount": [100.0, 200.0]})
        customers = pd.DataFrame({"id": [101, 102], "state": ["CA", "NY"]})
        qc = QueryChat(orders, "orders")
        qc.add_table(customers, "customers")

        state = AppState(
            data_sources=dict(qc._data_sources),
            client=mock_client,
            query_executor=qc._require_query_executor("test"),
        )

        state.update_dashboard(
            {
                "table": "orders",
                "query": "SELECT * FROM orders WHERE amount > 100",
                "title": "Big orders",
            }
        )
        state.update_dashboard(
            {
                "table": "customers",
                "query": "SELECT * FROM customers WHERE state = 'CA'",
                "title": "CA customers",
            }
        )

        # orders' filter should still be intact
        assert (
            state._table_states["orders"]["sql"]
            == "SELECT * FROM orders WHERE amount > 100"
        )
        assert state._table_states["orders"]["title"] == "Big orders"
        # customers is now active
        assert state.active_table == "customers"
        assert state.sql == "SELECT * FROM customers WHERE state = 'CA'"

    def test_to_dict_includes_per_table_states(self, mock_client):
        """to_dict() should include all tables' sql/title/error, not just the active one."""
        orders = pd.DataFrame({"id": [1, 2], "amount": [100.0, 200.0]})
        customers = pd.DataFrame({"id": [101, 102], "state": ["CA", "NY"]})
        qc = QueryChat(orders, "orders")
        qc.add_table(customers, "customers")

        mock_client.get_turns.return_value = []
        state = AppState(
            data_sources=dict(qc._data_sources),
            client=mock_client,
            query_executor=qc._require_query_executor("test"),
        )
        state.update_dashboard(
            {
                "table": "orders",
                "query": "SELECT * FROM orders WHERE amount > 100",
                "title": "Big orders",
            }
        )
        state.update_dashboard(
            {
                "table": "customers",
                "query": "SELECT * FROM customers WHERE state = 'CA'",
                "title": "CA customers",
            }
        )

        result = state.to_dict()

        assert "table_states" in result
        assert (
            result["table_states"]["orders"]["sql"]
            == "SELECT * FROM orders WHERE amount > 100"
        )
        assert (
            result["table_states"]["customers"]["sql"]
            == "SELECT * FROM customers WHERE state = 'CA'"
        )

    def test_update_from_dict_restores_per_table_states(self, mock_client):
        """update_from_dict() should restore all tables' sql/title/error."""
        orders = pd.DataFrame({"id": [1, 2], "amount": [100.0, 200.0]})
        customers = pd.DataFrame({"id": [101, 102], "state": ["CA", "NY"]})
        qc = QueryChat(orders, "orders")
        qc.add_table(customers, "customers")

        state = AppState(
            data_sources=dict(qc._data_sources),
            client=mock_client,
            query_executor=qc._require_query_executor("test"),
        )

        state.update_from_dict(
            {
                "table": "customers",
                "sql": "SELECT * FROM customers WHERE state = 'CA'",
                "title": "CA customers",
                "error": None,
                "table_states": {
                    "orders": {
                        "sql": "SELECT * FROM orders WHERE amount > 100",
                        "title": "Big orders",
                        "error": None,
                    },
                    "customers": {
                        "sql": "SELECT * FROM customers WHERE state = 'CA'",
                        "title": "CA customers",
                        "error": None,
                    },
                },
                "turns": [],
            }
        )

        assert state.active_table == "customers"
        assert state.sql == "SELECT * FROM customers WHERE state = 'CA'"
        assert (
            state._table_states["orders"]["sql"]
            == "SELECT * FROM orders WHERE amount > 100"
        )
        assert state._table_states["orders"]["title"] == "Big orders"


class TestCreateAppState:
    def test_creates_state_with_callbacks(self, data_source):
        callback_data: dict[str, Any] = {}

        def client_factory(update_callback, reset_callback):
            # Store the callbacks for testing
            callback_data["update_callback"] = update_callback
            callback_data["reset_callback"] = reset_callback
            return MagicMock()

        state = create_app_state(
            data_sources={"test_table": data_source},
            client_factory=client_factory,
            greeting="Welcome!",
        )
        assert state.greeting == "Welcome!"
        assert state.data_sources["test_table"] is data_source

        # Test that the update callback works
        callback_data["update_callback"](
            {"table": "test_table", "query": "SELECT 1", "title": "Test"}
        )
        assert state.sql == "SELECT 1"
        assert state.title == "Test"

        # Test that the reset callback works
        callback_data["reset_callback"]("test_table")
        assert state.active_table == "test_table"
        assert state.sql is None
        assert state.title is None


class DummyStateAccessor(StateDictQueryChat[pd.DataFrame]):
    def __init__(self, qc: QueryChat):
        self._data_sources = dict(qc._data_sources)
        self._query_executor = qc._require_query_executor("test")
        self.greeting = None

    def _require_initialized(self, _method_name: str):
        pass

    def _require_query_executor(self, _method_name: str):
        return self._query_executor

    def client(self, **_kwargs):
        return MagicMock()


class TestStateDictQueryChat:
    def test_df_uses_query_executor_for_multi_table_dashboard_sql(self):
        orders = pd.DataFrame(
            {
                "id": [1, 2, 3],
                "customer_id": [101, 102, 101],
                "amount": [100.0, 200.0, 150.0],
            }
        )
        customers = pd.DataFrame(
            {
                "id": [101, 102],
                "state": ["CA", "NY"],
            }
        )
        qc = QueryChat(orders, "orders")
        qc.add_table(customers, "customers")
        accessor = DummyStateAccessor(qc)
        sql = (
            "SELECT orders.* "
            "FROM orders "
            "JOIN customers ON orders.customer_id = customers.id "
            "WHERE customers.state = 'CA'"
        )

        result = accessor.df(
            {
                "table_states": {
                    "orders": {"sql": sql, "title": "California orders", "error": None},
                    "customers": {"sql": None, "title": None, "error": None},
                },
                "table": "orders",
                "sql": sql,
                "title": "California orders",
                "error": None,
                "turns": [],
            },
            table="orders",
        )

        assert result["id"].tolist() == [1, 3]

    def test_df_uses_active_table_for_full_data_and_error_fallback(self):
        orders = pd.DataFrame(
            {
                "id": [1, 2, 3],
                "customer_id": [101, 102, 101],
                "amount": [100.0, 200.0, 150.0],
            }
        )
        customers = pd.DataFrame(
            {
                "id": [101, 102],
                "state": ["CA", "NY"],
            }
        )
        qc = QueryChat(orders, "orders")
        qc.add_table(customers, "customers")
        accessor = DummyStateAccessor(qc)

        full_result = accessor.df(
            {
                "table": "customers",
                "sql": None,
                "title": None,
                "error": None,
                "turns": [],
            },
            table="customers",
        )
        error_result = accessor.df(
            {
                "table": "customers",
                "sql": "SELECT missing_column FROM customers",
                "title": "Broken customer query",
                "error": None,
                "turns": [],
            },
            table="customers",
        )

        assert full_result["id"].tolist() == [101, 102]
        assert error_result["id"].tolist() == [101, 102]


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
        state = AppState(data_sources={"test_table": data_source}, client=mock_client)
        assert state.get_display_messages() == []

    def test_user_message(self, data_source, mock_client):
        from chatlas import Turn

        user_turn = Turn(role="user", contents="Hello world")
        mock_client.get_turns.return_value = [user_turn]
        state = AppState(data_sources={"test_table": data_source}, client=mock_client)
        messages = state.get_display_messages()
        assert len(messages) == 1
        assert messages[0] == {"role": "user", "content": "Hello world"}

    def test_assistant_message(self, data_source, mock_client):
        from chatlas import Turn

        assistant_turn = Turn(role="assistant", contents="Hi there!")
        mock_client.get_turns.return_value = [assistant_turn]
        state = AppState(data_sources={"test_table": data_source}, client=mock_client)
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
        state = AppState(data_sources={"test_table": data_source}, client=mock_client)
        messages = state.get_display_messages()
        assert len(messages) == 2
        assert messages[0] == {"role": "user", "content": "Question"}
        assert messages[1] == {"role": "assistant", "content": "Answer"}

    def test_legacy_greeting_prompt_turn_is_hidden(self, data_source, mock_client):
        """
        State serialized by older releases injected GREETING_PROMPT as a user
        turn on the shared client; it must stay hidden after restore.
        """
        from chatlas import Turn
        from querychat._querychat_core import GREETING_PROMPT

        turns = [
            Turn(role="user", contents=GREETING_PROMPT),
            Turn(role="assistant", contents="Welcome!"),
        ]
        mock_client.get_turns.return_value = turns
        state = AppState(data_sources={"test_table": data_source}, client=mock_client)
        messages = state.get_display_messages()
        assert messages == [{"role": "assistant", "content": "Welcome!"}]


class TestTypedDicts:
    def test_app_state_dict_structure(self):
        from querychat._querychat_core import AppStateDict

        state: AppStateDict = {
            "table": "test",
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

        state = AppState(data_sources={"test_table": data_source}, client=mock_client)
        state.sql = "SELECT * FROM test"
        state.title = "Test"

        result = state.to_dict()

        assert result["table"] == "test_table"
        assert result["sql"] == "SELECT * FROM test"
        assert result["title"] == "Test"
        assert "turns" in result
        assert len(result["turns"]) == 2
        assert result["turns"][0]["role"] == "user"
        assert result["turns"][1]["role"] == "assistant"
        assert "chat_history" not in result

    def test_to_dict_empty_turns(self, data_source, mock_client):
        mock_client.get_turns.return_value = []
        state = AppState(data_sources={"test_table": data_source}, client=mock_client)
        result = state.to_dict()
        assert result["turns"] == []


class TestAppStateDeserialization:
    def test_update_from_dict_restores_turns(self, data_source, mock_client):
        state = AppState(data_sources={"test_table": data_source}, client=mock_client)

        state.update_from_dict(
            {
                "table": "test_table",
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

        assert state.active_table == "test_table"
        assert state.sql == "SELECT name FROM test"
        assert state.title == "Names Only"
        mock_client.set_turns.assert_called_once()
        turns_arg = mock_client.set_turns.call_args[0][0]
        assert len(turns_arg) == 2
        assert turns_arg[0].role == "user"
        assert turns_arg[1].role == "assistant"

    def test_update_from_dict_empty_turns(self, data_source, mock_client):
        state = AppState(data_sources={"test_table": data_source}, client=mock_client)
        state.update_from_dict(
            {
                "table": "test_table",
                "sql": None,
                "title": None,
                "error": None,
                "turns": [],
            }
        )
        mock_client.set_turns.assert_called_with([])
