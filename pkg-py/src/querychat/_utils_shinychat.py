from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from shinychat._chat_types import ChatGreeting


def chat_greeting_persistent(content: Any) -> ChatGreeting:
    from importlib.metadata import version

    import shinychat
    from packaging.version import Version

    if Version(version("shinychat")) > Version("0.4.0"):
        return shinychat.chat_greeting(content, persistent=True)
    else:
        return shinychat.chat_greeting(content, dismissible=False)  # pyright: ignore[reportArgumentType]
