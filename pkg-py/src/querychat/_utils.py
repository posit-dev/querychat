from __future__ import annotations

import os
import warnings
from contextlib import contextmanager
from typing import TYPE_CHECKING, Literal, Optional

import narwhals.stable.v1 as nw

if TYPE_CHECKING:
    from narwhals.stable.v1.typing import IntoFrame


class MISSING_TYPE:  # noqa: N801
    """
    A singleton representing a missing value.
    """


MISSING = MISSING_TYPE()


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


def df_to_html(df: IntoFrame, maxrows: int = 5) -> str:
    """
    Convert a DataFrame to an HTML table for display in chat.

    Parameters
    ----------
    df : IntoFrame
        The DataFrame to convert
    maxrows : int, default=5
        Maximum number of rows to display

    Returns
    -------
    str
        HTML string representation of the table

    """
    ndf = nw.from_native(df)

    if isinstance(ndf, (nw.LazyFrame, nw.DataFrame)):
        df_short = ndf.lazy().head(maxrows).collect()
        nrow_full = ndf.lazy().select(nw.len()).collect().item()
    else:
        raise TypeError(
            "Must be able to convert `df` into a Narwhals DataFrame or LazyFrame",
        )

    # Generate HTML table
    table_html = df_short.to_pandas().to_html(
        index=False,
        classes="table table-striped",
    )

    # Add note about truncated rows if needed
    if len(df_short) != nrow_full:
        rows_notice = (
            f"\n\n(Showing only the first {maxrows} rows out of {nrow_full}.)\n"
        )
    else:
        rows_notice = ""

    return table_html + rows_notice
