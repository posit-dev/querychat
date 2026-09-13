from __future__ import annotations

import duckdb
import narwhals.stable.v1 as nw
import pandas as pd
import pytest

pins = pytest.importorskip("pins")

from querychat._pin_source import PinSource  # noqa: E402


@pytest.fixture
def board(tmp_path):
    return pins.board_folder(str(tmp_path))


@pytest.fixture
def sample_df():
    return pd.DataFrame(
        {
            "name": ["Alice", "Bob", "Charlie", "Diana"],
            "age": [30, 25, 35, 28],
            "score": [85.5, 92.3, 78.1, 95.0],
        }
    )


@pytest.fixture
def parquet_source(board, sample_df):
    board.pin_write(sample_df, "test_data", type="parquet")
    ps = PinSource(board, "test_data")
    yield ps
    ps.cleanup()


class TestPinSourceLazyPath:
    def test_parquet_pin(self, parquet_source):
        result = parquet_source.execute_query("SELECT * FROM test_data")
        assert isinstance(result, nw.DataFrame)
        assert len(result) == 4
        assert list(result.columns) == ["name", "age", "score"]

    def test_csv_pin(self, board, sample_df):
        board.pin_write(sample_df, "csv_data", type="csv")
        ps = PinSource(board, "csv_data")
        try:
            result = ps.execute_query("SELECT * FROM csv_data WHERE age > 28")
            assert isinstance(result, nw.DataFrame)
            assert all(result["age"] > 28)
        finally:
            ps.cleanup()

    def test_json_pin(self, board, sample_df):
        board.pin_write(sample_df, "json_data", type="json")
        ps = PinSource(board, "json_data")
        try:
            result = ps.get_data()
            assert isinstance(result, nw.DataFrame)
            assert len(result) == 4
        finally:
            ps.cleanup()

    def test_arrow_pin(self, board, sample_df):
        board.pin_write(sample_df, "arrow_data", type="arrow")
        ps = PinSource(board, "arrow_data")
        try:
            result = ps.execute_query("SELECT * FROM arrow_data")
            assert isinstance(result, nw.DataFrame)
            assert len(result) == 4
            assert list(result.columns) == ["name", "age", "score"]
        finally:
            ps.cleanup()

    def test_parquet_pin_filtered_query(self, parquet_source, sample_df):
        result = parquet_source.execute_query(
            "SELECT name FROM test_data WHERE score > 90"
        )
        assert isinstance(result, nw.DataFrame)
        assert list(result.columns) == ["name"]
        assert len(result) == 2


class TestPinSourceSchema:
    def test_get_schema(self, parquet_source):
        schema = parquet_source.get_schema(categorical_threshold=20)
        assert "test_data" in schema
        assert "name" in schema
        assert "age" in schema
        assert "score" in schema

    def test_get_schema_table_header(self, parquet_source):
        schema = parquet_source.get_schema(categorical_threshold=20)
        lines = schema.split("\n")
        assert lines[0] == "Table: test_data"
        assert lines[1] == "Columns:"

    def test_get_schema_categorical_values(self, board):
        df = pd.DataFrame(
            {"category": ["A", "B", "A", "C", "B"], "value": [1, 2, 3, 4, 5]}
        )
        board.pin_write(df, "cat_test", type="parquet")
        ps = PinSource(board, "cat_test")
        try:
            schema = ps.get_schema(categorical_threshold=5)
            assert "Categorical values:" in schema
            assert "'A'" in schema
            assert "'B'" in schema
            assert "'C'" in schema
        finally:
            ps.cleanup()

    def test_get_schema_numeric_range(self, parquet_source):
        schema = parquet_source.get_schema(categorical_threshold=20)
        assert "Range:" in schema
        assert "25" in schema
        assert "35" in schema

    def test_get_db_type(self, parquet_source):
        assert parquet_source.get_db_type() == "DuckDB"

    def test_test_query(self, parquet_source):
        result = parquet_source.test_query("SELECT * FROM test_data")
        assert len(result) == 1

    def test_test_query_trailing_semicolon(self, parquet_source):
        result = parquet_source.test_query("SELECT * FROM test_data;")
        assert len(result) == 1


class TestPinSourceMetadata:
    def test_get_data_description_with_title_and_description(self, board, sample_df):
        board.pin_write(
            sample_df,
            "described_pin",
            type="parquet",
            title="Test Dataset",
            description="A sample dataset for testing",
        )
        ps = PinSource(board, "described_pin")
        try:
            desc = ps.get_data_description()
            assert "Test Dataset" in desc
            assert "A sample dataset for testing" in desc
        finally:
            ps.cleanup()

    def test_get_data_description_minimal(self, parquet_source):
        desc = parquet_source.get_data_description()
        assert isinstance(desc, str)
        assert "test_data" in desc

    def test_pin_meta_property(self, parquet_source):
        meta = parquet_source.pin_meta
        assert meta is not None
        assert meta.name == "test_data"

    def test_pin_meta_type(self, parquet_source):
        assert parquet_source.pin_meta.type == "parquet"


class TestPinSourceTableName:
    def test_defaults_to_pin_name(self, parquet_source):
        assert parquet_source.table_name == "test_data"
        result = parquet_source.execute_query("SELECT * FROM test_data")
        assert len(result) == 4

    def test_custom_table_name(self, board, sample_df):
        board.pin_write(sample_df, "my_pin", type="parquet")
        ps = PinSource(board, "my_pin", table_name="custom_table")
        try:
            assert ps.table_name == "custom_table"
            result = ps.execute_query("SELECT * FROM custom_table")
            assert len(result) == 4
        finally:
            ps.cleanup()

    def test_custom_table_name_in_schema(self, board, sample_df):
        board.pin_write(sample_df, "schema_pin", type="parquet")
        ps = PinSource(board, "schema_pin", table_name="my_table")
        try:
            schema = ps.get_schema(categorical_threshold=10)
            assert "my_table" in schema
            assert "schema_pin" not in schema
        finally:
            ps.cleanup()


class TestPinSourceErrors:
    def test_rejects_multi_file_pin(self, board, sample_df, tmp_path):
        from unittest.mock import patch

        board.pin_write(sample_df, "multi_pin", type="parquet")

        fake_paths = [str(tmp_path / "a.parquet"), str(tmp_path / "b.parquet")]
        with (
            patch.object(board, "pin_download", return_value=fake_paths),
            pytest.raises(ValueError, match="contains 2 files"),
        ):
            PinSource(board, "multi_pin")


class TestPinSourceSecurity:
    def test_duckdb_locked_down(self, parquet_source):
        with pytest.raises(duckdb.PermissionException, match="has been disabled"):
            parquet_source.execute_query("SELECT * FROM read_csv_auto('/etc/passwd')")

    def test_blocks_unsafe_queries(self, parquet_source):
        from querychat._utils import UnsafeQueryError

        with pytest.raises(UnsafeQueryError):
            parquet_source.execute_query("DROP TABLE test_data")


class TestQueryChatPinSourceIntegration:
    def test_auto_fills_data_description(self, board, sample_df):
        from querychat import QueryChat

        board.pin_write(
            sample_df,
            "cars",
            type="parquet",
            title="Motor Trend Cars",
            description="Road test data",
        )
        ps = PinSource(board, "cars")
        qc = QueryChat(data_source=ps, table_name="cars", greeting="Hi")
        try:
            prompt = qc._table_set.system_prompt.render(qc.tools)
            assert "Motor Trend Cars" in prompt
            assert "Road test data" in prompt
        finally:
            qc.cleanup()

    def test_explicit_description_overrides_pin_metadata(self, board, sample_df):
        from querychat import QueryChat

        board.pin_write(
            sample_df,
            "cars",
            type="parquet",
            title="Motor Trend Cars",
        )
        ps = PinSource(board, "cars")
        qc = QueryChat(
            data_source=ps,
            table_name="cars",
            greeting="Hi",
            data_description="Custom description",
        )
        try:
            prompt = qc._table_set.system_prompt.render(qc.tools)
            assert "Custom description" in prompt
            assert "Motor Trend Cars" not in prompt
        finally:
            qc.cleanup()

    def test_explicit_description_survives_source_change(self, board, sample_df):
        from querychat import QueryChat

        board.pin_write(
            sample_df,
            "cars",
            type="parquet",
            title="Motor Trend Cars",
        )
        ps = PinSource(board, "cars")
        qc = QueryChat(
            data_source=ps,
            table_name="cars",
            greeting="Hi",
            data_description="Custom description",
        )
        try:
            qc.add_table(sample_df, "cars", replace=True)
            prompt = qc._table_set.system_prompt.render(qc.tools)
            assert "Custom description" in prompt
            assert "Motor Trend Cars" not in prompt
        finally:
            qc.cleanup()

    def test_clears_auto_description_on_source_change(self, board, sample_df):
        from querychat import QueryChat

        board.pin_write(
            sample_df,
            "cars",
            type="parquet",
            title="Motor Trend Cars",
        )
        ps = PinSource(board, "cars")
        qc = QueryChat(data_source=ps, table_name="cars", greeting="Hi")
        try:
            prompt_before = qc._table_set.system_prompt.render(qc.tools)
            assert "Motor Trend Cars" in prompt_before

            qc.add_table(sample_df, "cars", replace=True)
            prompt_after = qc._table_set.system_prompt.render(qc.tools)
            assert "Motor Trend Cars" not in prompt_after
        finally:
            qc.cleanup()


class TestMultiplePins:
    """Multiple pins (and pin + data frame mixes) share a DuckDB executor."""

    def test_second_pin_passes_compatibility_check(self, board, sample_df):
        from querychat._query_executor import check_source_compatibility

        board.pin_write(sample_df, "pin_a", type="parquet")
        board.pin_write(sample_df, "pin_b", type="parquet")
        first = PinSource(board, "pin_a")
        second = PinSource(board, "pin_b")
        try:
            check_source_compatibility({"pin_a": first}, second, "pin_b")
        finally:
            first.cleanup()
            second.cleanup()

    def test_two_pins_query_through_shared_executor(self, board, sample_df):
        from querychat import QueryChat
        from querychat._query_executor import DuckDBExecutor

        board.pin_write(sample_df, "pin_a", type="parquet")
        cities = pd.DataFrame(
            {"name": ["Alice", "Diana"], "city": ["Springfield", "Shelbyville"]}
        )
        board.pin_write(cities, "pin_b", type="csv")

        qc = QueryChat(board, "pin_a")
        try:
            qc.add_table(board, "pin_b")
            executor = qc._table_set.executor
            assert isinstance(executor, DuckDBExecutor)

            result = nw.from_native(
                executor.execute_query(
                    "SELECT a.name, b.city FROM pin_a a "
                    "JOIN pin_b b ON a.name = b.name ORDER BY a.name"
                )
            )
            assert result.rows(named=True) == [
                {"name": "Alice", "city": "Springfield"},
                {"name": "Diana", "city": "Shelbyville"},
            ]

            # Per-table schema and validation work for both pins
            metas = executor.get_column_metas("pin_b")
            assert {m.name for m in metas} == {"name", "city"}
            executor.test_query(
                "SELECT * FROM pin_b", table_name="pin_b", require_all_columns=True
            )
        finally:
            qc.cleanup()

    def test_pin_and_dataframe_mix(self, board, sample_df):
        from querychat import QueryChat
        from querychat._query_executor import DuckDBExecutor

        board.pin_write(sample_df, "pin_a", type="parquet")
        qc = QueryChat(board, "pin_a")
        try:
            qc.add_table(
                pd.DataFrame({"name": ["Bob"], "dept": ["Engineering"]}),
                "employees",
            )
            executor = qc._table_set.executor
            assert isinstance(executor, DuckDBExecutor)

            result = nw.from_native(
                executor.execute_query(
                    "SELECT e.dept FROM pin_a p JOIN employees e ON p.name = e.name"
                )
            )
            assert result.rows(named=True) == [{"dept": "Engineering"}]
        finally:
            qc.cleanup()

    def test_mixed_dataframe_backends_still_rejected_with_pin(self, board, sample_df):
        pl = pytest.importorskip("polars")

        from querychat import QueryChat

        board.pin_write(sample_df, "pin_a", type="parquet")
        qc = QueryChat(board, "pin_a")
        try:
            qc.add_table(sample_df, "pandas_table")
            with pytest.raises(ValueError, match="same DataFrame backend"):
                qc.add_table(pl.DataFrame({"x": [1]}), "polars_table")
        finally:
            qc.cleanup()

    def test_pin_with_non_sql_safe_name(self, board, sample_df):
        """Registry keys that need quoting work in the shared executor."""
        from querychat import QueryChat

        board.pin_write(sample_df, "sales-2026", type="parquet")
        board.pin_write(sample_df, "pin_b", type="parquet")
        qc = QueryChat(board, "sales-2026")
        try:
            qc.add_table(board, "pin_b")
            executor = qc._table_set.executor
            result = nw.from_native(
                executor.execute_query('SELECT COUNT(*) AS n FROM "sales-2026"')
            )
            assert result.rows(named=True) == [{"n": 4}]
        finally:
            qc.cleanup()

    def test_shared_executor_uses_version_resolved_at_construction(
        self, board, sample_df
    ):
        """Updating a pin after construction doesn't change the shared table."""
        from querychat import QueryChat

        board.pin_write(sample_df, "pin_a", type="parquet")
        board.pin_write(sample_df, "pin_b", type="parquet")
        qc = QueryChat(board, "pin_a")
        try:
            qc.add_table(board, "pin_b")
            # New version of pin_a published after its PinSource was built
            board.pin_write(sample_df.head(1), "pin_a", type="parquet")
            executor = qc._table_set.executor
            result = nw.from_native(
                executor.execute_query("SELECT COUNT(*) AS n FROM pin_a")
            )
            assert result.rows(named=True) == [{"n": 4}]
        finally:
            qc.cleanup()

    def test_shared_executor_falls_back_when_snapshot_version_is_pruned(
        self, tmp_path, sample_df
    ):
        """
        Non-versioned boards drop old versions on rewrite; the shared table
        must still match the source's own copy.
        """
        from querychat import QueryChat

        unversioned = pins.board_folder(str(tmp_path / "unversioned"), versioned=False)
        unversioned.pin_write(sample_df, "pin_a", type="parquet")
        unversioned.pin_write(sample_df, "pin_b", type="parquet")
        qc = QueryChat(unversioned, "pin_a")
        try:
            qc.add_table(unversioned, "pin_b")
            unversioned.pin_write(sample_df.head(1), "pin_a", type="parquet")
            executor = qc._table_set.executor
            result = nw.from_native(
                executor.execute_query("SELECT COUNT(*) AS n FROM pin_a")
            )
            assert result.rows(named=True) == [{"n": 4}]
        finally:
            qc.cleanup()

    def test_executor_cleanup_leaves_pin_connections(self, board, sample_df):
        """The shared connection is executor-owned; pins keep their own."""
        from querychat import QueryChat

        board.pin_write(sample_df, "pin_a", type="parquet")
        board.pin_write(sample_df, "pin_b", type="parquet")
        qc = QueryChat(board, "pin_a")
        try:
            qc.add_table(board, "pin_b")
            _ = qc._table_set.executor  # build the shared executor
            qc._table_set.cleanup_executor()

            # Both pins still answer source-level queries through their
            # private connections.
            for name in ("pin_a", "pin_b"):
                result = qc._data_sources[name].execute_query(
                    f"SELECT COUNT(*) AS n FROM {name}"
                )
                assert result.rows(named=True) == [{"n": 4}]
        finally:
            qc.cleanup()
