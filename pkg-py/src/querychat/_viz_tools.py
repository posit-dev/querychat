"""Visualization tool definitions for querychat."""

from __future__ import annotations

import base64
import copy
import io
from typing import TYPE_CHECKING, Any, TypedDict
from uuid import uuid4

from chatlas import ContentToolResult, Tool, content_image_url
from htmltools import HTMLDependency, TagList, tags
from shinychat.types import ToolResultDisplay

from shiny import ui

from .__version import __version__
from ._icons import bs_icon
from ._utils import querychat_tool_starts_open, read_prompt_template
from ._viz_altair_widget import AltairWidget, fit_chart_to_container
from ._viz_ggsql import execute_ggsql

if TYPE_CHECKING:
    from collections.abc import Callable

    import altair as alt
    from ipywidgets.widgets.widget import Widget

    from ._datasource import DataSource


class VisualizeQueryData(TypedDict):
    """
    Data passed to visualize_query callback.

    This TypedDict defines the structure of data passed to the
    `tool_visualize_query` callback function when the LLM creates an
    exploratory visualization from a ggsql query.

    Attributes
    ----------
    ggsql
        The full ggsql query string (SQL + VISUALISE).
    title
        A descriptive title for the visualization.
    widget_id
        The unique widget ID used to register the visualization with shinywidgets.

    """

    ggsql: str
    title: str
    widget_id: str


def tool_visualize_query(
    data_source: DataSource,
    update_fn: Callable[[VisualizeQueryData], None],
) -> Tool:
    """
    Create a tool that executes a ggsql query and renders the visualization.

    Parameters
    ----------
    data_source
        The data source to query against
    update_fn
        Callback function to call with VisualizeQueryData when visualization succeeds

    Returns
    -------
    Tool
        A tool that can be registered with chatlas

    """
    impl = visualize_query_impl(data_source, update_fn)
    impl.__doc__ = read_prompt_template(
        "tool-visualize-query.md",
        db_type=data_source.get_db_type(),
    )

    return Tool.from_func(
        impl,
        name="querychat_visualize_query",
        annotations={"title": "Query Visualization"},
    )


class VisualizeQueryResult(ContentToolResult):
    """Tool result that registers an ipywidget and embeds it inline via shinywidgets."""

    def __init__(
        self,
        widget_id: str,
        widget: Widget,
        ggsql_str: str,
        title: str,
        png_bytes: bytes | None = None,
        **kwargs: Any,
    ):
        from shinywidgets import output_widget, register_widget

        register_widget(widget_id, widget)

        title_display = f" with title '{title}'" if title else ""
        text = f"Chart displayed{title_display}."

        if png_bytes is not None:
            png_b64 = base64.b64encode(png_bytes).decode("ascii")
            value = [
                text,
                content_image_url(f"data:image/png;base64,{png_b64}"),
            ]
        else:
            value = text

        footer = build_viz_footer(ggsql_str, title, widget_id)

        widget_html = output_widget(widget_id, fill=True, fillable=True)
        widget_html.add_class("querychat-viz-container")
        widget_html.append(viz_dep())

        extra = {
            "display": ToolResultDisplay(
                html=widget_html,
                title=title or "Query Visualization",
                show_request=False,
                open=querychat_tool_starts_open("visualize_query"),
                full_screen=True,
                icon=bs_icon("graph-up"),
                footer=footer,
            ),
        }

        super().__init__(value=value, model_format="as_is", extra=extra, **kwargs)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def visualize_query_impl(
    data_source: DataSource,
    update_fn: Callable[[VisualizeQueryData], None],
) -> Callable[[str, str], ContentToolResult]:
    """Create the visualize_query implementation function."""
    from ggsql import VegaLiteWriter, validate

    def visualize_query(
        ggsql: str,
        title: str,
    ) -> ContentToolResult:
        """Execute a ggsql query and render the visualization."""
        markdown = f"```sql\n{ggsql}\n```"

        try:
            validated = validate(ggsql)
            if not validated.has_visual():
                # When VISUALISE contains SQL expressions (e.g., CAST()),
                # ggsql silently treats the entire query as plain SQL:
                # valid()=True, has_visual()=False, no errors. This
                # heuristic catches that case so we can guide the LLM.
                # Remove when ggsql reports this as a parse error:
                # https://github.com/posit-dev/ggsql/issues/256
                has_keyword = (
                    "VISUALISE" in ggsql.upper() or "VISUALIZE" in ggsql.upper()
                )
                if has_keyword:
                    raise ValueError(
                        "VISUALISE clause was not recognized. "
                        "VISUALISE and MAPPING accept column names only — "
                        "no SQL expressions, CAST(), or functions. "
                        "Move all data transformations to the SELECT clause, "
                        "then reference the resulting column by name in VISUALISE."
                    )
                raise ValueError(
                    "Query must include a VISUALISE clause. "
                    "Use querychat_query for queries without visualization."
                )

            spec = execute_ggsql(data_source, validated)

            raw_chart = VegaLiteWriter().render_chart(spec)
            altair_widget = AltairWidget(copy.deepcopy(raw_chart))

            try:
                png_bytes = render_chart_to_png(raw_chart)
            except Exception:
                png_bytes = None

            update_fn(
                {"ggsql": ggsql, "title": title, "widget_id": altair_widget.widget_id}
            )

            return VisualizeQueryResult(
                widget_id=altair_widget.widget_id,
                widget=altair_widget.widget,
                ggsql_str=ggsql,
                title=title,
                png_bytes=png_bytes,
            )

        except Exception as e:
            error_msg = str(e)
            markdown += f"\n\n> Error: {error_msg}"
            return ContentToolResult(value=markdown, error=e)

    return visualize_query


PNG_WIDTH = 500
PNG_HEIGHT = 300


def render_chart_to_png(chart: alt.TopLevelMixin) -> bytes:
    """Render an Altair chart to PNG bytes at a fixed size for LLM feedback."""
    import altair as alt

    chart = copy.deepcopy(chart)
    is_compound = isinstance(
        chart,
        (alt.FacetChart, alt.ConcatChart, alt.HConcatChart, alt.VConcatChart),
    )
    if is_compound:
        chart = fit_chart_to_container(chart, PNG_WIDTH, PNG_HEIGHT)
    else:
        chart = chart.properties(width=PNG_WIDTH, height=PNG_HEIGHT)

    buf = io.BytesIO()
    chart.save(buf, format="png", scale_factor=1)
    return buf.getvalue()


def viz_dep() -> HTMLDependency:
    """HTMLDependency for viz-specific CSS and JS assets."""
    return HTMLDependency(
        "querychat-viz",
        __version__,
        source={
            "package": "querychat",
            "subdir": "static",
        },
        stylesheet=[{"href": "css/viz.css"}],
        script=[{"src": "js/viz.js"}],
    )


def build_viz_footer(
    ggsql_str: str,
    title: str,
    widget_id: str,
) -> TagList:
    """Build footer HTML for visualization tool results."""
    footer_id = f"querychat_footer_{uuid4().hex[:8]}"
    query_section_id = f"{footer_id}_query"
    code_editor_id = f"{footer_id}_code"

    # Read-only code editor for query display
    code_editor = ui.input_code_editor(
        id=code_editor_id,
        value=ggsql_str,
        language="ggsql",
        read_only=True,
        line_numbers=False,
        height="auto",
        theme_dark="github-dark",
    )

    # Query section (hidden by default)
    query_section = tags.div(
        {"class": "querychat-query-section", "id": query_section_id},
        code_editor,
    )

    # Footer buttons row
    buttons_row = tags.div(
        {"class": "querychat-footer-buttons"},
        # Left: Show Query toggle
        tags.div(
            {"class": "querychat-footer-left"},
            tags.button(
                {
                    "class": "querychat-show-query-btn",
                    "data-target": query_section_id,
                },
                tags.span({"class": "querychat-query-chevron"}, "\u25b6"),
                tags.span({"class": "querychat-query-label"}, "Show Query"),
            ),
        ),
        # Right: Save dropdown
        tags.div(
            {"class": "querychat-footer-right"},
            tags.div(
                {"class": "querychat-save-dropdown"},
                tags.button(
                    {
                        "class": "querychat-save-btn",
                        "data-widget-id": widget_id,
                    },
                    bs_icon("download", cls="querychat-icon"),
                    "Save",
                    bs_icon("chevron-down", cls="querychat-dropdown-chevron"),
                ),
                tags.div(
                    {"class": "querychat-save-menu"},
                    tags.button(
                        {
                            "class": "querychat-save-png-btn",
                            "data-widget-id": widget_id,
                            "data-title": title,
                        },
                        "Save as PNG",
                    ),
                    tags.button(
                        {
                            "class": "querychat-save-svg-btn",
                            "data-widget-id": widget_id,
                            "data-title": title,
                        },
                        "Save as SVG",
                    ),
                ),
            ),
        ),
    )

    return TagList(buttons_row, query_section)
