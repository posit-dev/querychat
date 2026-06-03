import csv
import io

import pytest
from querychat._artifact_data import (
    ArtifactDataContext,
    get_artifact_data_context,
)
from querychat._datasource import DataFrameSource
from querychat.data import tips


@pytest.fixture
def tips_source():
    return DataFrameSource(tips(), "tips")


class TestArtifactDataContext:
    def test_none_data_source(self):
        ctx = get_artifact_data_context(None)
        assert isinstance(ctx, ArtifactDataContext)
        assert ctx.bundled_files == {}
        assert "TODO" in ctx.data_instructions

    def test_dataframe_source_bundles_csv(self, tips_source: DataFrameSource):
        ctx = get_artifact_data_context(tips_source)
        assert "tips.csv" in ctx.bundled_files
        csv_bytes = ctx.bundled_files["tips.csv"]
        assert len(csv_bytes) > 0
        reader = csv.reader(io.StringIO(csv_bytes.decode("utf-8")))
        header = next(reader)
        assert "total_bill" in header

    def test_bundled_instructions_reference_csv(self, tips_source: DataFrameSource):
        ctx = get_artifact_data_context(tips_source)
        assert "tips.csv" in ctx.data_instructions

    def test_bundled_instructions_mention_table_name(self, tips_source: DataFrameSource):
        ctx = get_artifact_data_context(tips_source)
        assert "tips" in ctx.data_instructions

    def test_large_data_not_bundled(self, tips_source: DataFrameSource, monkeypatch):
        monkeypatch.setattr("querychat._artifact_data.MAX_BUNDLE_SIZE", 1)
        ctx = get_artifact_data_context(tips_source)
        assert ctx.bundled_files == {}
        assert "TODO" in ctx.data_instructions

    def test_instructions_mention_db_type(self, tips_source: DataFrameSource, monkeypatch):
        monkeypatch.setattr("querychat._artifact_data.MAX_BUNDLE_SIZE", 1)
        ctx = get_artifact_data_context(tips_source)
        assert "DuckDB" in ctx.data_instructions
