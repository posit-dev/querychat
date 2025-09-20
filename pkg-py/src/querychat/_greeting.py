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

    Use this function to generate a friendly greeting message using the chat
    client and data source specified in the `querychat_config` object. You can
    pass this greeting to `init()` to set an initial greeting for users for
    faster startup times and lower costs. If you don't provide a greeting in
    `init()`, one will be generated at the start of every new conversation.

    Parameters
    ----------
    querychat_config
        A QueryChatConfig object from `init()`.
    generate
        If `True` and if `querychat_config` does not include a `greeting`, a new
        greeting is generated. If `False`, returns the existing greeting from
        the configuration (if any).
    stream
        If `True`, returns a streaming response suitable for use in a Shiny app
        with `chat_ui.append_message_stream()`. If `False` (default), returns
        the full greeting at once. Only relevant when `generate = True`.
    **kwargs
        Additional arguments passed to the chat client's `chat()` or `stream_async()` method.

    Returns
    -------
    str | None
        - When `generate = False`: Returns the existing greeting as a string or
          `None` if no greeting exists.
        - When `generate = True`: Returns the chat response containing a greeting and
          sample prompts.

    Examples
    --------
    ```python
    import pandas as pd
    from querychat import init, greeting

    # Create config with mtcars dataset
    mtcars = pd.read_csv(
        "https://gist.githubusercontent.com/seankross/a412dfbd88b3db70b74b/raw/5f23f993cd87c283ce766e7ac6b329ee7cc2e1d1/mtcars.csv"
    )
    mtcars_config = init(mtcars, "mtcars")

    # Generate a new greeting
    greeting_text = greeting(mtcars_config)

    # Update the config with the generated greeting
    mtcars_config = init(
        mtcars,
        "mtcars",
        greeting="Hello! I'm here to help you explore and analyze the mtcars...",
    )
    ```

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
