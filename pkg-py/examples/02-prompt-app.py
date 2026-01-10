
from pathlib import Path
from querychat import QueryChat
from querychat.data import titanic

greeting = Path(__file__).parent / "greeting.md"
data_desc = Path(__file__).parent / "data_description.md"

qc = QueryChat(
    titanic(),
    "titanic",
    greeting=greeting,
    data_description=data_desc,
)

app = qc.app()
