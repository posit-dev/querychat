import ibis
from pathlib import Path
import querychat

import chaos

with open(Path(__file__).parent / "greeting.md", "r") as f:
    greeting = f.read()

# Establish Ibis connection to Snowflake
conn = ibis.snowflake.from_connection(
    chaos.get_connection(),
    create_object_udfs=False,
)

tbl = conn.table(chaos.TABLE_NAME)
print(tbl.head(5))

qc = querychat.QueryChat(
    tbl,
    table_name=chaos.TABLE_NAME,
    greeting=greeting,
)

app = qc.app()
