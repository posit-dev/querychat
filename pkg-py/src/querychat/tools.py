from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Callable

import chevron
from chatlas import ContentToolResult, Tool
from shinychat.types import ToolResultDisplay

from ._icons import bs_icon
from ._utils import df_to_html

if TYPE_CHECKING:
    from ._querychat_module import ReactiveString, ReactiveStringOrNone
    from .datasource import DataSource


def _read_prompt_template(filename: str, **kwargs) -> str:
    """Read and interpolate a prompt template file."""
    template_path = Path(__file__).parent / "prompts" / filename
    template = template_path.read_text()
    return chevron.render(template, kwargs)


def _update_dashboard_impl(
    data_source: DataSource,
    current_query: ReactiveString,
    current_title: ReactiveStringOrNone,
) -> Callable[[str, str], ContentToolResult]:
    """Create the implementation function for updating the dashboard."""

    def update_dashboard(query: str, title: str) -> ContentToolResult:
        error = None
        markdown = f"```sql\n{query}\n```"
        value = "Dashboard updated. Use `query` tool to review results, if needed."

        try:
            # Test the query but don't execute it yet
            data_source.execute_query(query)

            # Add Apply Filter button
            button_html = f"""<button
                class="btn btn-outline-primary btn-sm float-end mt-3 querychat-update-dashboard-btn"
                data-query="{query}"
                data-title="{title}">
                Apply Filter
            </button>"""

            # Update state on success
            if query is not None:
                current_query.set(query)
            if title is not None:
                current_title.set(title)

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
                    open=True,
                    icon=bs_icon("funnel-fill"),
                ),
            },
        )

    return update_dashboard


def tool_update_dashboard(
    data_source: DataSource,
    current_query: ReactiveString,
    current_title: ReactiveStringOrNone,
) -> Tool:
    """
    Create a tool that modifies the data presented in the dashboard based on the SQL query.

    Parameters
    ----------
    data_source
        The data source to query against
    current_query
        Reactive value for storing the current SQL query
    current_title
        Reactive value for storing the current title

    Returns
    -------
    Tool
        A tool that can be registered with chatlas

    """
    impl = _update_dashboard_impl(data_source, current_query, current_title)

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
    current_query: ReactiveString,
    current_title: ReactiveStringOrNone,
) -> Callable[[], ContentToolResult]:
    """Create the implementation function for resetting the dashboard."""

    def reset_dashboard() -> ContentToolResult:
        # Reset current query and title
        current_query.set("")
        current_title.set(None)

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
                    open=False,
                    icon=bs_icon("arrow-counterclockwise"),
                ),
            },
        )

    return reset_dashboard


def tool_reset_dashboard(
    current_query: ReactiveString,
    current_title: ReactiveStringOrNone,
) -> Tool:
    """
    Create a tool that resets the dashboard to show all data.

    Parameters
    ----------
    current_query
        Reactive value for storing the current SQL query
    current_title
        Reactive value for storing the current title

    Returns
    -------
    Tool
        A tool that can be registered with chatlas

    """
    impl = _reset_dashboard_impl(current_query, current_title)

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
            value = result_df.to_dict(orient="records")

            # Format table results
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
                    open=True,
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
