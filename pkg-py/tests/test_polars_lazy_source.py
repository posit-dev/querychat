"""Tests for the PolarsLazySource class."""

import narwhals.stable.v1 as nw
import polars as pl
import pytest


@pytest.fixture
def polars_lazy_df():
    """Create a sample Polars LazyFrame."""
    return pl.LazyFrame(
        {
            "id": [1, 2, 3, 4, 5],
            "name": ["Alice", "Bob", "Charlie", "Diana", "Eve"],
            "age": [25, 30, 35, 28, 32],
            "salary": [50000.0, 60000.0, 70000.0, 55000.0, 65000.0],
            "department": ["Engineering", "Sales", "Engineering", "Sales", "Engineering"],
        }
    )


class TestPolarsLazySourceInit:
    """Tests for PolarsLazySource initialization."""

    def test_init_accepts_narwhals_lazyframe(self, polars_lazy_df):
        """Test that PolarsLazySource accepts a narwhals LazyFrame."""
        from querychat._datasource import PolarsLazySource

        nw_lf = nw.from_native(polars_lazy_df)
        source = PolarsLazySource(nw_lf, "test_table")
        assert source.table_name == "test_table"

    def test_get_db_type_returns_polars(self, polars_lazy_df):
        """Test that get_db_type returns 'Polars'."""
        from querychat._datasource import PolarsLazySource

        nw_lf = nw.from_native(polars_lazy_df)
        source = PolarsLazySource(nw_lf, "employees")
        assert source.get_db_type() == "Polars"


class TestPolarsLazySourceExecuteQuery:
    """Tests for PolarsLazySource.execute_query method."""

    def test_execute_query_returns_native_lazyframe(self, polars_lazy_df):
        """Test that execute_query returns a native polars LazyFrame."""
        from querychat._datasource import PolarsLazySource

        nw_lf = nw.from_native(polars_lazy_df)
        source = PolarsLazySource(nw_lf, "employees")
        result = source.execute_query("SELECT * FROM employees")
        assert isinstance(result, pl.LazyFrame)

    def test_execute_query_select_all(self, polars_lazy_df):
        """Test SELECT * query."""
        from querychat._datasource import PolarsLazySource

        nw_lf = nw.from_native(polars_lazy_df)
        source = PolarsLazySource(nw_lf, "employees")
        result = source.execute_query("SELECT * FROM employees")

        # Collect to verify results
        collected = result.collect()
        assert collected.shape == (5, 5)
        assert set(collected.columns) == {"id", "name", "age", "salary", "department"}

    def test_execute_query_with_filter(self, polars_lazy_df):
        """Test query with WHERE clause."""
        from querychat._datasource import PolarsLazySource

        nw_lf = nw.from_native(polars_lazy_df)
        source = PolarsLazySource(nw_lf, "employees")
        result = source.execute_query(
            "SELECT * FROM employees WHERE department = 'Engineering'"
        )

        collected = result.collect()
        assert collected.shape == (3, 5)

    def test_execute_query_with_aggregation(self, polars_lazy_df):
        """Test query with aggregation."""
        from querychat._datasource import PolarsLazySource

        nw_lf = nw.from_native(polars_lazy_df)
        source = PolarsLazySource(nw_lf, "employees")
        result = source.execute_query(
            "SELECT department, AVG(salary) as avg_salary FROM employees GROUP BY department"
        )

        collected = result.collect()
        assert collected.shape == (2, 2)
        assert "department" in collected.columns
        assert "avg_salary" in collected.columns


class TestPolarsLazySourceGetData:
    """Tests for PolarsLazySource.get_data method."""

    def test_get_data_returns_native_lazyframe(self, polars_lazy_df):
        """Test that get_data returns a native polars LazyFrame."""
        from querychat._datasource import PolarsLazySource

        nw_lf = nw.from_native(polars_lazy_df)
        source = PolarsLazySource(nw_lf, "employees")
        result = source.get_data()
        assert isinstance(result, pl.LazyFrame)

    def test_get_data_returns_original_lazyframe(self, polars_lazy_df):
        """Test that get_data returns the original LazyFrame."""
        from querychat._datasource import PolarsLazySource

        nw_lf = nw.from_native(polars_lazy_df)
        source = PolarsLazySource(nw_lf, "employees")
        result = source.get_data()

        # Should return the original native Polars LazyFrame
        assert result is polars_lazy_df


class TestPolarsLazySourceGetSchema:
    """Tests for PolarsLazySource.get_schema method."""

    def test_get_schema_includes_table_name(self, polars_lazy_df):
        """Test that schema includes table name."""
        from querychat._datasource import PolarsLazySource

        nw_lf = nw.from_native(polars_lazy_df)
        source = PolarsLazySource(nw_lf, "employees")
        schema = source.get_schema(categorical_threshold=10)

        assert "Table: employees" in schema
        assert "Columns:" in schema

    def test_get_schema_includes_all_columns(self, polars_lazy_df):
        """Test that schema includes all columns."""
        from querychat._datasource import PolarsLazySource

        nw_lf = nw.from_native(polars_lazy_df)
        source = PolarsLazySource(nw_lf, "employees")
        schema = source.get_schema(categorical_threshold=10)

        for col in ["id", "name", "age", "salary", "department"]:
            assert f"- {col} (" in schema

    def test_get_schema_numeric_ranges(self, polars_lazy_df):
        """Test that numeric columns include range information."""
        from querychat._datasource import PolarsLazySource

        nw_lf = nw.from_native(polars_lazy_df)
        source = PolarsLazySource(nw_lf, "employees")
        schema = source.get_schema(categorical_threshold=10)

        # Age should have range
        assert "Range: 25 to 35" in schema
        # Salary should have range
        assert "Range: 50000.0 to 70000.0" in schema

    def test_get_schema_categorical_values(self, polars_lazy_df):
        """Test that categorical columns show unique values."""
        from querychat._datasource import PolarsLazySource

        nw_lf = nw.from_native(polars_lazy_df)
        source = PolarsLazySource(nw_lf, "employees")
        schema = source.get_schema(categorical_threshold=10)

        # Department has only 2 unique values, should be categorical
        assert "Categorical values:" in schema
        assert "'Engineering'" in schema
        assert "'Sales'" in schema


class TestPolarsLazySourceTestQuery:
    """Tests for PolarsLazySource.test_query method."""

    def test_test_query_returns_dataframe(self, polars_lazy_df):
        """Test that test_query returns a collected DataFrame (not LazyFrame)."""
        from querychat._datasource import PolarsLazySource

        nw_lf = nw.from_native(polars_lazy_df)
        source = PolarsLazySource(nw_lf, "employees")
        result = source.test_query("SELECT * FROM employees")
        # test_query collects to catch runtime errors, so returns DataFrame
        assert isinstance(result, nw.DataFrame)
        assert len(result) <= 1

    def test_test_query_require_all_columns_passes(self, polars_lazy_df):
        """Test that test_query passes when all columns present."""
        from querychat._datasource import PolarsLazySource

        nw_lf = nw.from_native(polars_lazy_df)
        source = PolarsLazySource(nw_lf, "employees")
        # Should not raise
        result = source.test_query(
            "SELECT * FROM employees", require_all_columns=True
        )
        assert isinstance(result, nw.DataFrame)

    def test_test_query_require_all_columns_fails(self, polars_lazy_df):
        """Test that test_query raises when columns missing."""
        from querychat._datasource import (
            MissingColumnsError,
            PolarsLazySource,
        )

        nw_lf = nw.from_native(polars_lazy_df)
        source = PolarsLazySource(nw_lf, "employees")

        with pytest.raises(MissingColumnsError):
            source.test_query(
                "SELECT name, age FROM employees", require_all_columns=True
            )

    def test_test_query_catches_runtime_errors(self):
        """Test that test_query catches runtime errors by actually executing."""
        from querychat._datasource import PolarsLazySource

        # Create LazyFrame with string column that can't be cast to integer
        lf = pl.LazyFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
        nw_lf = nw.from_native(lf)
        source = PolarsLazySource(nw_lf, "test_table")

        # This query fails at runtime when trying to cast strings to integers
        # test_query should catch this because it actually executes (collects) the query
        with pytest.raises(pl.exceptions.InvalidOperationError):
            source.test_query("SELECT CAST(b AS INTEGER) FROM test_table")
