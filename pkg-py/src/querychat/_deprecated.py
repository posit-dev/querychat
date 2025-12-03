from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional, Union

from shiny import Inputs, Outputs, Session, module, ui

if TYPE_CHECKING:
    from pathlib import Path

    import chatlas
    import sqlalchemy
    from narwhals.stable.v1.typing import IntoFrame

    from ._datasource import DataSource


def init(
    data_source: IntoFrame | sqlalchemy.Engine,
    table_name: str,
    *,
    greeting: Optional[str | Path] = None,
    data_description: Optional[str | Path] = None,
    extra_instructions: Optional[str | Path] = None,
    prompt_template: Optional[str | Path] = None,
    system_prompt_override: Optional[str] = None,
    client: Optional[Union[chatlas.Chat, str]] = None,
):
    """
    Initialize querychat with any compliant data source.

    **Deprecated.** Use `QueryChat()` instead.
    """
    raise RuntimeError("init() is deprecated. Use QueryChat() instead.")


@module.ui
def mod_ui(**kwargs) -> ui.TagList:
    """
    Create the UI for the querychat component.

    **Deprecated.** Use `QueryChat.ui()` instead.
    """
    raise RuntimeError("mod_ui() is deprecated. Use QueryChat.ui() instead.")


@module.server
def mod_server(
    input: Inputs,
    output: Outputs,
    session: Session,
    querychat_config: Any,
):
    """
    Initialize the querychat server.

    **Deprecated.** Use `QueryChat.server()` instead.
    """
    raise RuntimeError("mod_server() is deprecated. Use QueryChat.server() instead.")


def sidebar(
    id: str,
    width: int = 400,
    height: str = "100%",
    **kwargs,
) -> ui.Sidebar:
    """
    Create a sidebar containing the querychat UI.

    **Deprecated.** Use `QueryChat.sidebar()` instead.
    """
    raise RuntimeError("sidebar() is deprecated. Use QueryChat.sidebar() instead.")


def system_prompt(
    data_source: DataSource,
    *,
    data_description: Optional[str | Path] = None,
    extra_instructions: Optional[str | Path] = None,
    categorical_threshold: int = 20,
    prompt_template: Optional[str | Path] = None,
) -> str:
    """
    Create a system prompt for the chat model based on a data source's schema
    and optional additional context and instructions.

    **Deprecated.** Use `QueryChat.set_system_prompt()` instead.
    """
    raise RuntimeError(
        "system_prompt() is deprecated. Use QueryChat.set_system_prompt() instead."
    )


def greeting(
    querychat_config,
    *,
    generate: bool = True,
    stream: bool = False,
    **kwargs,
) -> str | None:
    """
    Generate or retrieve a greeting message.

    **Deprecated.** Use `QueryChat.generate_greeting()` instead.
    """
    raise RuntimeError(
        "greeting() is deprecated. Use QueryChat.generate_greeting() instead."
    )
