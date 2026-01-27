from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, TypedDict, runtime_checkable

import chevron
from chatlas import ContentToolResult, Tool
from shinychat.types import ToolResultDisplay

from ._icons import bs_icon
from ._utils import as_narwhals, df_to_html, querychat_tool_starts_open

if TYPE_CHECKING:
    from collections.abc import Callable

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


class VisualizeDashboardData(TypedDict):
    """
    Data passed to visualize_dashboard callback.

    This TypedDict defines the structure of data passed to the
    `tool_visualize_dashboard` callback function when the LLM creates a
    persistent visualization for the dashboard.

    Attributes
    ----------
    spec
        The ggsql VISUALISE specification string.
    title
        A descriptive title for the visualization, or None if not provided.

    """

    spec: str
    title: str | None


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


def _visualize_dashboard_impl(
    data_source: DataSource,
    update_fn: Callable[[VisualizeDashboardData], None],
) -> Callable[[str, str | None], ContentToolResult]:
    """Create the visualize_dashboard implementation function."""
    import ggsql

    from ._ggsql import extract_title

    def visualize_dashboard(
        viz_spec: str,
        title: str | None = None,
    ) -> ContentToolResult:
        """Create a dashboard visualization from a VISUALISE spec."""
        markdown = f"```ggsql\n{viz_spec}\n```"

        try:
            # Validate the spec by rendering it (will raise on error)
            df = data_source.get_data()
            ggsql.render_altair(df, viz_spec)

            # Extract title from spec if not provided
            if title is None:
                title = extract_title(viz_spec)

            # Store just the spec - rendering happens on display
            update_fn(
                {
                    "spec": viz_spec,
                    "title": title,
                }
            )

            # Format success message
            title_display = f" - {title}" if title else ""
            markdown += f"\n\nVisualization created{title_display}."

            return ContentToolResult(
                value=markdown,
                extra={
                    "display": ToolResultDisplay(
                        markdown=markdown,
                        title=title or "Filter Visualization",
                        show_request=False,
                        open=querychat_tool_starts_open("visualize_dashboard"),
                        icon=bs_icon("bar-chart-fill"),
                    ),
                },
            )

        except Exception as e:
            error_msg = str(e)
            markdown += f"\n\n> Error: {error_msg}"
            return ContentToolResult(value=markdown, error=e)

    return visualize_dashboard


def tool_visualize_dashboard(
    data_source: DataSource,
    update_fn: Callable[[VisualizeDashboardData], None],
) -> Tool:
    """
    Create a tool that creates a persistent visualization for the dashboard.

    Parameters
    ----------
    data_source
        The data source to visualize
    update_fn
        Callback function to call with VisualizeDashboardData when visualization succeeds

    Returns
    -------
    Tool
        A tool that can be registered with chatlas

    """
    impl = _visualize_dashboard_impl(data_source, update_fn)
    impl.__doc__ = _read_prompt_template("tool-visualize-dashboard.md")

    return Tool.from_func(
        impl,
        name="querychat_visualize_dashboard",
        annotations={"title": "Create Filter Visualization"},
    )


def _visualize_query_impl(
    data_source: DataSource,
    update_fn: Callable[[VisualizeQueryData], None],
) -> Callable[[str, str | None], ContentToolResult]:
    """Create the visualize_query implementation function."""
    import ggsql as ggsql_pkg

    from ._ggsql import extract_title

    def visualize_query(
        ggsql: str,
        title: str | None = None,
    ) -> ContentToolResult:
        """Execute a ggsql query and render the visualization."""
        markdown = f"```sql\n{ggsql}\n```"

        try:
            # Split the query
            sql, viz_spec = ggsql_pkg.split_query(ggsql)

            if not viz_spec:
                raise ValueError(
                    "Query must include a VISUALISE clause. "
                    "Use querychat_query for queries without visualization."
                )

            # Execute the SQL and validate by rendering
            df = data_source.execute_query(sql)
            ggsql_pkg.render_altair(df, viz_spec)

            # Extract title from spec if not provided
            if title is None:
                title = extract_title(viz_spec)

            # Store just the ggsql - rendering happens on display
            update_fn(
                {
                    "ggsql": ggsql,
                    "title": title,
                }
            )

            # Format success message with data summary
            nw_df = as_narwhals(df)
            row_count = len(nw_df)
            col_count = len(nw_df.columns)

            title_display = f" - {title}" if title else ""
            markdown += f"\n\nVisualization created{title_display}."
            markdown += f"\n\nData: {row_count} rows, {col_count} columns."

            return ContentToolResult(
                value=markdown,
                extra={
                    "display": ToolResultDisplay(
                        markdown=markdown,
                        title=title or "Query Visualization",
                        show_request=False,
                        open=querychat_tool_starts_open("visualize_query"),
                        icon=bs_icon("graph-up"),
                    ),
                },
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
