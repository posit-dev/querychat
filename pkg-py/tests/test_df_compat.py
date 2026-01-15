"""Tests for the _df_compat module and narwhals DataFrame compatibility."""

import gzip
import tempfile
from pathlib import Path

import duckdb
import narwhals.stable.v1 as nw
import pytest
from querychat._df_compat import duckdb_result_to_polars, read_csv

# Check if polars and pyarrow are available (both needed for DuckDB + polars)
try:
    import polars as pl
    import pyarrow as pa  # noqa: F401

    HAS_POLARS_WITH_PYARROW = True
except ImportError:
    HAS_POLARS_WITH_PYARROW = False
    pl = None  # type: ignore[assignment]


class TestReadCsv:
    """
    Tests for the read_csv function.

    Note: read_csv is designed for reading gzipped CSV files (used for bundled data).
    """

    @pytest.fixture
    def gzip_csv_file(self):
        """Create a temporary gzipped CSV file for testing."""
        with tempfile.NamedTemporaryFile(suffix=".csv.gz", delete=False) as f:
            temp_path = f.name

        with gzip.open(temp_path, "wt") as f:
            f.write("id,name,value\n")
            f.write("1,Alice,100\n")
            f.write("2,Bob,200\n")
            f.write("3,Charlie,300\n")

        yield temp_path
        Path(temp_path).unlink()

    def test_read_csv_returns_narwhals_dataframe(self, gzip_csv_file):
        """Test that read_csv returns a narwhals DataFrame."""
        result = read_csv(gzip_csv_file)
        assert isinstance(result, nw.DataFrame)

    def test_read_csv_has_correct_shape(self, gzip_csv_file):
        """Test that read_csv produces correct data."""
        result = read_csv(gzip_csv_file)
        assert result.shape == (3, 3)
        assert list(result.columns) == ["id", "name", "value"]

    def test_read_csv_data_integrity(self, gzip_csv_file):
        """Test that read_csv preserves data correctly."""
        result = read_csv(gzip_csv_file)
        names = result["name"].to_list()
        assert names == ["Alice", "Bob", "Charlie"]


@pytest.mark.skipif(
    not HAS_POLARS_WITH_PYARROW, reason="polars or pyarrow not installed"
)
class TestDuckdbResultToPolars:
    """Tests for the duckdb_result_to_polars function."""

    @pytest.fixture
    def duckdb_conn(self):
        """Create a DuckDB connection with test data."""
        conn = duckdb.connect(":memory:")
        conn.execute("CREATE TABLE test (id INTEGER, name VARCHAR, value DOUBLE)")
        conn.execute("INSERT INTO test VALUES (1, 'Alice', 10.5)")
        conn.execute("INSERT INTO test VALUES (2, 'Bob', 20.5)")
        yield conn
        conn.close()

    def test_duckdb_result_returns_polars_dataframe(self, duckdb_conn):
        """Test that duckdb_result_to_polars returns a polars DataFrame."""
        result = duckdb_conn.execute("SELECT * FROM test")
        df = duckdb_result_to_polars(result)
        assert isinstance(df, pl.DataFrame)

    def test_duckdb_result_has_correct_data(self, duckdb_conn):
        """Test that duckdb_result_to_polars preserves data correctly."""
        result = duckdb_conn.execute("SELECT * FROM test ORDER BY id")
        df = duckdb_result_to_polars(result)

        assert df.shape == (2, 3)
        assert list(df.columns) == ["id", "name", "value"]
        assert df["id"].to_list() == [1, 2]
        assert df["name"].to_list() == ["Alice", "Bob"]

    def test_duckdb_result_empty_query(self, duckdb_conn):
        """Test handling of empty query results."""
        result = duckdb_conn.execute("SELECT * FROM test WHERE id > 100")
        df = duckdb_result_to_polars(result)

        assert isinstance(df, pl.DataFrame)
        assert df.shape == (0, 3)


@pytest.mark.skipif(
    not HAS_POLARS_WITH_PYARROW, reason="polars or pyarrow not installed"
)
class TestPolarsBackend:
    """Tests that verify polars backend works correctly when available."""

    def test_read_csv_uses_polars_when_available(self):
        """Test that read_csv uses polars as the backend when available."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("x,y\n1,2\n3,4\n")
            temp_path = f.name

        try:
            result = read_csv(temp_path)
            # The native frame should be polars when polars is available
            native = result.to_native()
            assert isinstance(native, pl.DataFrame)
        finally:
            Path(temp_path).unlink()
