"""Tests for visualization tool functions."""

import builtins

import narwhals.stable.v1 as nw
import polars as pl
import pytest
from conftest import ggsql_render_works
from querychat._datasource import DataFrameSource
from querychat.tools import (
    VisualizeDashboardData,
    VisualizeQueryData,
    tool_visualize_dashboard,
    tool_visualize_query,
)


class TestVizDependencyCheck:
    def test_missing_ggsql_raises_helpful_error(self, monkeypatch):
        """Requesting viz tools without ggsql installed should fail early."""
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "ggsql":
                raise ImportError("No module named 'ggsql'")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)

        from querychat._querychat_base import check_viz_dependencies

        with pytest.raises(ImportError, match="pip install querychat\\[viz\\]"):
            check_viz_dependencies(("visualize_dashboard",))

    def test_no_error_without_viz_tools(self):
        """Non-viz tool configs should not check for ggsql."""
        from querychat._querychat_base import check_viz_dependencies

        # Should not raise
        check_viz_dependencies(("update", "query"))
        check_viz_dependencies(None)


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
