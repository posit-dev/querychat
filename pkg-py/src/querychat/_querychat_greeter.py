"""Greeting generation for QueryChat instances."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Literal

from ._querychat_core import GREETING_PROMPT

if TYPE_CHECKING:
    from ._querychat_base import QueryChatBase


class QueryChatGreeter:
    """Controls greeting generation for a QueryChat instance. Access via ``qc.greeter``."""

    def __init__(self, parent: QueryChatBase) -> None:
        self._parent = parent
        self._tables: list[str] = []
        self._prompt: str | Path = Path(__file__).parent / "prompts" / "greeting.md"

    @property
    def tables(self) -> list[str]:
        """Table names whose context to include in the greeting."""
        return self._tables

    @tables.setter
    def tables(self, value: list[str]) -> None:
        self._tables = value

    @property
    def prompt(self) -> str | Path:
        """The greeting template (string or file path)."""
        return self._prompt

    @prompt.setter
    def prompt(self, value: str | Path) -> None:
        self._prompt = value

    def generate(self, *, echo: Literal["none", "output"] = "none") -> str:
        """Generate a greeting using the greeting system prompt."""
        chat = self._parent._build_greeting_client()
        txt = str(chat.chat(GREETING_PROMPT, echo=echo))
        self._parent.greeting = txt
        return txt
