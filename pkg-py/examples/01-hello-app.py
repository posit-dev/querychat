from querychat import QueryChat
from querychat.data import titanic

qc = QueryChat(titanic(backend="polars"), "titanic")
app = qc.app()
