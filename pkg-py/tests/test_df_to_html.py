import sqlite3
import tempfile
from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy import create_engine
from src.querychat.datasource import DataFrameSource, SQLAlchemySource
from src.querychat.querychat import df_to_html


@pytest.fixture
def sample_dataframe():
    """Create a sample pandas DataFrame for testing."""
    return pd.DataFrame(
        {
            "id": [1, 2, 3, 4, 5],
            "name": ["Alice", "Bob", "Charlie", "Diana", "Eve"],
            "age": [25, 30, 35, 28, 32],
            "salary": [50000, 60000, 70000, 55000, 65000],
        },
    )


@pytest.fixture
def sample_sqlite():
    """Create a temporary SQLite database with test data."""
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")  # noqa: SIM115
    temp_db.close()

    conn = sqlite3.connect(temp_db.name)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE employees (
            id INTEGER PRIMARY KEY,
            name TEXT,
            age INTEGER,
            salary REAL
        )
    """)

    test_data = [
        (1, "Alice", 25, 50000),
        (2, "Bob", 30, 60000),
        (3, "Charlie", 35, 70000),
        (4, "Diana", 28, 55000),
        (5, "Eve", 32, 65000),
    ]

    cursor.executemany(
        "INSERT INTO employees (id, name, age, salary) VALUES (?, ?, ?, ?)",
        test_data,
    )

    conn.commit()
    conn.close()

    engine = create_engine(f"sqlite:///{temp_db.name}")
    yield engine

    # Cleanup
    Path(temp_db.name).unlink()


def test_df_to_html_with_dataframe_source_result(sample_dataframe):
    """Test that df_to_html() works with results from DataFrameSource.execute_query()."""
    source = DataFrameSource(sample_dataframe, "employees")

    # Execute query to get pandas DataFrame
    result_df = source.execute_query("SELECT * FROM employees WHERE age > 25")

    # This should succeed after the fix
    html_output = df_to_html(result_df)

    # Verify the HTML contains expected content
    assert isinstance(html_output, str)
    assert "<table" in html_output
    assert "Bob" in html_output
    assert "Charlie" in html_output
    assert "Diana" in html_output
    assert "Eve" in html_output


def test_df_to_html_with_sqlalchemy_source_result(sample_sqlite):
    """Test that df_to_html() works with results from SQLAlchemySource.execute_query()."""
    source = SQLAlchemySource(sample_sqlite, "employees")

    # Execute query to get pandas DataFrame
    result_df = source.execute_query("SELECT * FROM employees WHERE age > 25")

    # This should succeed after the fix
    html_output = df_to_html(result_df)

    # Verify the HTML contains expected content
    assert isinstance(html_output, str)
    assert "<table" in html_output
    assert "Bob" in html_output
    assert "Charlie" in html_output
    assert "Diana" in html_output
    assert "Eve" in html_output


def test_df_to_html_with_truncation(sample_dataframe):
    """Test that df_to_html() properly truncates large datasets."""
    source = DataFrameSource(sample_dataframe, "employees")

    # Execute query to get all rows
    result_df = source.execute_query("SELECT * FROM employees")

    # Test with maxrows=3 to trigger truncation
    html_output = df_to_html(result_df, maxrows=3)

    # Should show truncation message
    assert "Showing only the first 3 rows out of 5" in html_output
    assert "<table" in html_output
