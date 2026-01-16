"""Tests for the IbisSource class."""

import pytest

ibis = pytest.importorskip("ibis")


@pytest.fixture
def ibis_table():
    """Create a sample Ibis Table backed by DuckDB."""
    conn = ibis.duckdb.connect()
    conn.create_table(
        "employees",
        {
            "id": [1, 2, 3, 4, 5],
            "name": ["Alice", "Bob", "Charlie", "Diana", "Eve"],
            "age": [25, 30, 35, 28, 32],
            "salary": [50000.0, 60000.0, 70000.0, 55000.0, 65000.0],
            "department": [
                "Engineering",
                "Sales",
                "Engineering",
                "Sales",
                "Engineering",
            ],
        },
    )
    yield conn.table("employees")
    conn.disconnect()


class TestIbisSourceInit:
    """Tests for IbisSource initialization."""

    def test_init_accepts_ibis_table(self, ibis_table):
        """Test that IbisSource accepts an ibis.Table."""
        from querychat._datasource import IbisSource

        source = IbisSource(ibis_table, "employees")
        assert source.table_name == "employees"

    def test_get_db_type_returns_backend_name(self, ibis_table):
        """Test that get_db_type returns 'duckdb'."""
        from querychat._datasource import IbisSource

        source = IbisSource(ibis_table, "employees")
        assert source.get_db_type() == "duckdb"


class TestIbisSourceExecuteQuery:
    """Tests for IbisSource.execute_query method."""

    def test_execute_query_returns_ibis_table(self, ibis_table):
        """Test that execute_query returns an ibis.Table."""
        from querychat._datasource import IbisSource

        source = IbisSource(ibis_table, "employees")
        result = source.execute_query("SELECT * FROM employees")
        assert isinstance(result, ibis.Table)

    def test_execute_query_select_all(self, ibis_table):
        """Test SELECT * query."""
        from querychat._datasource import IbisSource

        source = IbisSource(ibis_table, "employees")
        result = source.execute_query("SELECT * FROM employees")

        # Execute to verify results
        executed = result.execute()
        assert executed.shape == (5, 5)
        assert set(executed.columns) == {"id", "name", "age", "salary", "department"}

    def test_execute_query_with_filter(self, ibis_table):
        """Test query with WHERE clause."""
        from querychat._datasource import IbisSource

        source = IbisSource(ibis_table, "employees")
        result = source.execute_query(
            "SELECT * FROM employees WHERE department = 'Engineering'"
        )

        executed = result.execute()
        assert executed.shape == (3, 5)

    def test_execute_query_with_aggregation(self, ibis_table):
        """Test query with aggregation."""
        from querychat._datasource import IbisSource

        source = IbisSource(ibis_table, "employees")
        result = source.execute_query(
            "SELECT department, AVG(salary) as avg_salary FROM employees GROUP BY department"
        )

        executed = result.execute()
        assert executed.shape == (2, 2)
        assert "department" in executed.columns
        assert "avg_salary" in executed.columns


class TestIbisSourceGetData:
    """Tests for IbisSource.get_data method."""

    def test_get_data_returns_original_table(self, ibis_table):
        """Test that get_data returns the original Ibis Table."""
        from querychat._datasource import IbisSource

        source = IbisSource(ibis_table, "employees")
        result = source.get_data()

        # Should be the same object
        assert result is ibis_table


class TestIbisSourceGetSchema:
    """Tests for IbisSource.get_schema method."""

    def test_get_schema_includes_table_name(self, ibis_table):
        """Test that schema includes table name."""
        from querychat._datasource import IbisSource

        source = IbisSource(ibis_table, "employees")
        schema = source.get_schema(categorical_threshold=10)

        assert "Table: employees" in schema
        assert "Columns:" in schema

    def test_get_schema_includes_all_columns(self, ibis_table):
        """Test that schema includes all columns."""
        from querychat._datasource import IbisSource

        source = IbisSource(ibis_table, "employees")
        schema = source.get_schema(categorical_threshold=10)

        for col in ["id", "name", "age", "salary", "department"]:
            assert f"- {col} (" in schema

    def test_get_schema_numeric_ranges(self, ibis_table):
        """Test that numeric columns include range information."""
        from querychat._datasource import IbisSource

        source = IbisSource(ibis_table, "employees")
        schema = source.get_schema(categorical_threshold=10)

        # Age should have range (Ibis/DuckDB may return as float)
        assert "Range: 25" in schema
        assert "to 35" in schema
        # Salary should have range
        assert "Range: 50000.0 to 70000.0" in schema

    def test_get_schema_categorical_values(self, ibis_table):
        """Test that categorical columns show unique values."""
        from querychat._datasource import IbisSource

        source = IbisSource(ibis_table, "employees")
        schema = source.get_schema(categorical_threshold=10)

        # Department has only 2 unique values, should be categorical
        assert "Categorical values:" in schema
        assert "'Engineering'" in schema
        assert "'Sales'" in schema


class TestIbisSourceTestQuery:
    """Tests for IbisSource.test_query method."""

    def test_test_query_returns_ibis_table(self, ibis_table):
        """Test that test_query returns an ibis.Table (lazy)."""
        from querychat._datasource import IbisSource

        source = IbisSource(ibis_table, "employees")
        result = source.test_query("SELECT * FROM employees")
        # test_query returns ibis.Table to match the generic DataSource pattern
        assert isinstance(result, ibis.Table)

    def test_test_query_require_all_columns_passes(self, ibis_table):
        """Test that test_query passes when all columns present."""
        from querychat._datasource import IbisSource

        source = IbisSource(ibis_table, "employees")
        # Should not raise
        result = source.test_query("SELECT * FROM employees", require_all_columns=True)
        assert isinstance(result, ibis.Table)

    def test_test_query_require_all_columns_fails(self, ibis_table):
        """Test that test_query raises when columns missing."""
        from querychat._datasource import (
            IbisSource,
            MissingColumnsError,
        )

        source = IbisSource(ibis_table, "employees")

        with pytest.raises(MissingColumnsError):
            source.test_query(
                "SELECT name, age FROM employees", require_all_columns=True
            )

    def test_test_query_catches_runtime_errors(self):
        """Test that test_query catches runtime errors by actually executing."""
        import duckdb
        from querychat._datasource import IbisSource

        # Create table with string column that can't be cast to integer
        conn = ibis.duckdb.connect()
        try:
            conn.create_table("test_table", {"a": [1, 2, 3], "b": ["x", "y", "z"]})
            table = conn.table("test_table")
            source = IbisSource(table, "test_table")

            # This query fails at runtime when trying to cast strings to integers.
            # test_query should catch this because it actually executes the query.
            with pytest.raises(duckdb.ConversionException):
                source.test_query("SELECT CAST(b AS INTEGER) FROM test_table")
        finally:
            conn.disconnect()


class TestIbisSourceValidation:
    """Tests for IbisSource validation and error handling."""

    def test_rejects_non_sql_backend(self):
        """Test that non-SQL backends raise TypeError."""
        import polars as pl
        from querychat._datasource import IbisSource

        # ibis.polars is a non-SQL backend
        df = pl.DataFrame({"x": [1, 2, 3], "y": ["a", "b", "c"]})
        conn = ibis.polars.connect({"my_table": df})
        table = conn.table("my_table")

        with pytest.raises(TypeError, match="SQL backend"):
            IbisSource(table, "my_table")


class TestIbisSourceEdgeCases:
    """Tests for edge cases in IbisSource."""

    def test_empty_table_schema(self):
        """Test get_schema with empty table."""
        import polars as pl
        from querychat._datasource import IbisSource

        conn = ibis.duckdb.connect()
        try:
            # Use polars DataFrame to create empty table with correct types
            empty_df = pl.DataFrame(
                {
                    "id": pl.Series([], dtype=pl.Int64),
                    "name": pl.Series([], dtype=pl.String),
                    "value": pl.Series([], dtype=pl.Float64),
                }
            )
            conn.create_table("empty", empty_df)
            table = conn.table("empty")

            source = IbisSource(table, "empty")
            schema = source.get_schema(categorical_threshold=10)

            assert "Table: empty" in schema
            assert "id" in schema
            assert "name" in schema
            assert "value" in schema
        finally:
            conn.disconnect()

    def test_empty_table_execute_query(self):
        """Test execute_query returns empty result for empty table."""
        import polars as pl
        from querychat._datasource import IbisSource

        conn = ibis.duckdb.connect()
        try:
            empty_df = pl.DataFrame(
                {
                    "id": pl.Series([], dtype=pl.Int64),
                    "name": pl.Series([], dtype=pl.String),
                }
            )
            conn.create_table("empty", empty_df)
            table = conn.table("empty")

            source = IbisSource(table, "empty")
            result = source.execute_query("SELECT * FROM empty")

            executed = result.execute()
            assert len(executed) == 0
        finally:
            conn.disconnect()

    def test_multiple_categorical_columns(self):
        """Test schema with multiple categorical columns (UNION query path)."""
        from querychat._datasource import IbisSource

        conn = ibis.duckdb.connect()
        try:
            conn.create_table(
                "multi_cat",
                {
                    "status": ["active", "inactive", "active"],
                    "type": ["A", "B", "A"],
                    "region": ["US", "EU", "US"],
                    "value": [1, 2, 3],
                },
            )
            table = conn.table("multi_cat")

            source = IbisSource(table, "multi_cat")
            schema = source.get_schema(categorical_threshold=10)

            # All three text columns should be categorical
            assert "'active'" in schema
            assert "'inactive'" in schema
            assert "'A'" in schema
            assert "'B'" in schema
            assert "'US'" in schema
            assert "'EU'" in schema
        finally:
            conn.disconnect()

    def test_no_categorical_columns(self):
        """Test schema with only numeric columns (early return path)."""
        from querychat._datasource import IbisSource

        conn = ibis.duckdb.connect()
        try:
            conn.create_table(
                "numeric_only",
                {"x": [1, 2, 3], "y": [4.0, 5.0, 6.0], "z": [7, 8, 9]},
            )
            table = conn.table("numeric_only")

            source = IbisSource(table, "numeric_only")
            schema = source.get_schema(categorical_threshold=10)

            assert "Categorical values:" not in schema
            assert "Range:" in schema
        finally:
            conn.disconnect()

    def test_column_with_all_nulls(self):
        """Test schema handles columns with all NULL values."""
        from querychat._datasource import IbisSource

        conn = ibis.duckdb.connect()
        try:
            # Create table with NULL column using raw SQL
            conn.raw_sql("""
                CREATE TABLE nulls AS
                SELECT NULL::VARCHAR as name, 1 as id
                UNION ALL
                SELECT NULL::VARCHAR, 2
            """)
            table = conn.table("nulls")

            source = IbisSource(table, "nulls")
            # Should not crash
            schema = source.get_schema(categorical_threshold=10)
            assert "name" in schema
            assert "id" in schema
        finally:
            conn.disconnect()

    def test_high_cardinality_text_not_categorical(self):
        """Test that high-cardinality text columns are not listed as categorical."""
        from querychat._datasource import IbisSource

        conn = ibis.duckdb.connect()
        try:
            # Create 100 unique values
            conn.create_table(
                "high_card",
                {
                    "id": list(range(100)),
                    "unique_str": [f"val_{i}" for i in range(100)],
                },
            )
            table = conn.table("high_card")

            source = IbisSource(table, "high_card")
            # Threshold of 10 should exclude 100 unique values
            schema = source.get_schema(categorical_threshold=10)

            # unique_str should NOT have categorical values listed
            assert "Categorical values:" not in schema
        finally:
            conn.disconnect()

    def test_categorical_at_threshold_boundary(self):
        """Test categorical detection at exact threshold boundary."""
        from querychat._datasource import IbisSource

        conn = ibis.duckdb.connect()
        try:
            # Create exactly 5 unique values
            conn.create_table(
                "boundary",
                {
                    "category": ["a", "b", "c", "d", "e", "a", "b"],
                },
            )
            table = conn.table("boundary")

            source = IbisSource(table, "boundary")

            # At threshold=5, should be categorical
            schema_at = source.get_schema(categorical_threshold=5)
            assert "Categorical values:" in schema_at

            # At threshold=4, should NOT be categorical
            schema_below = source.get_schema(categorical_threshold=4)
            assert "Categorical values:" not in schema_below
        finally:
            conn.disconnect()

    def test_cleanup_is_safe_noop(self):
        """Test that cleanup() doesn't break anything."""
        from querychat._datasource import IbisSource

        conn = ibis.duckdb.connect()
        try:
            conn.create_table("test", {"x": [1, 2, 3]})
            table = conn.table("test")

            source = IbisSource(table, "test")

            # cleanup should be a no-op
            source.cleanup()

            # Should still be able to use the source after cleanup
            result = source.get_data()
            assert result.execute().shape[0] == 3

            # Should still be able to execute queries
            query_result = source.execute_query("SELECT * FROM test")
            assert query_result.execute().shape[0] == 3
        finally:
            conn.disconnect()

    def test_get_data_after_execute_query(self):
        """Test that get_data still returns original after queries."""
        from querychat._datasource import IbisSource

        conn = ibis.duckdb.connect()
        try:
            conn.create_table("test", {"x": [1, 2, 3, 4, 5]})
            table = conn.table("test")

            source = IbisSource(table, "test")

            # Execute a filtered query
            source.execute_query("SELECT * FROM test WHERE x > 3")

            # get_data should still return original unfiltered data
            result = source.get_data()
            assert result.execute().shape[0] == 5
        finally:
            conn.disconnect()
