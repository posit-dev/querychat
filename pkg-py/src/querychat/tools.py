from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

from chatlas import ContentToolResult, Tool
from htmltools import HTML
from shinychat.types import ToolResultDisplay

from ._utils import df_to_html

if TYPE_CHECKING:
    from .datasource import DataSource


def _as_tool(**kwargs) -> Callable[[Callable[..., Any]], Tool]:
    def decorator(func: Callable[..., Any]) -> Tool:
        return Tool.from_func(func, **kwargs)

    return decorator


def tool_update_dashboard(
    data_source: DataSource,
    current_query: Callable,
    current_title: Callable,
) -> Tool:
    """
    Create a tool that modifies the data presented in the dashboard based on the SQL query.

    Parameters
    ----------
    data_source : DataSource
        The data source to query against
    current_query : Callable
        Reactive value for storing the current SQL query
    current_title : Callable
        Reactive value for storing the current title

    Returns
    -------
    Callable
        A function that can be registered as a tool with chatlas

    """

    @_as_tool(annotations={"title": "Update Dashboard"})
    def update_dashboard(query: str, title: str) -> ContentToolResult:
        """
        Modify the data presented in the data dashboard, based on the given SQL query,
        and also updates the title.

        Parameters
        ----------
        query : str
            A SQL query; must be a SELECT statement.
        title : str
            A title to display at the top of the data dashboard, summarizing the intent of the SQL query.

        """
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
                current_query(query)
            if title is not None:
                current_title(title)

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
                    icon=HTML(
                        '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-funnel-fill" viewBox="0 0 16 16"><path d="M1.5 1.5A.5.5 0 0 1 2 1h12a.5.5 0 0 1 .5.5v2a.5.5 0 0 1-.128.334L10 8.692V13.5a.5.5 0 0 1-.342.474l-3 1A.5.5 0 0 1 6 14.5V8.692L1.628 3.834A.5.5 0 0 1 1.5 3.5z"/></svg>',
                    ),
                ),
            },
        )

    return update_dashboard


def tool_reset_dashboard(
    current_query: Callable,
    current_title: Callable,
) -> Tool:
    """
    Create a tool that resets the dashboard to show all data.

    Parameters
    ----------
    current_query : Callable
        Reactive value for storing the current SQL query
    current_title : Callable
        Reactive value for storing the current title

    Returns
    -------
    Tool
        A tool that can be registered with chatlas

    """

    @_as_tool(annotations={"title": "Reset Dashboard"})
    def reset_dashboard() -> ContentToolResult:
        """
        Reset the data dashboard to show all data.
        """
        # Reset current query and title
        current_query("")
        current_title(None)

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
                    icon=HTML(
                        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" class="bi bi-arrow-counterclockwise" style="height:1em;width:1em;fill:currentColor;vertical-align:-0.125em;" aria-hidden="true" role="img"><path fill-rule="evenodd" d="M8 3a5 5 0 1 1-4.546 2.914.5.5 0 0 0-.908-.417A6 6 0 1 0 8 2v1z"></path><path d="M8 4.466V.534a.25.25 0 0 0-.41-.192L5.23 2.308a.25.25 0 0 0 0 .384l2.36 1.966A.25.25 0 0 0 8 4.466z"></path></svg>',
                    ),
                ),
            },
        )

    return reset_dashboard


def tool_query(data_source: DataSource) -> Tool:
    """
    Create a tool that performs a SQL query on the data.

    Parameters
    ----------
    data_source : DataSource
        The data source to query against

    Returns
    -------
    Callable
        A function that can be registered as a tool with chatlas

    """

    @_as_tool(annotations={"title": "Query Data"})
    # TODO: Replace title with `_intent` if supported directly by chatlas
    def query(query: str, title: str = "") -> ContentToolResult:
        """
        Perform a SQL query on the data, and return the results as JSON.

        Parameters
        ----------
        query : str
            A SQL query; must be a SELECT statement.
        title : str, optional
            The intent of the query, in brief natural language for user context.

        """
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
                    title=f"Query: {title}" if title else None,
                    show_request=False,
                    open=True,
                    icon=HTML(
                        '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-table" viewBox="0 0 16 16"><path d="M0 2a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2zm15 2h-4v3h4zm0 4h-4v3h4zm0 4h-4v3h3a1 1 0 0 0 1-1zm-5 3v-3H6v3zm-5 0v-3H1v2a1 1 0 0 0 1 1zm-4-4h4V8H1zm0-4h4V4H1zm5-3v3h4V4zm4 4H6v3h4z"/></svg>',
                    ),
                ),
            },
        )

    return query
