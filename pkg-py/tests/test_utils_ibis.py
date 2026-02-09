"""Tests for utility functions with Ibis Tables."""

import pytest

ibis = pytest.importorskip("ibis")

import narwhals.stable.v1 as nw  # noqa: E402
from querychat._utils import as_narwhals, df_to_html, is_ibis_table  # noqa: E402


@pytest.fixture
def ibis_conn():
    """Create a DuckDB connection for tests."""
    conn = ibis.duckdb.connect()
    yield conn
    conn.disconnect()


@pytest.fixture
def ibis_table(ibis_conn):
    """Create a sample Ibis Table."""
    ibis_conn.create_table(
        "sample",
        {"x": [1, 2, 3, 4, 5], "name": ["a", "b", "c", "d", "e"]},
    )
    return ibis_conn.table("sample")


@pytest.fixture
def empty_ibis_table(ibis_conn):
    """Create an empty Ibis Table."""
    import polars as pl

    # Use empty polars DataFrame to create empty table
    empty_df = pl.DataFrame(
        {"x": pl.Series([], dtype=pl.Int64), "name": pl.Series([], dtype=pl.String)}
    )
    ibis_conn.create_table("empty", empty_df)
    return ibis_conn.table("empty")


class TestIsIbisTable:
    """Tests for is_ibis_table() TypeGuard."""

    def test_returns_true_for_ibis_table(self, ibis_table):
        assert is_ibis_table(ibis_table) is True

    def test_returns_false_for_dataframe(self):
        import pandas as pd

        df = pd.DataFrame({"x": [1, 2, 3]})
        assert is_ibis_table(df) is False

    def test_returns_false_for_none(self):
        assert is_ibis_table(None) is False

    def test_returns_false_for_string(self):
        assert is_ibis_table("not a table") is False

    def test_returns_false_for_polars_dataframe(self):
        import polars as pl

        df = pl.DataFrame({"x": [1, 2, 3]})
        assert is_ibis_table(df) is False

    def test_returns_false_for_polars_lazyframe(self):
        import polars as pl

        lf = pl.LazyFrame({"x": [1, 2, 3]})
        assert is_ibis_table(lf) is False


class TestAsNarwhalsWithIbis:
    """Tests for as_narwhals() with Ibis Tables."""

    def test_eager_collection(self, ibis_table):
        """Verify lazy=False collects Ibis Table to DataFrame."""
        result = as_narwhals(ibis_table, lazy=False)
        assert isinstance(result, nw.DataFrame)
        assert result.shape == (5, 2)
        assert set(result.columns) == {"x", "name"}

    def test_lazy_conversion(self, ibis_table):
        """Verify lazy=True returns LazyFrame."""
        result = as_narwhals(ibis_table, lazy=True)
        assert isinstance(result, nw.LazyFrame)
        # Collect to verify data
        collected = result.collect()
        assert collected.shape == (5, 2)

    def test_empty_table_eager(self, empty_ibis_table):
        """Verify empty table works with lazy=False."""
        result = as_narwhals(empty_ibis_table, lazy=False)
        assert isinstance(result, nw.DataFrame)
        assert result.shape[0] == 0

    def test_empty_table_lazy(self, empty_ibis_table):
        """Verify empty table works with lazy=True."""
        result = as_narwhals(empty_ibis_table, lazy=True)
        assert isinstance(result, nw.LazyFrame)
        assert result.collect().shape[0] == 0

    def test_default_is_eager(self, ibis_table):
        """Verify default (no lazy param) returns eager DataFrame."""
        result = as_narwhals(ibis_table)
        assert isinstance(result, nw.DataFrame)

    def test_preserves_data_values(self, ibis_table):
        """Verify data values are preserved through conversion."""
        result = as_narwhals(ibis_table, lazy=False)
        x_values = result.get_column("x").to_list()
        assert x_values == [1, 2, 3, 4, 5]

        name_values = result.get_column("name").to_list()
        assert name_values == ["a", "b", "c", "d", "e"]


class TestDfToHtmlWithIbis:
    """Tests for df_to_html() with Ibis Tables."""

    def test_basic_html_generation(self, ibis_table):
        """Verify HTML is generated from Ibis Table."""
        html = df_to_html(ibis_table, maxrows=3)
        assert "<table" in html.lower()
        assert "Showing 3 of 5 rows" in html

    def test_full_table_no_truncation_message(self, ibis_table):
        """Verify no truncation message when showing all rows."""
        html = df_to_html(ibis_table, maxrows=10)
        assert "Showing" not in html

    def test_empty_table(self, empty_ibis_table):
        """Verify empty table produces valid HTML."""
        html = df_to_html(empty_ibis_table, maxrows=5)
        assert "<table" in html.lower()

    def test_single_row_table(self, ibis_conn):
        """Verify single-row table works."""
        ibis_conn.create_table("single", {"x": [42]})
        table = ibis_conn.table("single")
        html = df_to_html(table, maxrows=5)
        assert "<table" in html.lower()
        # Should not show truncation for 1 row with maxrows=5
        assert "Showing" not in html

    def test_exact_maxrows_no_truncation(self, ibis_table):
        """Verify no truncation message when rows == maxrows."""
        html = df_to_html(ibis_table, maxrows=5)
        # 5 rows with maxrows=5 should not show truncation
        assert "Showing" not in html

    def test_contains_column_data(self, ibis_table):
        """Verify HTML contains actual data from the table."""
        html = df_to_html(ibis_table, maxrows=5)
        # Should contain the column values
        assert "1" in html  # x values
        assert "a" in html  # name values
