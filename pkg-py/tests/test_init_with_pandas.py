import os

import narwhals.stable.v1 as nw
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


def test_init_with_pandas_dataframe():
    """Test that QueryChat() can accept a pandas DataFrame."""
    # Create a simple pandas DataFrame
    df = pd.DataFrame(
        {
            "id": [1, 2, 3],
            "name": ["Alice", "Bob", "Charlie"],
            "age": [25, 30, 35],
        },
    )

    # Call QueryChat with the pandas DataFrame - it should not raise errors
    # The function should accept a pandas DataFrame even with the narwhals import change
    qc = QueryChat(
        data_source=df,
        table_name="test_table",
        greeting="hello!",
    )

    # Verify the result is properly configured
    assert qc is not None


def test_init_with_narwhals_dataframe():
    """Test that QueryChat() can accept a narwhals DataFrame."""
    # Create a pandas DataFrame and convert to narwhals
    pdf = pd.DataFrame(
        {
            "id": [1, 2, 3],
            "name": ["Alice", "Bob", "Charlie"],
            "age": [25, 30, 35],
        },
    )
    nw_df = nw.from_native(pdf)

    # Call QueryChat with the narwhals DataFrame - it should not raise errors
    qc = QueryChat(
        data_source=nw_df,
        table_name="test_table",
        greeting="hello!",
    )

    # Verify the result is correctly configured
    assert qc is not None


def test_init_with_narwhals_lazyframe_raises():
    """Test that QueryChat() raises TypeError for LazyFrames."""
    pdf = pd.DataFrame(
        {
            "id": [1, 2, 3],
            "name": ["Alice", "Bob", "Charlie"],
            "age": [25, 30, 35],
        },
    )
    nw_lazy = nw.from_native(pdf).lazy()

    with pytest.raises(NotImplementedError, match="LazyFrame"):
        QueryChat(
            data_source=nw_lazy,
            table_name="test_table",
            greeting="hello!",
        )
