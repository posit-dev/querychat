from __future__ import annotations

import os
import re
import warnings
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, Literal, Optional

import narwhals.stable.v1 as nw
from great_tables import GT

if TYPE_CHECKING:
    from typing import TypeGuard

    import ibis


def is_ibis_table(obj: Any) -> TypeGuard[ibis.Table]:
    """
    Check if an object is an Ibis Table.

    This is a TypeGuard that narrows the type to ibis.Table when True.
    Returns False if ibis is not installed.

    Parameters
    ----------
    obj
        The object to check

    Returns
    -------
    :
        True if obj is an ibis.Table, False otherwise

    """
    try:
        import ibis

        return isinstance(obj, ibis.Table)
    except ImportError:
        return False


class MISSING_TYPE:  # noqa: N801
    """
    A singleton representing a missing value.
    """


MISSING = MISSING_TYPE()


class UnsafeQueryError(ValueError):
    """Raised when a query contains an unsafe/write operation."""


def check_query(query: str) -> None:
    """
    Check if a SQL query appears to be a non-read-only (write) operation.

    Raises UnsafeQueryError if the query starts with a dangerous keyword.

    Two categories of keywords are checked:

    - Always blocked: DELETE, TRUNCATE, CREATE, DROP, ALTER, GRANT, REVOKE,
      EXEC, EXECUTE, CALL
    - Blocked unless QUERYCHAT_ENABLE_UPDATE_QUERIES=true: INSERT, UPDATE,
      MERGE, REPLACE, UPSERT

    Parameters
    ----------
    query
        The SQL query string to check

    Raises
    ------
    UnsafeQueryError
        If the query starts with a disallowed keyword

    """
    # Normalize: newlines/tabs -> space, collapse multiple spaces, trim, uppercase
    normalized = re.sub(r"[\r\n\t]+", " ", query)
    normalized = re.sub(r" +", " ", normalized)
    normalized = normalized.strip().upper()

    # Always blocked - destructive/schema/admin operations
    always_blocked = [
        "DELETE",
        "TRUNCATE",
        "CREATE",
        "DROP",
        "ALTER",
        "GRANT",
        "REVOKE",
        "EXEC",
        "EXECUTE",
        "CALL",
    ]

    # Blocked unless escape hatch enabled - data modification
    update_keywords = ["INSERT", "UPDATE", "MERGE", "REPLACE", "UPSERT"]

    # Check always-blocked keywords first
    always_pattern = r"^(" + "|".join(always_blocked) + r")\b"
    match = re.match(always_pattern, normalized)
    if match:
        raise UnsafeQueryError(
            f"Query appears to contain a disallowed operation: {match.group(1)}. "
            "Only SELECT queries are allowed."
        )

    # Check update keywords (can be enabled via envvar)
    enable_updates = os.environ.get("QUERYCHAT_ENABLE_UPDATE_QUERIES", "").lower()
    if enable_updates not in ("true", "1", "yes"):
        update_pattern = r"^(" + "|".join(update_keywords) + r")\b"
        match = re.match(update_pattern, normalized)
        if match:
            raise UnsafeQueryError(
                f"Query appears to contain an update operation: {match.group(1)}. "
                "Only SELECT queries are allowed. "
                "Set QUERYCHAT_ENABLE_UPDATE_QUERIES=true to allow update queries."
            )


@contextmanager
def temp_env_vars(env_vars: dict[str, Optional[str]]):
    """
    Temporarily set environment variables and restore them when exiting.

    Parameters
    ----------
    env_vars : Dict[str, str]
        Dictionary of environment variable names to values to set temporarily

    Example
    -------
    with temp_env_vars({"FOO": "bar", "BAZ": "qux"}):
        # FOO and BAZ are set to "bar" and "qux"
        do_something()
    # FOO and BAZ are restored to their original values (or unset if they weren't set)

    """
    original_values: dict[str, Optional[str]] = {}
    for key in env_vars:
        original_values[key] = os.environ.get(key)

    for key, value in env_vars.items():
        if value is None:
            # If value is None, remove the variable
            os.environ.pop(key, None)
        else:
            # Otherwise set the variable to the specified value
            os.environ[key] = value

    try:
        yield
    finally:
        # Restore original values
        for key, original_value in original_values.items():
            if original_value is None:
                # Variable wasn't set originally, so remove it
                os.environ.pop(key, None)
            else:
                # Restore original value
                os.environ[key] = original_value


def get_tool_details_setting() -> Optional[Literal["expanded", "collapsed", "default"]]:
    """
    Get and validate the tool details setting from environment variable.

    Returns
    -------
    Optional[str]
        The validated value of QUERYCHAT_TOOL_DETAILS environment variable
        (one of 'expanded', 'collapsed', or 'default'), or None if not set
        or invalid

    """
    setting = os.environ.get("QUERYCHAT_TOOL_DETAILS")
    if setting is None:
        return None

    setting_lower = setting.lower()
    valid_settings = ("expanded", "collapsed", "default")

    if setting_lower not in valid_settings:
        warnings.warn(
            f"Invalid value for QUERYCHAT_TOOL_DETAILS: {setting!r}. "
            "Must be one of: 'expanded', 'collapsed', or 'default'",
            UserWarning,
            stacklevel=2,
        )
        return None

    return setting_lower


def querychat_tool_starts_open(action: Literal["update", "query", "reset"]) -> bool:
    """
    Determine whether a tool card should be open based on action and setting.

    Parameters
    ----------
    action : str
        The action type ('update', 'query', or 'reset')

    Returns
    -------
    bool
        True if the tool card should be open, False otherwise

    """
    setting = get_tool_details_setting()

    if setting is None:
        return action != "reset"

    if setting == "expanded":
        return True
    elif setting == "collapsed":
        return False
    else:  # setting == "default"
        return action != "reset"


def df_to_html(df, maxrows: int = 5) -> str:
    """
    Convert a DataFrame to a Bootstrap-styled HTML table for display in chat.

    Parameters
    ----------
    df
        The DataFrame to convert (narwhals, native polars/pandas, or ibis.Table)
    maxrows : int, default=5
        Maximum number of rows to display

    Returns
    -------
    str
        HTML string representation of the table

    """
    if is_ibis_table(df):
        df_short = df.limit(maxrows).execute()
        gt_tbl = GT(df_short)
        table_html = gt_tbl.as_raw_html(make_page=False)

        nrow_full = df.count().execute()
        if nrow_full > maxrows:
            table_html += f"\n\n*(Showing {maxrows} of {nrow_full} rows)*\n"

        return table_html

    if not isinstance(df, (nw.DataFrame, nw.LazyFrame)):
        df = nw.from_native(df)

    if isinstance(df, nw.DataFrame):
        df = df.lazy()

    df_short = df.head(maxrows).collect()
    gt_tbl = GT(df_short.to_native())
    table_html = gt_tbl.as_raw_html(make_page=False)

    nrow_full = df.select(nw.len()).collect().item()
    if nrow_full > maxrows:
        table_html += f"\n\n*(Showing {maxrows} of {nrow_full} rows)*\n"

    return table_html
