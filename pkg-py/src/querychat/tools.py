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
    table
        The name of the table being filtered.
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
        print(f"Table: {data['table']}")
        print(f"Executing: {data['query']}")
        print(f"Title: {data['title']}")


    df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
    qc = QueryChat(df, "my_data")
    client = qc.client(update_dashboard=log_update)
    ```

    """

    table: str
    query: str
    title: str


def _read_prompt_template(filename: str, **kwargs) -> str:
    """Read and interpolate a prompt template file."""
    template_path = Path(__file__).parent / "prompts" / filename
    template = template_path.read_text()
    return chevron.render(template, kwargs)


def _update_dashboard_impl(
    data_sources: dict[str, DataSource],
    update_fn: Callable[[UpdateDashboardData], None],
) -> Callable[[str, str, str], ContentToolResult]:
    """Create the implementation function for updating the dashboard."""

    def update_dashboard(table: str, query: str, title: str) -> ContentToolResult:
        error = None
        markdown = f"```sql\n{query}\n```"
        value = "Dashboard updated. Use `query` tool to review results, if needed."

        # Validate table exists
        if table not in data_sources:
            available = ", ".join(data_sources.keys())
            error = f"Table '{table}' not found. Available: {available}"
            markdown += f"\n\n> Error: {error}"
            return ContentToolResult(value=markdown, error=Exception(error))

        data_source = data_sources[table]

        try:
            # Test the query but don't execute it yet
            data_source.test_query(query, require_all_columns=True)

            # Add Apply Filter button
            button_html = f"""<button
                class="btn btn-outline-primary btn-sm float-end mt-3 querychat-update-dashboard-btn"
                data-table="{table}"
                data-query="{query}"
                data-title="{title}">
                Apply Filter
            </button>"""

            # Call the callback with TypedDict data on success
            update_fn({"table": table, "query": query, "title": title})

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
    data_sources: dict[str, DataSource],
    update_fn: Callable[[UpdateDashboardData], None],
) -> Tool:
    """
    Create a tool that modifies the data presented in the dashboard.

    Parameters
    ----------
    data_sources
        Dictionary of data sources keyed by table name.
    update_fn
        Callback function to call with UpdateDashboardData when update succeeds.

    Returns
    -------
    Tool
        A tool that can be registered with chatlas.

    """
    impl = _update_dashboard_impl(data_sources, update_fn)

    # Get db_type from first source (all should be same dialect)
    first_source = next(iter(data_sources.values()))
    description = _read_prompt_template(
        "tool-update-dashboard.md",
        db_type=first_source.get_db_type(),
    )
    impl.__doc__ = description

    return Tool.from_func(
        impl,
        name="querychat_update_dashboard",
        annotations={"title": "Update Dashboard"},
    )


def _reset_dashboard_impl(
    reset_fn: Callable[[str], None],
) -> Callable[[str], ContentToolResult]:
    """Create the implementation function for resetting the dashboard."""

    def reset_dashboard(table: str) -> ContentToolResult:
        # Call the callback to reset
        reset_fn(table)

        # Add Reset Filter button
        button_html = f"""<button
            class="btn btn-outline-primary btn-sm float-end mt-3 querychat-update-dashboard-btn"
            data-table="{table}"
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
    reset_fn: Callable[[str], None],
) -> Tool:
    """
    Create a tool that resets the dashboard to show all data.

    Parameters
    ----------
    reset_fn
        Callback function to call with table name when reset is requested.

    Returns
    -------
    Tool
        A tool that can be registered with chatlas.

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


def tool_query(data_sources: dict[str, DataSource]) -> Tool:
    """
    Create a tool that performs a SQL query on the data.

    Parameters
    ----------
    data_sources
        Dictionary of data sources keyed by table name.

    Returns
    -------
    Tool
        A tool that can be registered with chatlas.

    Note
    ----
    For now, this uses the first data source. True multi-table JOIN support
    would require all tables to share a database connection, which is more
    complex and not needed for MVP.

    """
    # Use first source for now - multi-table JOINs will need shared connection
    first_source = next(iter(data_sources.values()))

    impl = _query_impl(first_source)

    description = _read_prompt_template(
        "tool-query.md", db_type=first_source.get_db_type()
    )
    impl.__doc__ = description

    return Tool.from_func(
        impl,
        name="querychat_query",
        annotations={"title": "Query Data"},
    )
