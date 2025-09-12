import sqlite3
import tempfile
from pathlib import Path

import pytest
from querychat.datasource import SQLAlchemySource
from sqlalchemy import create_engine, text


@pytest.fixture
def test_db_engine():
    """Create a temporary SQLite database with test data."""
    # Create temporary database file
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")  # noqa: SIM115
    temp_db.close()

    # Connect and create test table with various data types
    conn = sqlite3.connect(temp_db.name)
    cursor = conn.cursor()

    # Create table with different column types
    cursor.execute("""
        CREATE TABLE test_table (
            id INTEGER PRIMARY KEY,
            name TEXT,
            age INTEGER,
            salary REAL,
            is_active BOOLEAN,
            join_date DATE,
            category TEXT,
            score NUMERIC,
            description TEXT
        )
    """)

    # Insert test data
    test_data = [
        (1, "Alice", 30, 75000.50, True, "2023-01-15", "A", 95.5, "Senior developer"),
        (2, "Bob", 25, 60000.00, True, "2023-03-20", "B", 87.2, "Junior developer"),
        (3, "Charlie", 35, 85000.75, False, "2022-12-01", "A", 92.1, "Team lead"),
        (
            4,
            "Diana",
            28,
            70000.25,
            True,
            "2023-05-10",
            "C",
            89.8,
            "Mid-level developer",
        ),
        (5, "Eve", 32, 80000.00, True, "2023-02-28", "A", 91.3, "Senior developer"),
        (6, "Frank", 26, 62000.50, False, "2023-04-15", "B", 85.7, "Junior developer"),
        (7, "Grace", 29, 72000.75, True, "2023-01-30", "A", 93.4, "Developer"),
        (8, "Henry", 31, 78000.25, True, "2023-03-05", "C", 88.9, "Senior developer"),
    ]

    cursor.executemany(
        """
        INSERT INTO test_table
        (id, name, age, salary, is_active, join_date, category, score, description)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        test_data,
    )

    conn.commit()
    conn.close()

    # Create SQLAlchemy engine
    engine = create_engine(f"sqlite:///{temp_db.name}")

    yield engine

    # Cleanup
    Path(temp_db.name).unlink()


def test_get_schema_numeric_ranges(test_db_engine):
    """Test that numeric columns include min/max ranges."""
    source = SQLAlchemySource(test_db_engine, "test_table")
    schema = source.get_schema(categorical_threshold=5)

    # Check that numeric columns have range information
    assert "- id (INTEGER)" in schema
    assert "Range: 1 to 8" in schema

    assert "- age (INTEGER)" in schema
    assert "Range: 25 to 35" in schema

    assert "- salary (FLOAT)" in schema
    assert "Range: 60000.0 to 85000.75" in schema

    assert "- score (NUMERIC)" in schema
    assert "Range: 85.7 to 95.5" in schema


def test_get_schema_categorical_values(test_db_engine):
    """Test that text columns with few unique values show categorical values."""
    source = SQLAlchemySource(test_db_engine, "test_table")
    schema = source.get_schema(categorical_threshold=5)

    # Category column should be treated as categorical (3 unique values: A, B, C)
    assert "- category (TEXT)" in schema
    assert "Categorical values:" in schema
    assert "'A'" in schema and "'B'" in schema and "'C'" in schema  # noqa: PT018


def test_get_schema_non_categorical_text(test_db_engine):
    """Test that text columns with many unique values don't show categorical values."""
    source = SQLAlchemySource(test_db_engine, "test_table")
    schema = source.get_schema(categorical_threshold=3)

    # Name and description columns should not be categorical (8 and 6 unique values respectively)
    lines = schema.split("\n")
    name_line_idx = next(i for i, line in enumerate(lines) if "- name (TEXT)" in line)
    description_line_idx = next(
        i for i, line in enumerate(lines) if "- description (TEXT)" in line
    )

    # Check that the next line after name column doesn't contain categorical values
    if name_line_idx + 1 < len(lines):
        assert "Categorical values:" not in lines[name_line_idx + 1]

    # Check that the next line after description column doesn't contain categorical values
    if description_line_idx + 1 < len(lines):
        assert "Categorical values:" not in lines[description_line_idx + 1]


def test_get_schema_different_thresholds(test_db_engine):
    """Test that categorical_threshold parameter works correctly."""
    source = SQLAlchemySource(test_db_engine, "test_table")

    # With threshold 2, only category column (3 unique) should not be categorical
    schema_low = source.get_schema(categorical_threshold=2)
    assert "- category (TEXT)" in schema_low
    assert "'A'" not in schema_low  # Should not show categorical values

    # With threshold 5, category column should be categorical
    schema_high = source.get_schema(categorical_threshold=5)
    assert "- category (TEXT)" in schema_high
    assert "'A'" in schema_high  # Should show categorical values


def test_get_schema_table_structure(test_db_engine):
    """Test the overall structure of the schema output."""
    source = SQLAlchemySource(test_db_engine, "test_table")
    schema = source.get_schema(categorical_threshold=5)

    lines = schema.split("\n")

    # Check header
    assert lines[0] == "Table: test_table"
    assert lines[1] == "Columns:"

    # Check that all columns are present
    expected_columns = [
        "id",
        "name",
        "age",
        "salary",
        "is_active",
        "join_date",
        "category",
        "score",
        "description",
    ]
    for col in expected_columns:
        assert any(f"- {col} (" in line for line in lines), (
            f"Column {col} not found in schema"
        )


def test_get_schema_empty_result_handling(test_db_engine):
    """Test handling when statistics queries return empty results."""
    # Create empty table
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE empty_table (id INTEGER, name TEXT)")
    conn.commit()

    engine = create_engine("sqlite:///:memory:")
    # Recreate table in the new engine
    with engine.connect() as connection:
        connection.execute(text("CREATE TABLE empty_table (id INTEGER, name TEXT)"))
        connection.commit()

    source = SQLAlchemySource(engine, "empty_table")
    schema = source.get_schema(categorical_threshold=5)

    # Should still work but without range/categorical info
    assert "Table: empty_table" in schema
    assert "- id (INTEGER)" in schema
    assert "- name (TEXT)" in schema
    # Should not have range or categorical information
    assert "Range:" not in schema
    assert "Categorical values:" not in schema


def test_get_schema_boolean_and_date_types(test_db_engine):
    """Test handling of boolean and date column types."""
    source = SQLAlchemySource(test_db_engine, "test_table")
    schema = source.get_schema(categorical_threshold=5)

    # Boolean column should show range
    assert "- is_active (BOOLEAN)" in schema
    # SQLite stores booleans as integers, so should show 0 to 1 range

    # Date column should show range
    assert "- join_date (DATE)" in schema
    assert "Range:" in schema


def test_invalid_table_name():
    """Test that invalid table name raises appropriate error."""
    engine = create_engine("sqlite:///:memory:")

    with pytest.raises(ValueError, match="Table 'nonexistent' not found in database"):
        SQLAlchemySource(engine, "nonexistent")
