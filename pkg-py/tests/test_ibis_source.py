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
