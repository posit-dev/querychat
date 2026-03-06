from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, TypedDict, runtime_checkable
from uuid import uuid4

import chevron
from chatlas import ContentToolResult, Tool
from shinychat.types import ToolResultDisplay

from ._icons import bs_icon
from ._utils import as_narwhals, df_to_html, querychat_tool_starts_open

if TYPE_CHECKING:
    from collections.abc import Callable

    from htmltools import TagList

    from ._datasource import DataSource


@runtime_checkable
class ReactiveString(Protocol):
    """Protocol for a reactive string value."""

    def set(self, value: str) -> Any: ...


@runtime_checkable
class ReactiveStringOrNone(Protocol):
    """Protocol for a reactive string (or None) value."""

    def set(self, value: str | None) -> Any: ...


class UpdateDashboardData(TypedDict):
    """
    Data passed to update_dashboard callback.

    This TypedDict defines the structure of data passed to the
    `tool_update_dashboard` callback function when the LLM requests an update to
    the dashboard's data based on a SQL query.

    Attributes
    ----------
    query
        The SQL query string to execute for filtering/sorting the dashboard.
    title
        A descriptive title for the query, typically displayed in the UI.

    Examples
    --------
    ```python
    import pandas as pd
    from querychat import QueryChat
    from querychat.types import UpdateDashboardData


    def log_update(data: UpdateDashboardData):
        print(f"Executing: {data['query']}")
        print(f"Title: {data['title']}")


    df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
    qc = QueryChat(df, "my_data")
    client = qc.client(update_dashboard=log_update)
    ```

    """

    query: str
    title: str


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


def _read_prompt_template(filename: str, **kwargs) -> str:
    """Read and interpolate a prompt template file."""
    template_path = Path(__file__).parent / "prompts" / filename
    template = template_path.read_text()
    return chevron.render(template, kwargs)


def _update_dashboard_impl(
    data_source: DataSource,
    update_fn: Callable[[UpdateDashboardData], None],
) -> Callable[[str, str], ContentToolResult]:
    """Create the implementation function for updating the dashboard."""

    def update_dashboard(query: str, title: str) -> ContentToolResult:
        error = None
        markdown = f"```sql\n{query}\n```"
        value = "Dashboard updated. Use `query` tool to review results, if needed."

        try:
            # Test the query but don't execute it yet
            data_source.test_query(query, require_all_columns=True)

            # Add Apply Filter button
            button_html = f"""<button
                class="btn btn-outline-primary btn-sm float-end mt-3 querychat-update-dashboard-btn"
                data-query="{query}"
                data-title="{title}">
                Apply Filter
            </button>"""

            # Call the callback with TypedDict data on success
            update_fn({"query": query, "title": title})

        except Exception as e:
            error = str(e)
            markdown += f"\n\n> Error: {error}"
            return ContentToolResult(value=markdown, error=e)

        # Return ContentToolResult with display metadata
        return ContentToolResult(
            value=value,
            extra={
                "display": ToolResultDisplay(
                    markdown=markdown + f"\n\n{button_html}",
                    title=title,
                    show_request=False,
                    open=querychat_tool_starts_open("update"),
                    icon=bs_icon("funnel-fill"),
                ),
            },
        )

    return update_dashboard


def tool_update_dashboard(
    data_source: DataSource,
    update_fn: Callable[[UpdateDashboardData], None],
) -> Tool:
    """
    Create a tool that modifies the data presented in the dashboard based on the SQL query.

    Parameters
    ----------
    data_source
        The data source to query against
    update_fn
        Callback function to call with UpdateDashboardData when update succeeds

    Returns
    -------
    Tool
        A tool that can be registered with chatlas

    """
    impl = _update_dashboard_impl(data_source, update_fn)

    description = _read_prompt_template(
        "tool-update-dashboard.md",
        db_type=data_source.get_db_type(),
    )
    impl.__doc__ = description

    return Tool.from_func(
        impl,
        name="querychat_update_dashboard",
        annotations={"title": "Update Dashboard"},
    )


def _reset_dashboard_impl(
    reset_fn: Callable[[], None],
) -> Callable[[], ContentToolResult]:
    """Create the implementation function for resetting the dashboard."""

    def reset_dashboard() -> ContentToolResult:
        # Call the callback to reset
        reset_fn()

        # Add Reset Filter button
        button_html = """<button
            class="btn btn-outline-primary btn-sm float-end mt-3 querychat-update-dashboard-btn"
            data-query=""
            data-title="">
            Reset Filter
        </button>"""

        # Return ContentToolResult with display metadata
        return ContentToolResult(
            value="The dashboard has been reset to show all data.",
            extra={
                "display": ToolResultDisplay(
                    markdown=button_html,
                    title=None,
                    show_request=False,
                    open=querychat_tool_starts_open("reset"),
                    icon=bs_icon("arrow-counterclockwise"),
                ),
            },
        )

    return reset_dashboard


def tool_reset_dashboard(
    reset_fn: Callable[[], None],
) -> Tool:
    """
    Create a tool that resets the dashboard to show all data.

    Parameters
    ----------
    reset_fn
        Callback function to call when reset is invoked

    Returns
    -------
    Tool
        A tool that can be registered with chatlas

    """
    impl = _reset_dashboard_impl(reset_fn)

    description = _read_prompt_template("tool-reset-dashboard.md")
    impl.__doc__ = description

    return Tool.from_func(
        impl,
        name="querychat_reset_dashboard",
        annotations={"title": "Reset Dashboard"},
    )


def _query_impl(data_source: DataSource) -> Callable[[str, str], ContentToolResult]:
    """Create the implementation function for querying data."""

    def query(query: str, _intent: str = "") -> ContentToolResult:
        error = None
        markdown = f"```sql\n{query}\n```"
        value = None

        try:
            result_df = data_source.execute_query(query)
            nw_df = as_narwhals(result_df)
            value = nw_df.rows(named=True)

            tbl_html = df_to_html(result_df, maxrows=5)
            markdown += "\n\n" + str(tbl_html)

        except Exception as e:
            error = str(e)
            markdown += f"\n\n> Error: {error}"
            return ContentToolResult(value=markdown, error=e)

        # Return ContentToolResult with display metadata
        return ContentToolResult(
            value=value,
            extra={
                "display": ToolResultDisplay(
                    markdown=markdown,
                    show_request=False,
                    open=querychat_tool_starts_open("query"),
                    icon=bs_icon("table"),
                ),
            },
        )

    return query


def tool_query(data_source: DataSource) -> Tool:
    """
    Create a tool that performs a SQL query on the data.

    Parameters
    ----------
    data_source
        The data source to query against

    Returns
    -------
    Tool
        A tool that can be registered with chatlas

    """
    impl = _query_impl(data_source)

    description = _read_prompt_template(
        "tool-query.md", db_type=data_source.get_db_type()
    )
    impl.__doc__ = description

    return Tool.from_func(
        impl,
        name="querychat_query",
        annotations={"title": "Query Data"},
    )


def _build_viz_footer(
    ggsql_str: str,
    title: str | None,
    widget_id: str,
) -> TagList:
    """Build footer HTML for visualization tool results."""
    from htmltools import HTMLDependency, Tag, TagList, tags

    from shiny import ui

    footer_id = f"querychat_footer_{uuid4().hex[:8]}"
    query_section_id = f"{footer_id}_query"
    code_editor_id = f"{footer_id}_code"

    # ggsql grammar dependency (extends SQL grammar at runtime)
    ggsql_grammar_dep = HTMLDependency(
        name="querychat-ggsql-grammar",
        version="0.1.0",
        source={"package": "querychat", "subdir": "static/js"},
        script={"src": "ggsql-grammar.js", "type": "module"},
    )

    # Read-only code editor for query display
    code_editor = ui.input_code_editor(
        id=code_editor_id,
        value=ggsql_str,
        language="sql",
        read_only=True,
        line_numbers=False,
        height="auto",
        theme_dark="github-dark",
    )

    # Query section (hidden by default)
    query_section = tags.div(
        {"class": "querychat-query-section", "id": query_section_id},
        code_editor,
        tags.button(
            {"class": "querychat-copy-btn", "data-query": ggsql_str},
            "Copy",
        ),
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
                    tags.svg(
                        {
                            "class": "querychat-icon",
                            "viewBox": "0 0 20 20",
                            "fill": "currentColor",
                            "xmlns": "http://www.w3.org/2000/svg",
                        },
                        Tag(
                            "path",
                            d="M10.75 2.75a.75.75 0 00-1.5 0v8.614L6.295 8.235a.75.75 0 10-1.09 1.03l4.25 4.5a.75.75 0 001.09 0l4.25-4.5a.75.75 0 00-1.09-1.03l-2.955 3.129V2.75z",
                        ),
                        Tag(
                            "path",
                            d="M3.5 12.75a.75.75 0 00-1.5 0v2.5A2.75 2.75 0 004.75 18h10.5A2.75 2.75 0 0018 15.25v-2.5a.75.75 0 00-1.5 0v2.5c0 .69-.56 1.25-1.25 1.25H4.75c-.69 0-1.25-.56-1.25-1.25v-2.5z",
                        ),
                    ),
                    "Save",
                    tags.svg(
                        {
                            "class": "querychat-dropdown-chevron",
                            "viewBox": "0 0 20 20",
                            "fill": "currentColor",
                            "xmlns": "http://www.w3.org/2000/svg",
                        },
                        Tag(
                            "path",
                            clip_rule="evenodd",
                            fill_rule="evenodd",
                            d="M5.22 8.22a.75.75 0 0 1 1.06 0L10 11.94l3.72-3.72a.75.75 0 1 1 1.06 1.06l-4.25 4.25a.75.75 0 0 1-1.06 0L5.22 9.28a.75.75 0 0 1 0-1.06Z",
                        ),
                    ),
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

    return TagList(ggsql_grammar_dep, buttons_row, query_section)


class VisualizeQueryResult(ContentToolResult):
    """Tool result that embeds an Altair chart inline via shinywidgets."""

    def __init__(
        self,
        chart: Any,
        ggsql_str: str,
        title: str | None,
        row_count: int,
        col_count: int,
        **kwargs: Any,
    ):
        from shinywidgets import output_widget, register_widget

        widget_id = f"querychat_viz_{uuid4().hex[:8]}"
        register_widget(widget_id, chart)

        title_display = f" - {title}" if title else ""
        markdown = f"```sql\n{ggsql_str}\n```"
        markdown += f"\n\nVisualization created{title_display}."
        markdown += f"\n\nData: {row_count} rows, {col_count} columns."

        footer = _build_viz_footer(ggsql_str, title, widget_id)

        widget_html = output_widget(widget_id, fill=True, fillable=True)
        widget_html.add_class("querychat-viz-container")

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


def _visualize_query_impl(
    data_source: DataSource,
    update_fn: Callable[[VisualizeQueryData], None],
) -> Callable[[str, str | None], ContentToolResult]:
    """Create the visualize_query implementation function."""
    import ggsql as ggsql_pkg

    from ._ggsql import execute_ggsql, extract_title, spec_to_altair

    def visualize_query(
        ggsql: str,
        title: str | None = None,
    ) -> ContentToolResult:
        """Execute a ggsql query and render the visualization."""
        markdown = f"```sql\n{ggsql}\n```"

        try:
            # Validate and split the query
            validated = ggsql_pkg.validate(ggsql)
            if not validated.has_visual():
                raise ValueError(
                    "Query must include a VISUALISE clause. "
                    "Use querychat_query for queries without visualization."
                )

            # Execute the SQL and render the visualization
            spec = execute_ggsql(data_source, ggsql)
            chart = spec_to_altair(spec)

            if title is None:
                title = extract_title(spec)
            metadata = spec.metadata()
            row_count = metadata["rows"]
            col_count = len(metadata["columns"])

            update_fn(
                {
                    "ggsql": ggsql,
                    "title": title,
                }
            )

            chart = chart.properties(width="container", height="container")

            return VisualizeQueryResult(
                chart=chart,
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
    impl = _visualize_query_impl(data_source, update_fn)
    impl.__doc__ = _read_prompt_template(
        "tool-visualize-query.md",
        db_type=data_source.get_db_type(),
    )

    return Tool.from_func(
        impl,
        name="querychat_visualize_query",
        annotations={"title": "Query Visualization"},
    )
