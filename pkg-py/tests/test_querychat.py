import os
from unittest.mock import patch

import ibis
import pandas as pd
import polars as pl
import pytest
from querychat import QueryChat
from querychat._datasource import IbisSource, PolarsLazySource
from querychat._querychat_core import GREETING_MARKER, build_greeting_prompt


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


def test_generate_greeting_uses_querychat_system_prompt(sample_df):
    """generate_greeting() should use the dataset-aware querychat system prompt."""
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
    result = qc._data_sources["test_table"].execute_query("SELECT * FROM test_table WHERE id = 2")
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
        result = qc._data_sources["test_table"].execute_query("SELECT * FROM test_table WHERE id = 2")
        assert isinstance(result, ibis.Table)

        # Execute to verify results
        executed = result.execute()
        assert len(executed) == 1
        assert executed["name"].iloc[0] == "Bob"
    finally:
        conn.disconnect()


def test_build_greeting_prompt_single_table_includes_schema(sample_df):
    """Single table with greeting_tables=None loads schema automatically."""
    import narwhals.stable.v1 as nw
    from querychat._datasource import DataFrameSource

    source = DataFrameSource(nw.from_native(sample_df), "people")
    prompt = build_greeting_prompt(
        data_sources={"people": source},
        categorical_threshold=20,
        greeting_tables=None,
    )
    assert prompt.startswith(GREETING_MARKER)
    assert "<schema>" in prompt
    assert "people" in prompt  # schema content references table


def test_build_greeting_prompt_multi_table_no_signal_omits_schema():
    """Multi-table with greeting_tables=None omits schema, adds explorer hint."""
    import narwhals.stable.v1 as nw
    from querychat._datasource import DataFrameSource

    sources = {
        "orders": DataFrameSource(nw.from_native(pd.DataFrame({"id": [1]})), "orders"),
        "customers": DataFrameSource(nw.from_native(pd.DataFrame({"id": [1]})), "customers"),
    }
    prompt = build_greeting_prompt(
        data_sources=sources,
        categorical_threshold=20,
        greeting_tables=None,
    )
    assert prompt.startswith(GREETING_MARKER)
    assert "<schema>" not in prompt
    # Should encourage exploration of available data
    assert "available" in prompt.lower() or "explore" in prompt.lower()


def test_build_greeting_prompt_explicit_tables_includes_only_those():
    """greeting_tables list loads schema for specified tables only."""
    import narwhals.stable.v1 as nw
    from querychat._datasource import DataFrameSource

    sources = {
        "orders": DataFrameSource(nw.from_native(pd.DataFrame({"amount": [10.0]})), "orders"),
        "customers": DataFrameSource(nw.from_native(pd.DataFrame({"name": ["Alice"]})), "customers"),
    }
    prompt = build_greeting_prompt(
        data_sources=sources,
        categorical_threshold=20,
        greeting_tables=["orders"],
    )
    assert prompt.startswith(GREETING_MARKER)
    assert "<schema>" in prompt
    assert "orders" in prompt
    # customers schema should not appear (only the orders schema section)
    # The prompt should contain "orders" but we check for column content distinction
    assert "amount" in prompt  # orders column
    assert "name" not in prompt  # customers column excluded


def test_build_greeting_prompt_true_includes_all_tables():
    """greeting_tables=True loads schema for all tables."""
    import narwhals.stable.v1 as nw
    from querychat._datasource import DataFrameSource

    sources = {
        "orders": DataFrameSource(nw.from_native(pd.DataFrame({"amount": [10.0]})), "orders"),
        "customers": DataFrameSource(nw.from_native(pd.DataFrame({"name": ["Alice"]})), "customers"),
    }
    prompt = build_greeting_prompt(
        data_sources=sources,
        categorical_threshold=20,
        greeting_tables=True,
    )
    assert prompt.startswith(GREETING_MARKER)
    assert "<schema>" in prompt
    assert "amount" in prompt  # orders column
    assert "name" in prompt  # customers column


def test_build_greeting_prompt_false_omits_schema_adds_explorer():
    """greeting_tables=False skips schema entirely and adds explorer hint."""
    import narwhals.stable.v1 as nw
    from querychat._datasource import DataFrameSource

    source = DataFrameSource(nw.from_native(pd.DataFrame({"id": [1]})), "t")
    prompt = build_greeting_prompt(
        data_sources={"t": source},
        categorical_threshold=20,
        greeting_tables=False,
    )
    assert prompt.startswith(GREETING_MARKER)
    assert "<schema>" not in prompt
    assert "available" in prompt.lower() or "explore" in prompt.lower()


def test_generate_greeting_embeds_schema_for_single_table(sample_df):
    """generate_greeting() sends schema-embedded prompt for a single table."""
    qc = QueryChat(data_source=sample_df, table_name="people")
    seen: dict[str, str] = {}

    def fake_chat(self, prompt, *args, **kwargs):
        seen["prompt"] = prompt
        seen["system_prompt"] = self.system_prompt or ""
        return "Hello!"

    with patch("chatlas.Chat.chat", fake_chat):
        result = qc.generate_greeting()

    assert result == "Hello!"
    assert seen["prompt"].startswith(GREETING_MARKER)
    assert "<schema>" in seen["prompt"]


def test_generate_greeting_omits_schema_for_multi_table_default():
    """generate_greeting() with no greeting_tables omits schema for multi-table."""
    qc = QueryChat()
    qc.add_table(pd.DataFrame({"a": [1]}), "t1")
    qc.add_table(pd.DataFrame({"b": [2]}), "t2")
    seen: dict[str, str] = {}

    def fake_chat(self, prompt, *args, **kwargs):
        seen["prompt"] = prompt
        return "Hello!"

    with patch("chatlas.Chat.chat", fake_chat):
        qc.generate_greeting()

    assert seen["prompt"].startswith(GREETING_MARKER)
    assert "<schema>" not in seen["prompt"]


def test_generate_greeting_respects_greeting_tables_param(sample_df):
    """generate_greeting() includes schema for tables named in greeting_tables."""
    qc = QueryChat(greeting_tables=["people"])
    qc.add_table(sample_df, "people")
    qc.add_table(pd.DataFrame({"x": [1]}), "other")
    seen: dict[str, str] = {}

    def fake_chat(self, prompt, *args, **kwargs):
        seen["prompt"] = prompt
        return "Hi!"

    with patch("chatlas.Chat.chat", fake_chat):
        qc.generate_greeting()

    assert seen["prompt"].startswith(GREETING_MARKER)
    assert "<schema>" in seen["prompt"]
    # only people schema present: people has 'name', 'age'; other has 'x'
    assert "age" in seen["prompt"]
    assert "x" not in seen["prompt"]
