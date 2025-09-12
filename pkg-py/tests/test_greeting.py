import os

import pandas as pd
import pytest

from querychat import greeting, init


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
def querychat_config():
    """Create a test querychat configuration."""
    # Create a simple pandas DataFrame
    df = pd.DataFrame(
        {
            "id": [1, 2, 3],
            "name": ["Alice", "Bob", "Charlie"],
            "age": [25, 30, 35],
        },
    )

    # Create a config with a greeting
    return init(
        data_source=df,
        table_name="test_table",
        greeting="Hello! This is a test greeting.",
    )


@pytest.fixture
def querychat_config_no_greeting():
    """Create a test querychat configuration without a greeting."""
    # Create a simple pandas DataFrame
    df = pd.DataFrame(
        {
            "id": [1, 2, 3],
            "name": ["Alice", "Bob", "Charlie"],
            "age": [25, 30, 35],
        },
    )

    # Create a config without a greeting
    return init(
        data_source=df,
        table_name="test_table",
        greeting=None,
    )


def test_greeting_retrieval(querychat_config):
    """
    Test that greeting() returns the existing greeting when generate=False.
    """
    result = greeting(querychat_config, generate=False)
    assert result == "Hello! This is a test greeting."


def test_greeting_retrieval_none(querychat_config_no_greeting):
    """
    Test that greeting() returns None when there's no existing greeting and
    generate=False.
    """
    result = greeting(querychat_config_no_greeting, generate=False)
    assert result is None


def test_greeting_retrieval_empty(querychat_config):
    """
    Test that greeting() returns None when the existing greeting is empty and
    generate=False.
    """
    querychat_config.greeting = ""

    result = greeting(querychat_config, generate=False)
    assert result is None


def test_greeting_invalid_config():
    """Test that greeting() raises TypeError when given an invalid config."""
    with pytest.raises(TypeError):
        greeting("not a config")
