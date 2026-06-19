from __future__ import annotations

import html
import json
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Protocol, TypedDict, runtime_checkable

from chatlas import ContentToolRequest, ContentToolResult, Tool
from htmltools import HTMLDependency, TagList, tags
from pydantic import Field
from shinychat import message_content_chunk
from shinychat.types import ChatMessage, ToolResultDisplay

from .__version import __version__
from ._datasource import ColumnMeta, format_schema
from ._icons import bs_icon
from ._utils import (
    as_narwhals,
    df_to_html,
    querychat_tool_starts_open,
    read_prompt_template,
    truncate_error,
)
from ._viz_tools import tool_visualize

__all__ = [
    "GetSchemaResult",
    "tool_get_schema",
    "tool_query",
    "tool_reset_dashboard",
    "tool_update_dashboard",
    "tool_visualize",
]

if TYPE_CHECKING:
    from ._data_dict import DataDict
    from ._query_executor import QueryExecutor


ResetDashboardCallback = Callable[[str], None]


class GetSchemaResult(ContentToolResult):
    """Tool result that carries schema text and structured column metadata for a single table."""

    table_name: str
    columns: list[ColumnMeta] = Field(default_factory=list)


def _col_to_dict(col: ColumnMeta) -> dict[str, Any]:
    return {
        "name": col.name,
        "sql_type": col.sql_type,
        "units": col.units,
        "description": col.description,
        "min_val": str(col.min_val) if col.min_val is not None else None,
        "max_val": str(col.max_val) if col.max_val is not None else None,
        "categories": col.categories,
        "constraints": col.constraints,
    }


_orig_request_handler = message_content_chunk.dispatch(ContentToolRequest)


@message_content_chunk.register
def _(request: ContentToolRequest) -> ChatMessage:
    if request.name == "querychat_get_schema":
        return ChatMessage(content="")
    return _orig_request_handler(request)


@message_content_chunk.register
def _(message: GetSchemaResult) -> ChatMessage:
    columns_json = json.dumps([_col_to_dict(c) for c in message.columns])
    content = TagList(
        tags.span(
            class_="qc-schema-collector",
            data_table=message.table_name,
            data_schema=str(message.value),
            data_schema_json=columns_json,
            style="display:none",
        ),
        _schema_dep(),
    )
    return ChatMessage(content=content)


def _schema_dep() -> HTMLDependency:
    return HTMLDependency(
        "querychat-schema-display",
        __version__,
        source={"package": "querychat", "subdir": "static"},
        script=[{"src": "js/schema-display.js"}],
    )


def _get_schema_impl(
    data_dicts: list[DataDict],
    executor: QueryExecutor,
    table_names: list[str],
    categorical_threshold: int,
) -> Callable[[str], ContentToolResult]:
    def get_schema(table_name: str) -> ContentToolResult:
        if table_name not in table_names:
            available = ", ".join(table_names)
            error = f"Table '{table_name}' not found. Available: {available}"
            return ContentToolResult(value=error, error=Exception(error))

        dd = next((d for d in data_dicts if table_name in d.tables), None)
        if dd is not None:
            columns = dd.get_table_schema(table_name, executor, categorical_threshold)
        else:
            columns = executor.get_column_details(table_name, categorical_threshold)

        schema_text = format_schema(table_name, columns)
        return GetSchemaResult(value=schema_text, table_name=table_name, columns=columns)

    return get_schema


def tool_get_schema(
    data_dicts: list[DataDict],
    executor: QueryExecutor,
    table_names: list[str],
    categorical_threshold: int,
) -> Tool:
    """
    Create a tool that retrieves full column details for a table.

    Parameters
    ----------
    data_dicts
        Data dictionaries with enriched column metadata. The first dict that
        covers a requested table is used; tables not covered by any dict fall
        back to live statistics from the executor.
    executor
        The query executor to use for schema introspection.
    table_names
        List of valid table names.
    categorical_threshold
        Maximum number of unique values before a text column is treated as
        free-form rather than categorical.

    Returns
    -------
    Tool
        A tool that can be registered with chatlas.

    """
    impl = _get_schema_impl(data_dicts, executor, table_names, categorical_threshold)
    description = read_prompt_template("tool-get-schema.md")
    impl.__doc__ = description
    return Tool.from_func(
        impl,
        name="querychat_get_schema",
        annotations={"title": "Get Schema"},
    )


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


def _update_dashboard_impl(
    executor: QueryExecutor,
    table_names: list[str],
    update_fn: Callable[[UpdateDashboardData], None],
) -> Callable[[str, str, str], ContentToolResult]:
    """Create the implementation function for updating the dashboard."""

    def update_dashboard(table: str, query: str, title: str) -> ContentToolResult:
        error = None
        markdown = f"```sql\n{query}\n```"
        value = "Dashboard updated. Use `query` tool to review results, if needed."

        # Validate table exists
        if table not in table_names:
            available = ", ".join(table_names)
            error = f"Table '{table}' not found. Available: {available}"
            markdown += f"\n\n> Error: {error}"
            return ContentToolResult(value=markdown, error=Exception(error))

        try:
            # Test the query but don't execute it yet
            executor.test_query(query, table_name=table, require_all_columns=True)

            # Add Apply Filter button
            button_html = f"""<button
                class="btn btn-outline-primary btn-sm float-end mt-3 querychat-update-dashboard-btn"
                data-table="{html.escape(table, quote=True)}"
                data-query="{html.escape(query, quote=True)}"
                data-title="{html.escape(title, quote=True)}">
                Apply Filter
            </button>"""

            # Call the callback with TypedDict data on success
            update_fn({"table": table, "query": query, "title": title})

        except Exception as e:
            error = truncate_error(str(e))
            markdown += f"\n\n> Error: {error}"
            return ContentToolResult(value=markdown, error=Exception(error))

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
    executor: QueryExecutor,
    table_names: list[str],
    update_fn: Callable[[UpdateDashboardData], None],
    *,
    multi_table: bool = False,
) -> Tool:
    """
    Create a tool that modifies the data presented in the dashboard.

    Parameters
    ----------
    executor
        The query executor to validate queries against.
    table_names
        List of valid table names for validation.
    update_fn
        Callback function to call with UpdateDashboardData when update succeeds.
    multi_table
        Whether multiple tables are registered.

    Returns
    -------
    Tool
        A tool that can be registered with chatlas.

    """
    impl = _update_dashboard_impl(executor, table_names, update_fn)

    description = read_prompt_template(
        "tool-update-dashboard.md",
        db_type=executor.get_db_type(),
        multi_table=multi_table,
    )
    impl.__doc__ = description

    return Tool.from_func(
        impl,
        name="querychat_update_dashboard",
        annotations={"title": "Update Dashboard"},
    )


def _reset_dashboard_impl(
    reset_fn: ResetDashboardCallback,
    table_names: list[str] | None,
) -> Callable[[str], ContentToolResult]:
    """Create the implementation function for resetting the dashboard."""

    def reset_dashboard(table: str) -> ContentToolResult:
        if table_names is not None and table not in table_names:
            available = ", ".join(table_names)
            error = f"Table '{table}' not found. Available: {available}"
            return ContentToolResult(
                value=error,
                error=Exception(error),
            )

        # Call the callback to reset
        reset_fn(table)

        # Add Reset Filter button
        button_html = f"""<button
            class="btn btn-outline-primary btn-sm float-end mt-3 querychat-update-dashboard-btn"
            data-table="{html.escape(table, quote=True)}"
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
    reset_fn: ResetDashboardCallback,
    table_names: list[str] | None = None,
) -> Tool:
    """
    Create a tool that resets the dashboard to show all data.

    Parameters
    ----------
    reset_fn
        Callback function to call with table name when reset is requested.
    table_names
        Optional list of valid table names for validation.

    Returns
    -------
    Tool
        A tool that can be registered with chatlas.

    """
    impl = _reset_dashboard_impl(reset_fn, table_names)

    description = read_prompt_template("tool-reset-dashboard.md")
    impl.__doc__ = description

    return Tool.from_func(
        impl,
        name="querychat_reset_dashboard",
        annotations={"title": "Reset Dashboard"},
    )


def _query_impl(executor: QueryExecutor) -> Callable[..., ContentToolResult]:
    """Create the implementation function for querying data."""

    def query(
        query: str,
        collapsed: bool | None = None,  # noqa: FBT001 (LLM tool parameter)
        _intent: str = "",
    ) -> ContentToolResult:
        error = None
        markdown = f"```sql\n{query}\n```"
        value = None

        try:
            result_df = executor.execute_query(query)
            nw_df = as_narwhals(result_df)
            value = nw_df.rows(named=True)

            tbl_html = df_to_html(result_df, maxrows=5)
            markdown += "\n\n" + str(tbl_html)

        except Exception as e:
            error = truncate_error(str(e))
            markdown += f"\n\n> Error: {error}"
            return ContentToolResult(value=markdown, error=Exception(error))

        # Return ContentToolResult with display metadata
        return ContentToolResult(
            value=value,
            extra={
                "display": ToolResultDisplay(
                    markdown=markdown,
                    show_request=False,
                    open=(not collapsed)
                    if collapsed is not None
                    else querychat_tool_starts_open("query"),
                    icon=bs_icon("table"),
                ),
            },
        )

    return query


def tool_query(executor: QueryExecutor, *, multi_table: bool = False) -> Tool:
    """
    Create a tool that performs a SQL query on the data.

    Parameters
    ----------
    executor
        The query executor to use for running queries.
    multi_table
        Whether multiple tables are registered. When True, multi-table
        query guidance is included in the tool description.

    Returns
    -------
    Tool
        A tool that can be registered with chatlas.

    """
    impl = _query_impl(executor)

    description = read_prompt_template(
        "tool-query.md",
        db_type=executor.get_db_type(),
        multi_table=multi_table,
    )
    impl.__doc__ = description

    return Tool.from_func(
        impl,
        name="querychat_query",
        annotations={"title": "Query Data"},
    )
