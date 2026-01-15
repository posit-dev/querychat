"""Tests for the DataFrameSource class with narwhals compatibility."""

import duckdb
import narwhals.stable.v1 as nw
import pandas as pd
import pytest
from querychat._datasource import DataFrameSource

# Check if polars and pyarrow are available (both needed for DuckDB + polars)
try:
    import polars as pl
    import pyarrow as pa  # noqa: F401

    HAS_POLARS_WITH_PYARROW = True
except ImportError:
    HAS_POLARS_WITH_PYARROW = False
    pl = None  # type: ignore[assignment]


@pytest.fixture
def pandas_df():
    """Create a sample pandas DataFrame."""
    return pd.DataFrame(
        {
            "id": [1, 2, 3, 4, 5],
            "name": ["Alice", "Bob", "Charlie", "Diana", "Eve"],
            "age": [25, 30, 35, 28, 32],
            "salary": [50000.0, 60000.0, 70000.0, 55000.0, 65000.0],
            "department": ["Engineering", "Sales", "Engineering", "Sales", "Engineering"],
        }
    )


@pytest.fixture
def narwhals_df(pandas_df):
    """Create a narwhals DataFrame from pandas."""
    return nw.from_native(pandas_df)


class TestDataFrameSourceInit:
    """Tests for DataFrameSource initialization."""

    def test_init_with_narwhals_dataframe(self, narwhals_df):
        """Test that DataFrameSource accepts a narwhals DataFrame."""
        source = DataFrameSource(narwhals_df, "test_table")
        assert source.table_name == "test_table"

    @pytest.mark.skipif(not HAS_POLARS_WITH_PYARROW, reason="polars or pyarrow not installed")
    def test_init_with_polars_dataframe(self):
        """Test that DataFrameSource accepts a narwhals-wrapped polars DataFrame."""
        polars_df = pl.DataFrame(
            {
                "id": [1, 2, 3],
                "name": ["Alice", "Bob", "Charlie"],
            }
        )
        source = DataFrameSource(nw.from_native(polars_df), "test_table")
        assert source.table_name == "test_table"


class TestDataFrameSourceExecuteQuery:
    """Tests for DataFrameSource.execute_query method."""

    def test_execute_query_returns_native_dataframe(self, narwhals_df):
        """Test that execute_query returns a native DataFrame (same as input)."""
        source = DataFrameSource(narwhals_df, "employees")
        result = source.execute_query("SELECT * FROM employees")
        # Since narwhals_df is created from pandas, result should be pandas
        assert isinstance(result, pd.DataFrame)

    def test_execute_query_select_all(self, narwhals_df):
        """Test SELECT * query."""
        source = DataFrameSource(narwhals_df, "employees")
        result = source.execute_query("SELECT * FROM employees")

        assert result.shape == (5, 5)
        assert set(result.columns) == {"id", "name", "age", "salary", "department"}

    def test_execute_query_with_filter(self, narwhals_df):
        """Test query with WHERE clause."""
        source = DataFrameSource(narwhals_df, "employees")
        result = source.execute_query(
            "SELECT * FROM employees WHERE department = 'Engineering'"
        )

        assert result.shape == (3, 5)
        departments = result["department"].unique().tolist()
        assert departments == ["Engineering"]

    def test_execute_query_with_aggregation(self, narwhals_df):
        """Test query with aggregation."""
        source = DataFrameSource(narwhals_df, "employees")
        result = source.execute_query(
            "SELECT department, AVG(salary) as avg_salary FROM employees GROUP BY department"
        )

        assert result.shape == (2, 2)
        assert "department" in result.columns
        assert "avg_salary" in result.columns

    def test_execute_query_select_columns(self, narwhals_df):
        """Test selecting specific columns."""
        source = DataFrameSource(narwhals_df, "employees")
        result = source.execute_query("SELECT name, age FROM employees")

        assert result.shape == (5, 2)
        assert list(result.columns) == ["name", "age"]

    def test_execute_query_order_by(self, narwhals_df):
        """Test query with ORDER BY clause."""
        source = DataFrameSource(narwhals_df, "employees")
        result = source.execute_query(
            "SELECT name, age FROM employees ORDER BY age DESC"
        )

        ages = result["age"].tolist()
        assert ages == sorted(ages, reverse=True)

    def test_execute_query_empty_result(self, narwhals_df):
        """Test query that returns no rows."""
        source = DataFrameSource(narwhals_df, "employees")
        result = source.execute_query(
            "SELECT * FROM employees WHERE age > 100"
        )

        # Result is native pandas DataFrame (same as input backend)
        assert isinstance(result, pd.DataFrame)
        assert result.shape == (0, 5)


class TestDataFrameSourceGetData:
    """Tests for DataFrameSource.get_data method."""

    def test_get_data_returns_native_dataframe(self, narwhals_df):
        """Test that get_data returns a native DataFrame (same as input)."""
        source = DataFrameSource(narwhals_df, "employees")
        result = source.get_data()
        # Since narwhals_df is created from pandas, result should be pandas
        assert isinstance(result, pd.DataFrame)

    def test_get_data_returns_full_dataset(self, narwhals_df):
        """Test that get_data returns all rows."""
        source = DataFrameSource(narwhals_df, "employees")
        result = source.get_data()

        assert result.shape == narwhals_df.shape
        assert set(result.columns) == set(narwhals_df.columns)

    def test_get_data_preserves_data(self, narwhals_df):
        """Test that get_data preserves data values."""
        source = DataFrameSource(narwhals_df, "employees")
        result = source.get_data()

        # Check that the data matches
        original_names = sorted(narwhals_df["name"].to_list())
        result_names = sorted(result["name"].tolist())
        assert original_names == result_names


class TestDataFrameSourceGetSchema:
    """Tests for DataFrameSource.get_schema method."""

    def test_get_schema_includes_table_name(self, narwhals_df):
        """Test that schema includes table name."""
        source = DataFrameSource(narwhals_df, "employees")
        schema = source.get_schema(categorical_threshold=10)

        assert "Table: employees" in schema
        assert "Columns:" in schema

    def test_get_schema_includes_all_columns(self, narwhals_df):
        """Test that schema includes all columns."""
        source = DataFrameSource(narwhals_df, "employees")
        schema = source.get_schema(categorical_threshold=10)

        for col in narwhals_df.columns:
            assert f"- {col} (" in schema

    def test_get_schema_numeric_ranges(self, narwhals_df):
        """Test that numeric columns include range information."""
        source = DataFrameSource(narwhals_df, "employees")
        schema = source.get_schema(categorical_threshold=10)

        # Age should have range
        assert "Range: 25 to 35" in schema
        # Salary should have range
        assert "Range: 50000.0 to 70000.0" in schema

    def test_get_schema_categorical_values(self, narwhals_df):
        """Test that categorical columns show unique values."""
        source = DataFrameSource(narwhals_df, "employees")
        schema = source.get_schema(categorical_threshold=10)

        # Department has only 2 unique values, should be categorical
        assert "Categorical values:" in schema
        assert "'Engineering'" in schema
        assert "'Sales'" in schema

    def test_get_schema_respects_threshold(self, narwhals_df):
        """Test that categorical_threshold is respected."""
        source = DataFrameSource(narwhals_df, "employees")

        # With threshold 1, no columns should be categorical
        schema_low = source.get_schema(categorical_threshold=1)
        # Department has 2 unique values, should not be listed as categorical
        lines = schema_low.split("\n")
        dept_idx = next(i for i, line in enumerate(lines) if "- department" in line)
        if dept_idx + 1 < len(lines):
            assert "Categorical values:" not in lines[dept_idx + 1]

        # With threshold 5, department should be categorical
        schema_high = source.get_schema(categorical_threshold=5)
        assert "'Engineering'" in schema_high


class TestDataFrameSourceDbType:
    """Tests for DataFrameSource.get_db_type method."""

    def test_get_db_type_returns_duckdb(self, narwhals_df):
        """Test that get_db_type returns 'DuckDB'."""
        source = DataFrameSource(narwhals_df, "employees")
        assert source.get_db_type() == "DuckDB"


class TestDataFrameSourceCleanup:
    """Tests for DataFrameSource.cleanup method."""

    def test_cleanup_closes_connection(self, narwhals_df):
        """Test that cleanup closes the DuckDB connection."""
        source = DataFrameSource(narwhals_df, "employees")

        # Should work before cleanup
        result = source.execute_query("SELECT * FROM employees LIMIT 1")
        assert result.shape[0] == 1

        # Cleanup
        source.cleanup()

        # After cleanup, queries should fail
        with pytest.raises(duckdb.ConnectionException):
            source.execute_query("SELECT * FROM employees")


@pytest.mark.skipif(not HAS_POLARS_WITH_PYARROW, reason="polars or pyarrow not installed")
class TestDataFrameSourceWithPolars:
    """Tests for DataFrameSource with polars DataFrames."""

    @pytest.fixture
    def polars_df(self):
        """Create a sample narwhals-wrapped polars DataFrame."""
        return nw.from_native(
            pl.DataFrame(
                {
                    "id": [1, 2, 3],
                    "name": ["Alice", "Bob", "Charlie"],
                    "value": [10.5, 20.5, 30.5],
                }
            )
        )

    def test_execute_query_with_polars(self, polars_df):
        """Test execute_query with polars source returns native polars DataFrame."""
        source = DataFrameSource(polars_df, "test_data")
        result = source.execute_query("SELECT * FROM test_data")

        assert isinstance(result, pl.DataFrame)
        assert result.shape == (3, 3)

    def test_get_data_with_polars(self, polars_df):
        """Test get_data with polars source returns native polars DataFrame."""
        source = DataFrameSource(polars_df, "test_data")
        result = source.get_data()

        assert isinstance(result, pl.DataFrame)
        assert result.shape == polars_df.shape

    def test_polars_result_backend(self, polars_df):
        """Test that results are native polars DataFrames when input is polars."""
        source = DataFrameSource(polars_df, "test_data")
        result = source.execute_query("SELECT * FROM test_data")

        # Results should be native polars DataFrames
        assert isinstance(result, pl.DataFrame)
