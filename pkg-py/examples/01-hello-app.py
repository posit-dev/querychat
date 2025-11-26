from seaborn import load_dataset
from querychat import QueryChat

titanic = load_dataset("titanic")
qc = QueryChat(titanic, "titanic")
app = qc.app()
