from querychat import QueryChat
from querychat.data import titanic

titanic = titanic()
qc = QueryChat(titanic, "titanic")
app = qc.app()
