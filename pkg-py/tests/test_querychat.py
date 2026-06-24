import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import ibis
import pandas as pd
import polars as pl
import pytest
from querychat import QueryChat
from querychat._datasource import IbisSource, PolarsLazySource
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
    """Create a sample pandas DataFrame for testing."""
    return pd.DataFrame(
        {
            "id": [1, 2, 3],
            "name": ["Alice", "Bob", "Charlie"],
            "age": [25, 30, 35],
        },
    )


def test_querychat_init(sample_df):
    """Test that QueryChat (Express mode) initializes correctly."""
    qc = QueryChat(
        data_source=sample_df,
        table_name="test_table",
        greeting="Hello!",
    )

    # Verify basic attributes are set
    assert qc is not None
    assert qc.id == "querychat_test_table"

    # Even without server initialization, we should be able to query the data source
    result = qc._data_sources["test_table"].execute_query(
        "SELECT * FROM test_table WHERE id = 2",
    )

    assert len(result) == 1
    # Result is now native pandas DataFrame
    assert result.iloc[0]["name"] == "Bob"


def test_querychat_custom_id(sample_df):
    """Test that QueryChat accepts custom ID."""
    qc = QueryChat(
        data_source=sample_df,
        table_name="test_table",
        id="custom_id",
        greeting="Hello!",
    )

    assert qc.id == "custom_id"


def test_querychat_client_has_system_prompt(sample_df):
    """
    Test that the client returned by .client() has a system prompt set.

    Regression test for issue #187: the system prompt was missing because
    _client.system_prompt wasn't being set during initialization.
    """
    qc = QueryChat(
        data_source=sample_df,
        table_name="test_table",
        greeting="Hello!",
    )

    # The client() method should return a chat with the system prompt set
    client = qc.client()
    assert client.system_prompt is not None
    assert len(client.system_prompt) > 0

    # The system_prompt should contain the table name since it includes schema info
    assert "test_table" in client.system_prompt

    # The system_prompt property should also return the prompt with table info
    assert qc.system_prompt is not None
    assert "test_table" in qc.system_prompt


def test_generate_greeting_uses_greeting_system_prompt(sample_df):
    """generate_greeting() should use the lean greeting prompt, not the main query prompt."""
    qc = QueryChat(
        data_source=sample_df,
        table_name="test_table",
        greeting="Hello!",
    )
    seen: dict[str, str | None] = {}

    def fake_chat(self, *args, **kwargs):
        seen["system_prompt"] = self.system_prompt
        return "Hello from querychat"

    with patch("chatlas.Chat.chat", fake_chat):
        greeting = qc.generate_greeting()

    assert greeting == "Hello from querychat"
    assert seen["system_prompt"] is not None
    assert "test_table" in seen["system_prompt"]
    assert "data dashboard chatbot" not in seen["system_prompt"]


def test_generate_greeting_does_not_register_querychat_tools(sample_df):
    """generate_greeting() should use a plain chat client without dashboard/query tools."""
    qc = QueryChat(
        data_source=sample_df,
        table_name="test_table",
        greeting="Hello!",
    )

    with (
        patch("chatlas.Chat.register_tool") as register_tool,
        patch("chatlas.Chat.chat", return_value="Hello from querychat"),
    ):
        greeting = qc.generate_greeting()

    assert greeting == "Hello from querychat"
    register_tool.assert_not_called()


def test_querychat_with_polars_lazyframe():
    """Test that QueryChat accepts a Polars LazyFrame."""
    lf = pl.LazyFrame(
        {
            "id": [1, 2, 3],
            "name": ["Alice", "Bob", "Charlie"],
            "age": [25, 30, 35],
        }
    )

    qc = QueryChat(
        data_source=lf,
        table_name="test_table",
        greeting="Hello!",
    )

    # Should have created a PolarsLazySource
    assert isinstance(qc._data_sources["test_table"], PolarsLazySource)

    # Query should return a native polars LazyFrame
    result = qc._data_sources["test_table"].execute_query(
        "SELECT * FROM test_table WHERE id = 2"
    )
    assert isinstance(result, pl.LazyFrame)

    # Collect to verify
    collected = result.collect()
    assert len(collected) == 1
    assert collected.item(0, "name") == "Bob"


def test_querychat_with_ibis_table():
    """Test that QueryChat accepts an Ibis Table."""
    conn = ibis.duckdb.connect()
    try:
        conn.create_table(
            "test_table",
            {
                "id": [1, 2, 3],
                "name": ["Alice", "Bob", "Charlie"],
                "age": [25, 30, 35],
            },
        )
        ibis_table = conn.table("test_table")

        qc = QueryChat(
            data_source=ibis_table,
            table_name="test_table",
            greeting="Hello!",
        )

        # Should have created an IbisSource
        assert isinstance(qc._data_sources["test_table"], IbisSource)

        # Query should return an ibis.Table
        result = qc._data_sources["test_table"].execute_query(
            "SELECT * FROM test_table WHERE id = 2"
        )
        assert isinstance(result, ibis.Table)

        # Execute to verify results
        executed = result.execute()
        assert len(executed) == 1
        assert executed["name"].iloc[0] == "Bob"
    finally:
        conn.disconnect()


@pytest.fixture
def sqlite_engine():
    """SQLite engine with two tables for add_tables greeting tests."""
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")  # noqa: SIM115
    temp_db.close()
    engine = create_engine(f"sqlite:///{temp_db.name}")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE orders (id INTEGER, amount REAL)"))
        conn.execute(text("CREATE TABLE customers (id INTEGER, name TEXT)"))
        conn.execute(text("INSERT INTO orders VALUES (1, 100.0), (2, 200.0)"))
        conn.execute(text("INSERT INTO customers VALUES (1, 'Alice'), (2, 'Bob')"))
    yield engine
    engine.dispose()
    Path(temp_db.name).unlink()


def test_greeter_tables_contains_constructor_table(sample_df):
    """Constructor table is always present in greeter.tables."""
    qc = QueryChat(data_source=sample_df, table_name="test_table")
    assert "test_table" in qc.greeter.tables


def test_constructor_greeting_survives_greeter_mutations(sample_df):
    """Setting greeter.tables or greeter.prompt must not clear qc.greeting."""
    qc = QueryChat(data_source=sample_df, table_name="test_table", greeting="Hello!")
    assert qc.greeting == "Hello!"

    qc.greeter.tables = ["test_table"]
    assert qc.greeting == "Hello!"

    qc.greeter.prompt = "Custom prompt"
    assert qc.greeting == "Hello!"


def test_add_table_include_in_greeting(sample_df):
    """add_table with include_in_greeting=True adds the name; default False does not."""
    qc = QueryChat()
    qc.add_table(sample_df, "base_table", include_in_greeting=False)

    extra = pd.DataFrame({"x": [1, 2]})
    qc.add_table(extra, "included", include_in_greeting=True)

    extra2 = pd.DataFrame({"y": [3, 4]})
    qc.add_table(extra2, "excluded")

    assert "included" in qc.greeter.tables
    assert "excluded" not in qc.greeter.tables
    assert "base_table" not in qc.greeter.tables


def test_add_tables_include_in_greeting_true(sqlite_engine):
    """add_tables with include_in_greeting=True adds all tables to greeter."""
    qc = QueryChat()
    qc.add_tables(sqlite_engine, include_in_greeting=True)
    assert "orders" in qc.greeter.tables
    assert "customers" in qc.greeter.tables


def test_add_tables_include_in_greeting_false(sqlite_engine):
    """add_tables with include_in_greeting=False (default) adds no tables to greeter."""
    qc = QueryChat()
    qc.add_tables(sqlite_engine, include_in_greeting=False)
    assert "orders" not in qc.greeter.tables
    assert "customers" not in qc.greeter.tables


def test_add_tables_include_in_greeting_list(sqlite_engine):
    """add_tables with a list only adds the named subset to greeter.tables."""
    qc = QueryChat()
    qc.add_tables(sqlite_engine, include_in_greeting=["orders"])
    assert "orders" in qc.greeter.tables
    assert "customers" not in qc.greeter.tables


def test_add_tables_include_in_greeting_str(sqlite_engine):
    """add_tables accepts a bare table-name string (parity with R)."""
    qc = QueryChat()
    qc.add_tables(sqlite_engine, include_in_greeting="orders")
    assert "orders" in qc.greeter.tables
    assert "customers" not in qc.greeter.tables


def test_add_tables_include_in_greeting_invalid_type(sqlite_engine):
    """add_tables rejects non-bool, non-string include_in_greeting."""
    qc = QueryChat()
    with pytest.raises(TypeError, match="include_in_greeting"):
        qc.add_tables(sqlite_engine, include_in_greeting=1)  # type: ignore[arg-type]


def test_generate_greeting_sets_greeting_and_returns_text(sample_df):
    """generate_greeting() returns the mocked text and sets qc.greeting."""
    qc = QueryChat(data_source=sample_df, table_name="test_table")
    seen: dict[str, str | None] = {}

    def fake_chat(self, *args, **kwargs):
        seen["system_prompt"] = self.system_prompt
        return "Generated greeting"

    with patch("chatlas.Chat.chat", fake_chat):
        result = qc.generate_greeting()

    assert result == "Generated greeting"
    assert qc.greeting == "Generated greeting"
    assert seen["system_prompt"] is not None
    assert "test_table" in seen["system_prompt"]
    assert "data dashboard chatbot" not in seen["system_prompt"]


def test_generate_greeting_with_empty_tables(sample_df):
    """Clearing greeter.tables produces a generic greeting without raising."""
    qc = QueryChat(data_source=sample_df, table_name="test_table")
    qc.greeter.tables = []

    with patch("chatlas.Chat.chat", return_value="Generic greeting"):
        result = qc.generate_greeting()

    assert result == "Generic greeting"
    assert qc.greeting == "Generic greeting"
