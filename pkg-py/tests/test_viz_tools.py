"""Tests for visualization tool functions."""

import narwhals.stable.v1 as nw
import polars as pl
import pytest
from querychat._datasource import DataFrameSource
from querychat.tools import (
    VisualizeDashboardData,
    VisualizeQueryData,
    tool_visualize_dashboard,
    tool_visualize_query,
)


@pytest.fixture
def sample_df():
    return pl.DataFrame(
        {
            "x": [1, 2, 3, 4, 5],
            "y": [10, 20, 15, 25, 30],
            "category": ["A", "B", "A", "B", "A"],
        }
    )


@pytest.fixture
def data_source(sample_df):
    nw_df = nw.from_native(sample_df)
    return DataFrameSource(nw_df, "test_data")


def _ggsql_render_works() -> bool:
    """Check if ggsql.render_altair() is functional (build can be broken in some envs)."""
    try:
        import ggsql

        df = pl.DataFrame({"x": [1, 2], "y": [3, 4]})
        result = ggsql.render_altair(df, "VISUALISE x, y DRAW point")
        spec = result.to_dict()
        return "$schema" in spec
    except (ValueError, ImportError):
        return False


ggsql_render_works = pytest.mark.skipif(
    not _ggsql_render_works(),
    reason="ggsql.render_altair() not functional (build environment issue)",
)


class TestToolVisualizeDashboard:
    def test_creates_tool(self, data_source):
        callback_data = {}

        def update_fn(data: VisualizeDashboardData):
            callback_data.update(data)

        tool = tool_visualize_dashboard(data_source, update_fn)
        assert tool.name == "querychat_visualize_dashboard"

    @ggsql_render_works
    def test_tool_renders_visualization(self, data_source):
        callback_data = {}

        def update_fn(data: VisualizeDashboardData):
            callback_data.update(data)

        tool = tool_visualize_dashboard(data_source, update_fn)
        impl = tool.func

        impl(viz_spec="VISUALISE x, y DRAW point", title="Test Scatter")

        assert "spec" in callback_data
        assert "title" in callback_data
        assert callback_data["title"] == "Test Scatter"
        # Chart is now rendered on demand, not stored in callback data
        assert "chart" not in callback_data

    @ggsql_render_works
    def test_tool_extracts_title_from_spec(self, data_source):
        callback_data = {}

        def update_fn(data: VisualizeDashboardData):
            callback_data.update(data)

        tool = tool_visualize_dashboard(data_source, update_fn)
        impl = tool.func

        impl(
            viz_spec="VISUALISE x, y DRAW point LABEL title => 'From Spec'", title=None
        )

        # Title from spec should be used when title param is None
        assert callback_data["title"] == "From Spec"


class TestToolVisualizeQuery:
    def test_creates_tool(self, data_source):
        callback_data = {}

        def update_fn(data: VisualizeQueryData):
            callback_data.update(data)

        tool = tool_visualize_query(data_source, update_fn)
        assert tool.name == "querychat_visualize_query"

    @ggsql_render_works
    def test_tool_executes_sql_and_renders(self, data_source):
        callback_data = {}

        def update_fn(data: VisualizeQueryData):
            callback_data.update(data)

        tool = tool_visualize_query(data_source, update_fn)
        impl = tool.func

        impl(
            ggsql="SELECT x, y FROM test_data WHERE x > 2 VISUALISE x, y DRAW point",
            title="Filtered Scatter",
        )

        assert "ggsql" in callback_data
        assert "title" in callback_data
        assert callback_data["title"] == "Filtered Scatter"
        # Chart is now rendered on demand, not stored in callback data
        assert "chart" not in callback_data

    @ggsql_render_works
    def test_tool_handles_query_without_visualise(self, data_source):
        callback_data = {}

        def update_fn(data: VisualizeQueryData):
            callback_data.update(data)

        tool = tool_visualize_query(data_source, update_fn)
        impl = tool.func

        # Query without VISUALISE should return error result
        result = impl(ggsql="SELECT x, y FROM test_data", title="No Viz")

        # Check that error is returned and callback was not called
        assert result.error is not None
        assert "VISUALISE" in str(result.error)
        assert "chart" not in callback_data
