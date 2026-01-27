"""Integration tests for ggsql visualization."""

import narwhals.stable.v1 as nw
import polars as pl
import pytest
from querychat._datasource import DataFrameSource
from querychat._querychat_core import AppState
from querychat.tools import (
    VisualizeDashboardData,
    VisualizeQueryData,
    tool_visualize_dashboard,
    tool_visualize_query,
)


def _ggsql_render_works() -> bool:
    """Check if ggsql.render_altair() is functional."""
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


@pytest.fixture
def sample_df():
    return pl.DataFrame(
        {
            "date": ["2024-01-01", "2024-01-02", "2024-01-03"],
            "revenue": [100, 150, 120],
            "category": ["A", "B", "A"],
        }
    )


@pytest.fixture
def data_source(sample_df):
    nw_df = nw.from_native(sample_df)
    return DataFrameSource(nw_df, "test_data")


class TestVisualizeDashboardIntegration:
    """Integration tests for visualize_dashboard tool."""

    @ggsql_render_works
    def test_creates_vegalite_chart(self, data_source):
        """Test that visualize_dashboard stores spec (chart rendered on demand)."""
        captured = {}

        def update_callback(data: VisualizeDashboardData):
            captured.update(data)

        tool = tool_visualize_dashboard(data_source, update_callback)
        impl = tool.func

        result = impl(
            viz_spec="VISUALISE category AS x, revenue AS y DRAW bar",
            title="Revenue by Category",
        )

        assert result.error is None
        assert "spec" in captured
        assert captured["title"] == "Revenue by Category"
        # Chart is now rendered on demand, not stored
        assert "chart" not in captured

    @ggsql_render_works
    def test_extracts_title_from_spec(self, data_source):
        """Test that title is extracted from LABEL clause when not provided."""
        captured = {}

        def update_callback(data: VisualizeDashboardData):
            captured.update(data)

        tool = tool_visualize_dashboard(data_source, update_callback)
        impl = tool.func

        impl(
            viz_spec="VISUALISE category AS x, revenue AS y DRAW bar LABEL title => 'From Spec Title'",
            title=None,
        )

        assert captured["title"] == "From Spec Title"


class TestVisualizeQueryIntegration:
    """Integration tests for visualize_query tool."""

    @ggsql_render_works
    def test_executes_sql_and_creates_chart(self, data_source):
        """Test that visualize_query stores ggsql (chart rendered on demand)."""
        captured = {}

        def update_callback(data: VisualizeQueryData):
            captured.update(data)

        tool = tool_visualize_query(data_source, update_callback)
        impl = tool.func

        result = impl(
            ggsql="SELECT category, SUM(revenue) as total FROM test_data GROUP BY category VISUALISE category AS x, total AS y DRAW bar",
            title="Total Revenue by Category",
        )

        assert result.error is None
        assert "ggsql" in captured
        assert captured["title"] == "Total Revenue by Category"
        # Chart is now rendered on demand, not stored
        assert "chart" not in captured

    @ggsql_render_works
    def test_handles_filter_in_query(self, data_source):
        """Test that WHERE clause filters data correctly."""
        captured = {}

        def update_callback(data: VisualizeQueryData):
            captured.update(data)

        tool = tool_visualize_query(data_source, update_callback)
        impl = tool.func

        result = impl(
            ggsql="SELECT date, revenue FROM test_data WHERE category = 'A' VISUALISE date AS x, revenue AS y DRAW line",
            title="Category A Revenue",
        )

        assert result.error is None
        # Chart is now rendered on demand, just verify the ggsql was captured
        assert "ggsql" in captured

    def test_returns_error_without_visualise(self, data_source):
        """Test that query without VISUALISE returns error."""
        captured = {}

        def update_callback(data: VisualizeQueryData):
            captured.update(data)

        tool = tool_visualize_query(data_source, update_callback)
        impl = tool.func

        result = impl(ggsql="SELECT * FROM test_data", title="No Viz")

        assert result.error is not None
        assert "VISUALISE" in str(result.error)
        assert "ggsql" not in captured


class TestAppStateVisualizationIntegration:
    """Integration tests for AppState visualization handling."""

    @ggsql_render_works
    def test_state_serialization_includes_viz(self, data_source):
        """Test that to_dict() includes visualization state (specs only)."""
        from unittest.mock import MagicMock

        mock_client = MagicMock()
        mock_client.get_turns.return_value = []

        state = AppState(data_source=data_source, client=mock_client)
        state.update_filter_viz(
            spec="VISUALISE x, y DRAW point",
            title="Test Chart",
        )

        state_dict = state.to_dict()

        assert state_dict["filter_viz_spec"] == "VISUALISE x, y DRAW point"
        assert state_dict["filter_viz_title"] == "Test Chart"
        # Chart is no longer stored, only spec
        assert "filter_viz_chart" not in state_dict

    @ggsql_render_works
    def test_state_deserialization_restores_viz(self, data_source):
        """Test that update_from_dict() restores visualization state (specs only)."""
        from unittest.mock import MagicMock

        mock_client = MagicMock()
        mock_client.get_turns.return_value = []

        state = AppState(data_source=data_source, client=mock_client)

        state_dict = {
            "sql": None,
            "title": None,
            "error": None,
            "turns": [],
            "filter_viz_spec": "VISUALISE a, b DRAW line",
            "filter_viz_title": "Restored Chart",
            "query_viz_ggsql": None,
            "query_viz_title": None,
        }

        state.update_from_dict(state_dict)

        assert state.filter_viz_spec == "VISUALISE a, b DRAW line"
        assert state.filter_viz_title == "Restored Chart"


class TestGgsqlRenderAltair:
    """Tests for ggsql.render_altair() which renders charts on demand."""

    @ggsql_render_works
    def test_render_altair_returns_correct_type(self):
        """Test that ggsql.render_altair returns Altair charts directly."""
        import altair as alt
        import ggsql

        df = pl.DataFrame({"x": [1, 2, 3], "y": [10, 20, 30]})
        chart = ggsql.render_altair(df, "VISUALISE x, y DRAW point")

        # ggsql.render_altair now returns the correct Altair type
        assert isinstance(chart, alt.TopLevelMixin)
        spec = chart.to_dict()
        assert "$schema" in spec
        assert "vega-lite" in spec["$schema"]
