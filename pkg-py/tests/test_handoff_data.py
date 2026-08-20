import pytest
import querychat._handoff_data as handoff_data
from querychat._datasource import DataFrameSource
from querychat._handoff_types import HandoffLanguage
from querychat.data import tips


class RecordingDataFrameSource(DataFrameSource):
    def __init__(self, table_name: str):
        super().__init__(tips(), table_name)
        self.get_data_calls = 0
        self.export_error: Exception | None = None

    def get_data(self):
        self.get_data_calls += 1
        if self.export_error is not None:
            raise self.export_error
        return super().get_data()


@pytest.fixture
def tips_source():
    return DataFrameSource(tips(), "tips")


class TestHandoffDataCatalog:
    @pytest.mark.parametrize(
        ("language", "expected", "forbidden"),
        [
            ("python", "duckdb.connect()", "DBI::dbConnect"),
            ("r", "DBI::dbConnect(duckdb::duckdb())", "duckdb.connect()"),
        ],
    )
    def test_bundled_csv_instructions_match_target_language(
        self,
        tips_source: DataFrameSource,
        language: HandoffLanguage,
        expected: str,
        forbidden: str,
    ):
        catalog = handoff_data.prepare_handoff_data(
            {"tips": tips_source},
            language=language,
        )

        assert expected in catalog.prompt_instructions
        assert forbidden not in catalog.prompt_instructions

    @pytest.mark.parametrize(
        ("language", "expected", "forbidden"),
        [
            ("python", 'os.environ["DATABASE_URL"]', "Sys.getenv"),
            ("r", 'Sys.getenv("DATABASE_URL")', "os.environ"),
        ],
    )
    def test_database_instructions_match_target_language(
        self,
        language: HandoffLanguage,
        expected: str,
        forbidden: str,
    ):
        class DatabaseSource:
            def get_db_type(self) -> str:
                return "PostgreSQL"

        catalog = handoff_data.prepare_handoff_data(
            {"orders": DatabaseSource()},
            language=language,
        )

        assert expected in catalog.prompt_instructions
        assert forbidden not in catalog.prompt_instructions

    @pytest.mark.parametrize(
        ("language", "expected", "forbidden"),
        [
            ("python", 'os.environ["DATABASE_URL"]', "Sys.getenv"),
            ("r", 'Sys.getenv("DATABASE_URL")', "os.environ"),
        ],
    )
    def test_external_dataframe_instructions_require_user_supplied_setup(
        self,
        language: HandoffLanguage,
        expected: str,
        forbidden: str,
    ):
        instructions = handoff_data.external_dataframe_instructions(
            "tips",
            "DuckDB",
            language,
        )

        assert (
            'The original in-memory DataFrame for table "tips" is not bundled.'
            in instructions
        )
        assert "user-supplied data file or equivalent database connection" in instructions
        assert "dedicated DATA SETUP block" in instructions
        assert 'existing table name `"tips"`' in instructions
        assert expected in instructions
        assert forbidden not in instructions
        assert "path/to/your" not in instructions
        assert (
            "Do not claim to know the original file path, connection string, "
            "or credentials." in instructions
        )
        assert (
            "This setup may need adjustment before the handoff can run." in instructions
        )

    def test_prepare_describes_every_registered_table(self):
        sources = {
            "tips": DataFrameSource(tips(), "tips"),
            "tips_copy": DataFrameSource(tips(), "tips_copy"),
        }

        catalog = handoff_data.prepare_handoff_data(sources, language="python")

        assert set(catalog.entries) == {"tips", "tips_copy"}
        assert "tips.csv" in catalog.prompt_instructions
        assert "tips_copy.csv" in catalog.prompt_instructions

    def test_prepare_does_not_export_any_dataframe(self):
        tips_source = RecordingDataFrameSource("tips")
        unused_source = RecordingDataFrameSource("unused")

        handoff_data.prepare_handoff_data(
            {"tips": tips_source, "unused": unused_source},
            language="python",
        )

        assert tips_source.get_data_calls == 0
        assert unused_source.get_data_calls == 0

    def test_materialize_exports_only_referenced_dataframe(self):
        tips_source = RecordingDataFrameSource("tips")
        unused_source = RecordingDataFrameSource("unused")
        sources = {"tips": tips_source, "unused": unused_source}
        catalog = handoff_data.prepare_handoff_data(sources, language="python")

        context = handoff_data.materialize_handoff_data(
            catalog,
            sources,
            ["tips"],
        )

        assert set(context.bundled_files) == {"tips.csv"}
        assert context.bundled_tables == ["tips"]
        assert tips_source.get_data_calls == 1
        assert unused_source.get_data_calls == 0

    def test_materialize_deduplicates_referenced_tables_before_export(
        self,
        monkeypatch,
    ):
        source = RecordingDataFrameSource("tips")
        sources = {"tips": source}
        catalog = handoff_data.prepare_handoff_data(sources, language="python")
        csv_size = len(handoff_data.export_csv(source))
        source.get_data_calls = 0
        monkeypatch.setattr(
            "querychat._handoff_data.MAX_BUNDLE_SIZE",
            csv_size,
        )

        context = handoff_data.materialize_handoff_data(
            catalog,
            sources,
            ["tips", "tips"],
        )

        assert context.bundled_tables == ["tips"]
        assert list(context.bundled_files) == ["tips.csv"]
        assert context.data_instructions.count("tips.csv") == 1
        assert source.get_data_calls == 1

    def test_materialize_preserves_first_reference_order(self):
        sources = {
            "first": RecordingDataFrameSource("first"),
            "second": RecordingDataFrameSource("second"),
        }
        catalog = handoff_data.prepare_handoff_data(sources, language="python")

        context = handoff_data.materialize_handoff_data(
            catalog,
            sources,
            ["second", "first", "second"],
        )

        assert context.bundled_tables == ["second", "first"]
        assert list(context.bundled_files) == ["second.csv", "first.csv"]

    def test_materialized_csv_and_instructions_are_stable_after_source_mutation(self):
        source = RecordingDataFrameSource("tips")
        sources = {"tips": source}
        catalog = handoff_data.prepare_handoff_data(sources, language="python")

        context = handoff_data.materialize_handoff_data(
            catalog,
            sources,
            ["tips"],
        )
        original_csv = context.bundled_files["tips.csv"]
        original_instructions = context.data_instructions
        source._df = source._df.head(1)

        assert context.bundled_files["tips.csv"] == original_csv
        assert context.data_instructions == original_instructions

    def test_materialize_rejects_unknown_tables_before_export(self):
        source = RecordingDataFrameSource("tips")
        sources = {"tips": source}
        catalog = handoff_data.prepare_handoff_data(sources, language="python")

        with pytest.raises(handoff_data.HandoffDataError, match="unknown"):
            handoff_data.materialize_handoff_data(
                catalog,
                sources,
                ["missing"],
            )

        assert source.get_data_calls == 0

    def test_materialize_rejects_export_failures(self):
        source = RecordingDataFrameSource("tips")
        source.export_error = RuntimeError("cannot export")
        sources = {"tips": source}
        catalog = handoff_data.prepare_handoff_data(sources, language="python")

        with pytest.raises(handoff_data.HandoffDataError, match="could not export"):
            handoff_data.materialize_handoff_data(
                catalog,
                sources,
                ["tips"],
            )

        assert source.get_data_calls == 1

    def test_materialize_externalizes_all_dataframes_when_one_exceeds_limit(
        self,
        monkeypatch,
    ):
        source = RecordingDataFrameSource("tips")
        sources = {"tips": source}
        catalog = handoff_data.prepare_handoff_data(sources, language="python")
        monkeypatch.setattr("querychat._handoff_data.MAX_BUNDLE_SIZE", 1)

        context = handoff_data.materialize_handoff_data(
            catalog,
            sources,
            ["tips"],
        )

        assert context.bundled_files == {}
        assert context.bundled_tables == []
        assert context.externalized_dataframe_tables == ["tips"]
        assert "DATA SETUP" in context.data_instructions
        assert "may need adjustment" in context.data_instructions

    def test_materialize_externalizes_all_dataframes_when_combined_bundle_exceeds_limit(
        self,
        monkeypatch,
    ):
        sources = {
            "tips": RecordingDataFrameSource("tips"),
            "tips_copy": RecordingDataFrameSource("tips_copy"),
        }
        catalog = handoff_data.prepare_handoff_data(sources, language="python")
        one_table = handoff_data.materialize_handoff_data(
            catalog,
            sources,
            ["tips"],
        )
        monkeypatch.setattr(
            "querychat._handoff_data.MAX_BUNDLE_SIZE",
            len(one_table.bundled_files["tips.csv"]) + 1,
        )

        context = handoff_data.materialize_handoff_data(
            catalog,
            sources,
            ["tips", "tips_copy"],
        )

        assert context.bundled_files == {}
        assert context.bundled_tables == []
        assert context.externalized_dataframe_tables == ["tips", "tips_copy"]
