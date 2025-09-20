import os

import narwhals.stable.v1 as nw
import pandas as pd
import pytest

from querychat.querychat import init


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


def test_init_with_pandas_dataframe():
    """Test that init() can accept a pandas DataFrame."""
    # Create a simple pandas DataFrame
    df = pd.DataFrame(
        {
            "id": [1, 2, 3],
            "name": ["Alice", "Bob", "Charlie"],
            "age": [25, 30, 35],
        },
    )

    # Call init with the pandas DataFrame - it should not raise errors
    # The function should accept a pandas DataFrame even with the narwhals import change
    result = init(
        data_source=df,
        table_name="test_table",
        greeting="hello!",
    )

    # Verify the result is an instance of QueryChatConfig
    assert result is not None
    assert hasattr(result, "data_source")
    assert hasattr(result, "system_prompt")
    assert hasattr(result, "greeting")
    assert hasattr(result, "client")


def test_init_with_narwhals_dataframe():
    """Test that init() can accept a narwhals DataFrame."""
    # Create a pandas DataFrame and convert to narwhals
    pdf = pd.DataFrame(
        {
            "id": [1, 2, 3],
            "name": ["Alice", "Bob", "Charlie"],
            "age": [25, 30, 35],
        },
    )
    nw_df = nw.from_native(pdf)

    # Call init with the narwhals DataFrame - it should not raise errors
    result = init(
        data_source=nw_df,
        table_name="test_table",
        greeting="hello!",
    )

    # Verify the result is correctly configured
    assert result is not None
    assert hasattr(result, "data_source")
    assert hasattr(result, "system_prompt")


def test_init_with_narwhals_lazyframe_direct_query():
    """Test that init() can accept a narwhals LazyFrame and execute queries."""
    # Create a pandas DataFrame and convert to narwhals LazyFrame
    pdf = pd.DataFrame(
        {
            "id": [1, 2, 3],
            "name": ["Alice", "Bob", "Charlie"],
            "age": [25, 30, 35],
        },
    )
    nw_lazy = nw.from_native(pdf).lazy()

    # Call init with the narwhals LazyFrame
    result = init(
        data_source=nw_lazy,  # TODO(@gadebuie): Fix this type error
        table_name="test_table",
        greeting="hello!",
    )

    # Verify the result is correctly configured
    assert result is not None
    assert hasattr(result, "data_source")

    # Test that we can run a query on the data source
    query_result = result.data_source.execute_query(
        "SELECT * FROM test_table WHERE id = 2",
    )
    assert len(query_result) == 1
    assert query_result.iloc[0]["name"] == "Bob"
