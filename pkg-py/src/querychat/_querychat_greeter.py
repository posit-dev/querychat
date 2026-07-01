"""Greeting generation for QueryChat instances."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Literal

from ._querychat_core import GREETING_PROMPT

if TYPE_CHECKING:
    from collections.abc import Callable

    import chatlas


class QueryChatGreeter:
    """Controls greeting generation for a QueryChat instance. Access via ``qc.greeter``."""

    def __init__(self, client_factory: Callable[..., chatlas.Chat]) -> None:
        self._client_factory = client_factory
        self._tables: list[str] = []
        self._prompt: str | Path = Path(__file__).parent / "prompts" / "greeting.md"

    @property
    def tables(self) -> list[str]:
        """Table names whose context to include in the greeting."""
        return self._tables

    @tables.setter
    def tables(self, value: list[str]) -> None:
        if isinstance(value, str):
            raise TypeError(
                "greeter.tables must be a list of table names, not a single "
                f"string. Did you mean [{value!r}]?"
            )
        if not isinstance(value, list) or not all(
            isinstance(name, str) for name in value
        ):
            raise TypeError(
                "greeter.tables must be a list of table names, got "
                f"{type(value).__name__}."
            )
        self._tables = value

    @property
    def prompt(self) -> str | Path:
        """The greeting template (string or file path)."""
        return self._prompt

    @prompt.setter
    def prompt(self, value: str | Path) -> None:
        self._prompt = value

    def build_client(self, base: chatlas.Chat | None = None) -> chatlas.Chat:
        """Build a greeting chat client using the injected factory."""
        return self._client_factory(self._tables, self._prompt, base)

    def generate(
        self,
        *,
        echo: Literal["none", "output"] = "none",
        base: chatlas.Chat | None = None,
    ) -> str:
        """Generate a greeting using the greeting system prompt."""
        return str(self.build_client(base).chat(GREETING_PROMPT, echo=echo))

    async def generate_async(self, *, base: chatlas.Chat | None = None):
        """Stream a greeting response from the greeting client."""
        client = self.build_client(base)
        return await client.stream_async(GREETING_PROMPT, echo="none")
