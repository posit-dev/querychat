import os

import ibis
import pandas as pd
import polars as pl
import pytest
from querychat import QueryChat
from querychat._datasource import IbisSource, PolarsLazySource


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
    result = qc.data_source.execute_query(
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

    # The internal _client should also have the system prompt set
    # (needed for methods like generate_greeting() that use _client directly)
    assert qc._client.system_prompt is not None
    assert "test_table" in qc._client.system_prompt


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
    assert isinstance(qc.data_source, PolarsLazySource)

    # Query should return a native polars LazyFrame
    result = qc.data_source.execute_query("SELECT * FROM test_table WHERE id = 2")
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
        assert isinstance(qc.data_source, IbisSource)

        # Query should return an ibis.Table
        result = qc.data_source.execute_query("SELECT * FROM test_table WHERE id = 2")
        assert isinstance(result, ibis.Table)

        # Execute to verify results
        executed = result.execute()
        assert len(executed) == 1
        assert executed["name"].iloc[0] == "Bob"
    finally:
        conn.disconnect()
