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


def test_querychat_init(sample_df):
    """Test that QueryChat (Express mode) initializes correctly."""
    qc = QueryChat(
        data_source=sample_df,
        table_name="test_table",
        greeting="Hello!",
    )

    # Verify basic attributes are set
    assert qc is not None
    assert hasattr(qc, "data_source")
    assert hasattr(qc, "system_prompt")
    assert hasattr(qc, "greeting")
    assert hasattr(qc, "client")
    assert qc.id == "test_table"

    # Even without server initialization, we should be able to query the data source
    result = qc.data_source.execute_query(
        "SELECT * FROM test_table WHERE id = 2",
    )

    assert len(result) == 1
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


def test_querychat_set_methods(sample_df):
    """Test that setter methods work."""
    qc = QueryChat(
        data_source=sample_df,
        table_name="test_table",
        greeting="Hello!",
    )

    # Test set_system_prompt
    qc.set_system_prompt(
        qc.data_source,
        data_description="A test dataset",
    )
    assert "test dataset" in qc.system_prompt.lower()

    # Test set_data_source
    new_df = pd.DataFrame({"x": [1, 2, 3]})
    qc.set_data_source(new_df, "new_table")
    assert qc.data_source is not None

    # Test set_client
    qc.set_client("openai/gpt-4o-mini")
    assert qc.client is not None


def test_querychat_core_reactive_access_before_server_raises(sample_df):
    """Test that accessing reactive properties before .server() raises error."""
    qc = QueryChat(
        data_source=sample_df,
        table_name="test_table",
        greeting="Hello!",
    )

    # Accessing reactive properties before .server() should raise
    with pytest.raises(RuntimeError, match="Must call \\.server\\(\\)"):
        qc.title()

    with pytest.raises(RuntimeError, match="Must call \\.server\\(\\)"):
        qc.sql()

    with pytest.raises(RuntimeError, match="Must call \\.server\\(\\)"):
        qc.df()
