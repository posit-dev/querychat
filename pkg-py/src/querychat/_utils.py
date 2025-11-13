from __future__ import annotations

import os
from contextlib import contextmanager
from typing import TYPE_CHECKING, Optional

import chatlas
import narwhals.stable.v1 as nw

if TYPE_CHECKING:
    from narwhals.stable.v1.typing import IntoFrame


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


def normalize_client(client: Optional[str | chatlas.Chat] = None) -> chatlas.Chat:
    if client is None:
        client = get_client_from_env()

    if client is None:
        # Default to OpenAI with using chatlas's default model
        return chatlas.ChatOpenAI()

    if isinstance(client, str):
        client = create_client_from_string(client)

    if not isinstance(client, chatlas.Chat):
        raise TypeError(
            "client must be a chatlas.Chat object or a string",
        )

    return client


def get_client_from_env() -> Optional[str]:
    """Get client configuration from environment variable."""
    env_client = os.getenv("QUERYCHAT_CLIENT", "")
    if not env_client:
        return None
    return env_client


def create_client_from_string(client_str: str) -> chatlas.Chat:
    """Create a chatlas.Chat client from a provider-model string."""
    provider, model = (
        client_str.split("/", 1) if "/" in client_str else (client_str, None)
    )
    # We unset chatlas's envvars so we can listen to querychat's envvars instead
    with temp_env_vars(
        {
            "CHATLAS_CHAT_PROVIDER": provider,
            "CHATLAS_CHAT_MODEL": model,
            "CHATLAS_CHAT_ARGS": os.environ.get("QUERYCHAT_CLIENT_ARGS"),
        },
    ):
        return chatlas.ChatAuto(provider="openai")
