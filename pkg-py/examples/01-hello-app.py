from pathlib import Path

from querychat import QueryChat
from querychat.data import titanic

greeting = Path(__file__).parent / "greeting.md"

qc = QueryChat(titanic(), "titanic", greeting=greeting)
app = qc.app()
