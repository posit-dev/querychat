"""Shared visualization utilities."""

from __future__ import annotations


def has_viz_tool(tools: tuple[str, ...] | None) -> bool:
    """Check if visualize_query is among the configured tools."""
    return tools is not None and "visualize_query" in tools


def has_viz_deps() -> bool:
    """Check whether visualization dependencies (ggsql, altair, shinywidgets) are installed."""
    import importlib.util

    return all(
        importlib.util.find_spec(pkg) is not None
        for pkg in ("ggsql", "altair", "shinywidgets")
    )



PRELOAD_WIDGET_ID = "__querychat_preload_viz__"


def preload_viz_deps_ui():
    """Return a hidden widget output that triggers eager JS dependency loading."""
    from htmltools import tags
    from shinywidgets import output_widget
    return tags.div(
        output_widget(PRELOAD_WIDGET_ID),
        style="position:absolute; left:-9999px; width:1px; height:1px;",
        **{"aria-hidden": "true"},
    )


def preload_viz_deps_server() -> None:
    """Register a minimal Altair widget to trigger full JS dependency loading."""
    from shinywidgets import register_widget
    register_widget(PRELOAD_WIDGET_ID, mock_altair_widget())


def mock_altair_widget():
    """Create a minimal Altair JupyterChart suitable for preloading JS dependencies."""
    import altair as alt
    chart = alt.Chart({"values": [{"x": 0}]}).mark_point().encode(x="x:Q")
    return alt.JupyterChart(chart)
