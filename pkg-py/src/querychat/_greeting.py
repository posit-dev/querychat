from __future__ import annotations

from copy import deepcopy


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
