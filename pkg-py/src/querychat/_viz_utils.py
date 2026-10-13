"""Shared visualization utilities."""

from __future__ import annotations

import importlib.metadata
import importlib.util

from htmltools import HTMLDependency, tags

from .__version import __version__

MIN_GGSQL_VERSION = (0, 5, 2)


def has_viz_tool(tools: set[str] | None) -> bool:
    """Check if visualize is among the configured tools."""
    return tools is not None and "visualize" in tools


def has_maps_tool(tools: set[str] | None) -> bool:
    """Check if the maps capability is among the configured tools."""
    return tools is not None and "maps" in tools


def has_viz_deps() -> bool:
    """Check whether visualization dependencies (ggsql, altair, shinywidgets, vl-convert-python) are installed."""
    if any(
        importlib.util.find_spec(pkg) is None
        for pkg in ("ggsql", "altair", "shinywidgets", "vl_convert")
    ):
        return False
    return ggsql_version() >= MIN_GGSQL_VERSION


def ggsql_version() -> tuple[int, ...]:
    """Installed ggsql version as a comparable tuple (e.g. ``(0, 5, 2)``)."""
    raw = importlib.metadata.version("ggsql")
    parts: list[int] = []
    for piece in raw.split("."):
        num = ""
        for ch in piece:
            if not ch.isdigit():
                break
            num += ch
        if not num:
            break
        parts.append(int(num))
    return tuple(parts)


PRELOAD_WIDGET_ID = "__querychat_preload_viz__"


def preload_viz_deps_ui():
    """Return a hidden widget output that triggers eager JS dependency loading."""
    from shinywidgets import output_widget

    return tags.div(
        output_widget(PRELOAD_WIDGET_ID),
        viz_preload_dep(),
        class_="querychat-viz-preload",
        hidden="",
        aria_hidden="true",
        # Clip so the full-height widget can't leak scrollable overflow into
        # scrollable ancestors (e.g. a sidebar hosting the chat).
        style="position:absolute; left:-9999px; width:1px; height:1px; overflow:clip;",
    )


def viz_preload_dep() -> HTMLDependency:
    """HTMLDependency for viz preload-specific JS."""
    return HTMLDependency(
        "querychat-viz-preload",
        __version__,
        source={
            "package": "querychat",
            "subdir": "static",
        },
        script=[{"src": "js/viz-preload.js"}],
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
