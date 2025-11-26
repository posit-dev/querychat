
from pathlib import Path
from seaborn import load_dataset
from querychat import QueryChat

titanic = load_dataset("titanic")

greeting = Path(__file__).parent / "greeting.md"
data_desc = Path(__file__).parent / "data_description.md"

qc = QueryChat(
    titanic,
    "titanic",
    greeting=greeting,
    data_description=data_desc,
)

qc.app()
