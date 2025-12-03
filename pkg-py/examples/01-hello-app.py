from querychat import QueryChat
from querychat.data import titanic

qc = QueryChat(titanic(), "titanic")
app = qc.app()
