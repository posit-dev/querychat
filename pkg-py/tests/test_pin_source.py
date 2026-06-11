from __future__ import annotations

import duckdb
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


class TestPinSourceLazyPath:
    def test_parquet_pin(self, board, sample_df):
        board.pin_write(sample_df, "test_data", type="parquet")
        ps = PinSource(board, "test_data")

        result = ps.execute_query("SELECT * FROM test_data")
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 4
        assert list(result.columns) == ["name", "age", "score"]
        ps.cleanup()

    def test_csv_pin(self, board, sample_df):
        board.pin_write(sample_df, "csv_data", type="csv")
        ps = PinSource(board, "csv_data")

        result = ps.execute_query("SELECT * FROM csv_data WHERE age > 28")
        assert isinstance(result, pd.DataFrame)
        assert all(result["age"] > 28)
        ps.cleanup()

    def test_json_pin(self, board, sample_df):
        board.pin_write(sample_df, "json_data", type="json")
        ps = PinSource(board, "json_data")

        result = ps.get_data()
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 4
        ps.cleanup()

    def test_parquet_pin_filtered_query(self, board, sample_df):
        board.pin_write(sample_df, "filtered_data", type="parquet")
        ps = PinSource(board, "filtered_data")

        result = ps.execute_query("SELECT name FROM filtered_data WHERE score > 90")
        assert isinstance(result, pd.DataFrame)
        assert list(result.columns) == ["name"]
        assert len(result) == 2
        ps.cleanup()


class TestPinSourceSchema:
    def test_get_schema(self, board, sample_df):
        board.pin_write(sample_df, "schema_test", type="parquet")
        ps = PinSource(board, "schema_test")

        schema = ps.get_schema(categorical_threshold=20)
        assert "schema_test" in schema
        assert "name" in schema
        assert "age" in schema
        assert "score" in schema
        ps.cleanup()

    def test_get_schema_table_header(self, board, sample_df):
        board.pin_write(sample_df, "header_test", type="parquet")
        ps = PinSource(board, "header_test")

        schema = ps.get_schema(categorical_threshold=20)
        lines = schema.split("\n")
        assert lines[0] == "Table: header_test"
        assert lines[1] == "Columns:"
        ps.cleanup()

    def test_get_schema_categorical_values(self, board):
        df = pd.DataFrame({"category": ["A", "B", "A", "C", "B"], "value": [1, 2, 3, 4, 5]})
        board.pin_write(df, "cat_test", type="parquet")
        ps = PinSource(board, "cat_test")

        schema = ps.get_schema(categorical_threshold=5)
        assert "Categorical values:" in schema
        assert "'A'" in schema
        assert "'B'" in schema
        assert "'C'" in schema
        ps.cleanup()

    def test_get_schema_numeric_range(self, board, sample_df):
        board.pin_write(sample_df, "range_test", type="parquet")
        ps = PinSource(board, "range_test")

        schema = ps.get_schema(categorical_threshold=20)
        assert "Range:" in schema
        assert "25" in schema
        assert "35" in schema
        ps.cleanup()

    def test_get_db_type(self, board, sample_df):
        board.pin_write(sample_df, "db_type_test", type="parquet")
        ps = PinSource(board, "db_type_test")

        assert ps.get_db_type() == "DuckDB"
        ps.cleanup()

    def test_test_query(self, board, sample_df):
        board.pin_write(sample_df, "tq_test", type="parquet")
        ps = PinSource(board, "tq_test")

        result = ps.test_query("SELECT * FROM tq_test")
        assert len(result) == 1
        ps.cleanup()


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

        desc = ps.get_data_description()
        assert "Test Dataset" in desc
        assert "A sample dataset for testing" in desc
        ps.cleanup()

    def test_get_data_description_minimal(self, board, sample_df):
        board.pin_write(sample_df, "minimal_pin", type="parquet")
        ps = PinSource(board, "minimal_pin")

        desc = ps.get_data_description()
        assert isinstance(desc, str)
        assert "minimal_pin" in desc
        ps.cleanup()

    def test_pin_meta_property(self, board, sample_df):
        board.pin_write(sample_df, "meta_test", type="parquet")
        ps = PinSource(board, "meta_test")

        meta = ps.pin_meta
        assert meta is not None
        assert meta.name == "meta_test"
        ps.cleanup()

    def test_pin_meta_type(self, board, sample_df):
        board.pin_write(sample_df, "type_test", type="parquet")
        ps = PinSource(board, "type_test")

        assert ps.pin_meta.type == "parquet"
        ps.cleanup()


class TestPinSourceTableName:
    def test_defaults_to_pin_name(self, board, sample_df):
        board.pin_write(sample_df, "my_pin", type="parquet")
        ps = PinSource(board, "my_pin")

        assert ps.table_name == "my_pin"
        result = ps.execute_query("SELECT * FROM my_pin")
        assert len(result) == 4
        ps.cleanup()

    def test_custom_table_name(self, board, sample_df):
        board.pin_write(sample_df, "my_pin", type="parquet")
        ps = PinSource(board, "my_pin", table_name="custom_table")

        assert ps.table_name == "custom_table"
        result = ps.execute_query("SELECT * FROM custom_table")
        assert len(result) == 4
        ps.cleanup()

    def test_custom_table_name_in_schema(self, board, sample_df):
        board.pin_write(sample_df, "schema_pin", type="parquet")
        ps = PinSource(board, "schema_pin", table_name="my_table")

        schema = ps.get_schema(categorical_threshold=10)
        assert "my_table" in schema
        assert "schema_pin" not in schema
        ps.cleanup()


class TestPinSourceSecurity:
    def test_duckdb_locked_down(self, board, sample_df):
        board.pin_write(sample_df, "secure_test", type="parquet")
        ps = PinSource(board, "secure_test")

        with pytest.raises(
            duckdb.PermissionException, match="has been disabled"
        ):
            ps.execute_query("SELECT * FROM read_csv_auto('/etc/passwd')")
        ps.cleanup()

    def test_blocks_unsafe_queries(self, board, sample_df):
        from querychat._utils import UnsafeQueryError

        board.pin_write(sample_df, "unsafe_test", type="parquet")
        ps = PinSource(board, "unsafe_test")

        with pytest.raises(UnsafeQueryError):
            ps.execute_query("DROP TABLE unsafe_test")
        ps.cleanup()


class TestQueryChatPinSourceIntegration:
    def test_auto_fills_data_description(self, board, sample_df):
        from querychat import QueryChat

        board.pin_write(
            sample_df, "cars", type="parquet",
            title="Motor Trend Cars", description="Road test data",
        )
        ps = PinSource(board, "cars")
        qc = QueryChat(data_source=ps, table_name="cars", greeting="Hi")

        prompt = qc._system_prompt.render(qc.tools)
        assert "Motor Trend Cars" in prompt
        assert "Road test data" in prompt
        qc.cleanup()

    def test_explicit_description_overrides_pin_metadata(self, board, sample_df):
        from querychat import QueryChat

        board.pin_write(
            sample_df, "cars", type="parquet", title="Motor Trend Cars",
        )
        ps = PinSource(board, "cars")
        qc = QueryChat(
            data_source=ps, table_name="cars", greeting="Hi",
            data_description="Custom description",
        )

        prompt = qc._system_prompt.render(qc.tools)
        assert "Custom description" in prompt
        assert "Motor Trend Cars" not in prompt
        qc.cleanup()

    def test_clears_auto_description_on_source_change(self, board, sample_df):
        from querychat import QueryChat

        board.pin_write(
            sample_df, "cars", type="parquet", title="Motor Trend Cars",
        )
        ps = PinSource(board, "cars")
        qc = QueryChat(data_source=ps, table_name="cars", greeting="Hi")

        prompt_before = qc._system_prompt.render(qc.tools)
        assert "Motor Trend Cars" in prompt_before

        qc.data_source = sample_df
        prompt_after = qc._system_prompt.render(qc.tools)
        assert "Motor Trend Cars" not in prompt_after
        qc.cleanup()
