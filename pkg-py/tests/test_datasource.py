import sqlite3
import tempfile
from pathlib import Path

import narwhals.stable.v1 as nw
import pandas as pd
import pytest
from querychat._datasource import DataFrameSource, SQLAlchemySource
from querychat._utils import UnsafeQueryError, check_query
from querychat.types import MissingColumnsError
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


def test_test_query_validates_all_columns(test_db_engine):
    """Test that test_query validates all columns when require_all_columns=True."""
    source = SQLAlchemySource(test_db_engine, "test_table")

    # Should succeed with all columns
    result = source.test_query("SELECT * FROM test_table", require_all_columns=True)
    assert len(result) <= 1
    expected_cols = {
        "id",
        "name",
        "age",
        "salary",
        "is_active",
        "join_date",
        "category",
        "score",
        "description",
    }
    assert set(result.columns) == expected_cols

    # Should succeed with all columns in different order
    result = source.test_query(
        "SELECT description, id, name, age, salary, is_active, join_date, category, score FROM test_table",
        require_all_columns=True,
    )
    assert len(result) <= 1
    assert set(result.columns) == expected_cols


def test_test_query_allows_additional_columns(test_db_engine):
    """Test that test_query allows additional computed columns."""
    source = SQLAlchemySource(test_db_engine, "test_table")

    # Should succeed with all columns plus computed columns
    result = source.test_query(
        "SELECT *, age * 2 as double_age FROM test_table", require_all_columns=True
    )
    assert len(result) <= 1
    assert "double_age" in result.columns
    expected_cols = {
        "id",
        "name",
        "age",
        "salary",
        "is_active",
        "join_date",
        "category",
        "score",
        "description",
        "double_age",
    }
    assert set(result.columns) == expected_cols


def test_test_query_fails_on_missing_columns(test_db_engine):
    """Test that test_query fails when columns are missing."""
    source = SQLAlchemySource(test_db_engine, "test_table")

    # Should fail when missing columns
    with pytest.raises(
        MissingColumnsError, match="Query result missing required columns"
    ):
        source.test_query(
            "SELECT id, name, age FROM test_table", require_all_columns=True
        )

    # Check that error message lists missing columns
    with pytest.raises(MissingColumnsError, match="'salary'"):
        source.test_query(
            "SELECT id, name, age FROM test_table", require_all_columns=True
        )


def test_test_query_without_validation(test_db_engine):
    """Test that test_query works without validation by default."""
    source = SQLAlchemySource(test_db_engine, "test_table")

    # Should succeed with subset of columns when not validating (default)
    result = source.test_query("SELECT id, name FROM test_table")
    assert len(result) <= 1
    assert list(result.columns) == ["id", "name"]

    # Should succeed with explicit require_all_columns=False
    result = source.test_query(
        "SELECT id, name FROM test_table", require_all_columns=False
    )
    assert len(result) <= 1
    assert list(result.columns) == ["id", "name"]


def test_test_query_empty_result(test_db_engine):
    """Test that test_query handles empty results correctly."""
    source = SQLAlchemySource(test_db_engine, "test_table")

    # Query with no matches
    result = source.test_query(
        "SELECT * FROM test_table WHERE id = 999", require_all_columns=True
    )
    assert len(result) == 0
    # Should still have column structure for validation
    expected_cols = {
        "id",
        "name",
        "age",
        "salary",
        "is_active",
        "join_date",
        "category",
        "score",
        "description",
    }
    assert set(result.columns) == expected_cols


def test_test_query_dataframe_source():
    """Test that test_query works with DataFrameSource."""
    # Create test DataFrame
    test_df = nw.from_native(
        pd.DataFrame(
            {
                "id": [1, 2, 3, 4, 5],
                "name": ["a", "b", "c", "d", "e"],
                "value": [10, 20, 30, 40, 50],
            }
        )
    )

    source = DataFrameSource(test_df, "test_table")

    # Should succeed with all columns
    result = source.test_query("SELECT * FROM test_table", require_all_columns=True)
    assert len(result) <= 1
    assert set(result.columns) == {"id", "name", "value"}

    # Should succeed with additional computed columns
    result = source.test_query(
        "SELECT *, value * 2 as doubled FROM test_table", require_all_columns=True
    )
    assert len(result) <= 1
    assert "doubled" in result.columns
    assert set(result.columns) == {"id", "name", "value", "doubled"}

    # Should fail when missing columns
    with pytest.raises(
        MissingColumnsError, match="Query result missing required columns"
    ):
        source.test_query("SELECT id FROM test_table", require_all_columns=True)

    # Should succeed without validation (default)
    result = source.test_query("SELECT id FROM test_table")
    assert len(result) <= 1
    assert list(result.columns) == ["id"]

    source.cleanup()


def test_test_query_error_message_format(test_db_engine):
    """Test that error message provides helpful information."""
    source = SQLAlchemySource(test_db_engine, "test_table")

    # Test error message format
    with pytest.raises(MissingColumnsError) as exc_info:
        source.test_query("SELECT id, name FROM test_table", require_all_columns=True)

    error_message = str(exc_info.value)
    assert "Query result missing required columns" in error_message
    assert "The query must return all original table columns" in error_message
    assert "Original columns:" in error_message


# Tests for check_query() function


def test_check_query_allows_valid_select():
    """Test that check_query allows valid SELECT queries."""
    check_query("SELECT * FROM test_table")
    check_query("select * from test_table")
    check_query("  SELECT * FROM test_table  ")
    check_query("\nSELECT * FROM test_table\n")


def test_check_query_blocks_always_blocked_keywords():
    """Test that check_query blocks always-blocked keywords."""
    always_blocked = [
        "DELETE",
        "TRUNCATE",
        "CREATE",
        "DROP",
        "ALTER",
        "GRANT",
        "REVOKE",
        "EXEC",
        "EXECUTE",
        "CALL",
    ]

    for keyword in always_blocked:
        with pytest.raises(UnsafeQueryError, match="disallowed operation"):
            check_query(f"{keyword} something")


def test_check_query_blocks_update_keywords_by_default():
    """Test that check_query blocks update keywords by default."""
    update_keywords = ["INSERT", "UPDATE", "MERGE", "REPLACE", "UPSERT"]

    for keyword in update_keywords:
        with pytest.raises(UnsafeQueryError, match="update operation"):
            check_query(f"{keyword} something")


def test_check_query_normalizes_whitespace_and_case():
    """Test that check_query normalizes whitespace and case."""
    with pytest.raises(UnsafeQueryError, match="disallowed"):
        check_query("  delete   FROM table  ")
    with pytest.raises(UnsafeQueryError, match="disallowed"):
        check_query("\n\nDELETE\n\nFROM table")
    with pytest.raises(UnsafeQueryError, match="disallowed"):
        check_query("\tDELETE\tFROM\ttable")
    with pytest.raises(UnsafeQueryError, match="disallowed"):
        check_query("DeLeTe FROM table")


def test_check_query_escape_hatch_enables_update_keywords(monkeypatch):
    """Test that escape hatch enables update keywords."""
    monkeypatch.setenv("QUERYCHAT_ENABLE_UPDATE_QUERIES", "true")

    # These should not raise
    check_query("INSERT INTO table VALUES (1)")
    check_query("UPDATE table SET x = 1")
    check_query("MERGE INTO table USING")
    check_query("REPLACE INTO table VALUES (1)")
    check_query("UPSERT INTO table VALUES (1)")


def test_check_query_escape_hatch_does_not_enable_always_blocked(monkeypatch):
    """Test that escape hatch does NOT enable always-blocked keywords."""
    monkeypatch.setenv("QUERYCHAT_ENABLE_UPDATE_QUERIES", "true")

    with pytest.raises(UnsafeQueryError, match="disallowed"):
        check_query("DELETE FROM table")
    with pytest.raises(UnsafeQueryError, match="disallowed"):
        check_query("DROP TABLE table")
    with pytest.raises(UnsafeQueryError, match="disallowed"):
        check_query("TRUNCATE TABLE table")


def test_check_query_integrated_into_execute_query():
    """Test that check_query is integrated into execute_query()."""
    test_df = nw.from_native(
        pd.DataFrame(
            {
                "id": [1, 2, 3],
                "name": ["a", "b", "c"],
                "value": [10, 20, 30],
            }
        )
    )

    source = DataFrameSource(test_df, "test_table")

    with pytest.raises(UnsafeQueryError, match="disallowed operation"):
        source.execute_query("DELETE FROM test_table")

    with pytest.raises(UnsafeQueryError, match="update operation"):
        source.execute_query("INSERT INTO test_table VALUES (1, 'a', 1)")

    source.cleanup()


def test_check_query_does_not_block_keywords_in_column_names():
    """Test that keywords in column names or values are not blocked."""
    check_query("SELECT update_count FROM table")
    check_query("SELECT * FROM delete_logs")


def test_check_query_escape_hatch_accepts_various_values(monkeypatch):
    """Test that escape hatch accepts various truthy values."""
    for value in ["true", "TRUE", "1", "yes", "YES"]:
        monkeypatch.setenv("QUERYCHAT_ENABLE_UPDATE_QUERIES", value)
        check_query("INSERT INTO table VALUES (1)")  # Should not raise
