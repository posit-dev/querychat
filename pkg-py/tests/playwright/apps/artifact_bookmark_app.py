"""Test app for artifact bookmark restore: server-side bookmarking avoids URL length limits."""

from pathlib import Path

from querychat import QueryChat
from querychat.data import titanic
from shinychat.types import HistoryOptions

greeting = Path(__file__).parents[3] / "examples" / "greeting.md"

qc = QueryChat(titanic(), "titanic", greeting=greeting)
app = qc.app(history=HistoryOptions(restore_mode="bookmark"))
