from __future__ import annotations

import warnings
from copy import deepcopy
from typing import TYPE_CHECKING, Optional, Union

from shiny import Inputs, Outputs, Session, module, ui

from .querychat import (
    QueryChatConfig,
    _init_impl,
    _server_impl,
    _system_prompt_impl,
    _ui_impl,
)

if TYPE_CHECKING:
    from pathlib import Path

    import chatlas
    import sqlalchemy
    from narwhals.stable.v1.typing import IntoFrame

    from .datasource import DataSource


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
) -> QueryChatConfig:
    """
    Initialize querychat with any compliant data source.

    .. deprecated:: 0.3.0
        Use :class:`QueryChat` instead. This function will be removed in
        version 1.0.

    Warning:
    -------
    This function is deprecated and will be removed in querychat 1.0.
    Use ``QueryChat()`` instead.

    """
    warn_deprecated(
        "init() is deprecated and will be removed in querychat 1.0. "
        "Use QueryChat() instead."
    )
    return _init_impl(
        data_source,
        table_name,
        greeting=greeting,
        data_description=data_description,
        extra_instructions=extra_instructions,
        prompt_template=prompt_template,
        system_prompt_override=system_prompt_override,
        client=client,
    )


@module.ui
def mod_ui(**kwargs) -> ui.TagList:
    """
    Create the UI for the querychat component.

    .. deprecated:: 0.3.0
        Use :meth:`QueryChat.ui()` instead. This function will be removed in
        a future release.

    """
    warn_deprecated(
        "ui() is deprecated and will be removed in a future release. "
        "Use QueryChat.ui() instead."
    )
    return _ui_impl(**kwargs)


@module.server
def mod_server(
    input: Inputs,
    output: Outputs,
    session: Session,
    querychat_config: QueryChatConfig,
):
    """
    Initialize the querychat server.

    .. deprecated:: 0.3.0
        Use :meth:`QueryChat.server()` instead. This function will be removed in
        a future release.

    """
    warnings.warn(
        "server() is deprecated and will be removed in a future release. "
        "Use QueryChat.server() instead.",
        FutureWarning,
        stacklevel=2,
    )
    return _server_impl(
        input,
        output,
        session,
        querychat_config,
    )


def sidebar(
    id: str,
    width: int = 400,
    height: str = "100%",
    **kwargs,
) -> ui.Sidebar:
    """
    Create a sidebar containing the querychat UI.

    .. deprecated:: 0.3.0
        Use :meth:`QueryChat.sidebar()` instead. This function will be removed in
        a future release.

    """
    warn_deprecated(
        "sidebar() is deprecated and will be removed in a future release. "
        "Use QueryChat.sidebar() instead."
    )
    return ui.sidebar(
        mod_ui(id),
        width=width,
        height=height,
        class_="querychat-sidebar",
        **kwargs,
    )


def system_prompt(
    data_source: DataSource,
    *,
    data_description: Optional[str | Path] = None,
    extra_instructions: Optional[str | Path] = None,
    categorical_threshold: int = 10,
    prompt_template: Optional[str | Path] = None,
) -> str:
    """
    Create a system prompt for the chat model based on a data source's schema
    and optional additional context and instructions.

    .. deprecated:: 0.3.0
        Use :meth:`QueryChat.set_system_prompt` instead. This function will be
        removed in version 1.0.

    Warning:
    -------
    This function is deprecated and will be removed in querychat 1.0.
    Use ``QueryChat.set_system_prompt()`` instead.

    """
    warnings.warn(
        "system_prompt() is deprecated and will be removed in querychat 1.0. "
        "Use QueryChat.set_system_prompt() instead.",
        FutureWarning,
        stacklevel=2,
    )
    return _system_prompt_impl(
        data_source,
        data_description=data_description,
        extra_instructions=extra_instructions,
        categorical_threshold=categorical_threshold,
        prompt_template=prompt_template,
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
    warn_deprecated(
        "greeting() is deprecated and will be removed in a future release. "
        "Use QueryChat.generate_greeting() instead."
    )

    not_querychat_config = (
        not hasattr(querychat_config, "client")
        and not hasattr(querychat_config, "greeting")
        and not hasattr(querychat_config, "system_prompt")
    )

    if not_querychat_config:
        raise TypeError("`querychat_config` must be a QueryChatConfig object.")

    greeting_text = querychat_config.greeting
    has_greeting = greeting_text is not None and len(greeting_text.strip()) > 0

    if has_greeting:
        return greeting_text

    if not generate:
        return None

    chat = deepcopy(querychat_config.client)
    chat.system_prompt = querychat_config.system_prompt

    prompt = "Please give me a friendly greeting. Include a few sample prompts in a two-level bulleted list."

    if stream:
        return chat.stream_async(prompt, **kwargs)
    else:
        return chat.chat(prompt, **kwargs)


def warn_deprecated(msg: str) -> None:
    warnings.warn(
        msg,
        FutureWarning,
        stacklevel=3,
    )
