"""Visualization tool definitions for querychat."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypedDict
from uuid import uuid4

from chatlas import ContentToolResult, Tool
from htmltools import HTMLDependency, TagList, tags
from shinychat.types import ToolResultDisplay

from shiny import ui

from .__version import __version__
from ._icons import bs_icon

if TYPE_CHECKING:
    from collections.abc import Callable

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
        A descriptive title for the visualization, or None if not provided.

    """

    ggsql: str
    title: str | None


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
        title: str | None,
        row_count: int,
        col_count: int,
        **kwargs: Any,
    ):
        from shinywidgets import output_widget, register_widget

        register_widget(widget_id, widget)

        title_display = f" - {title}" if title else ""
        markdown = f"```sql\n{ggsql_str}\n```"
        markdown += f"\n\nVisualization created{title_display}."
        markdown += f"\n\nData: {row_count} rows, {col_count} columns."

        footer = build_viz_footer(ggsql_str, title, widget_id)

        widget_html = output_widget(widget_id, fill=True, fillable=True)
        widget_html.add_class("querychat-viz-container")
        widget_html.append(viz_dep())

        extra = {
            "display": ToolResultDisplay(
                html=widget_html,
                title=title or "Query Visualization",
                show_request=False,
                open=True,
                full_screen=True,
                icon=bs_icon("graph-up"),
                footer=footer,
            ),
        }

        super().__init__(value=markdown, extra=extra, **kwargs)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def visualize_query_impl(
    data_source: DataSource,
    update_fn: Callable[[VisualizeQueryData], None],
) -> Callable[[str, str | None], ContentToolResult]:
    """Create the visualize_query implementation function."""
    import ggsql as ggsql_pkg

    from ._viz_altair_widget import AltairWidget
    from ._viz_ggsql import execute_ggsql

    def visualize_query(
        ggsql: str,
        title: str | None = None,
    ) -> ContentToolResult:
        """Execute a ggsql query and render the visualization."""
        markdown = f"```sql\n{ggsql}\n```"

        try:
            validated = ggsql_pkg.validate(ggsql)
            if not validated.has_visual():
                has_keyword = "VISUALISE" in ggsql.upper() or "VISUALIZE" in ggsql.upper()
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

            spec = execute_ggsql(data_source, ggsql)
            altair_widget = AltairWidget.from_ggsql(spec)

            metadata = spec.metadata()
            row_count = metadata["rows"]
            col_count = len(metadata["columns"])

            update_fn({"ggsql": ggsql, "title": title})

            return VisualizeQueryResult(
                widget_id=altair_widget.widget_id,
                widget=altair_widget.widget,
                ggsql_str=ggsql,
                title=title,
                row_count=row_count,
                col_count=col_count,
            )

        except Exception as e:
            error_msg = str(e)
            markdown += f"\n\n> Error: {error_msg}"
            return ContentToolResult(value=markdown, error=e)

    return visualize_query


def read_prompt_template(filename: str, **kwargs: object) -> str:
    """Read and interpolate a prompt template file."""
    from pathlib import Path

    import chevron

    template_path = Path(__file__).parent / "prompts" / filename
    template = template_path.read_text()
    return chevron.render(template, kwargs)


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
    title: str | None,
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
                            "data-title": title or "chart",
                        },
                        "Save as PNG",
                    ),
                    tags.button(
                        {
                            "class": "querychat-save-svg-btn",
                            "data-widget-id": widget_id,
                            "data-title": title or "chart",
                        },
                        "Save as SVG",
                    ),
                ),
            ),
        ),
    )

    return TagList(buttons_row, query_section)
