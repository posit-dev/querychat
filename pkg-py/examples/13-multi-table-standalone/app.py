# /// script
# dependencies = [
#     "querychat[polars,viz]",
#     "anthropic",
# ]
# ///
"""Multi-table querychat demo: a synthetic fine-jewelry retailer.

Five related tables -- diamonds, settings, customers, orders, and
order_items -- are registered with a single QueryChat instance so the LLM
can query any one of them or write joins across them (e.g. an "Engagement
Ring" order item joins to both its diamond and its setting).

Data is generated once and cached to ./data/*.parquet; later runs read the
cache instead of regenerating (see generate_data.py).

Usage:
    uv run app.py

Requires ANTHROPIC_API_KEY to be set (change client= below to use a
different provider).
"""

from pathlib import Path

from generate_data import load_tables
from querychat import QueryChat

GREETING = """\
## Brilliant Retail: Jewelry Explorer 💎

Welcome! You're chatting with a synthetic fine-jewelry retailer's data --
**diamonds**, **settings** (ring mountings), **customers**, **orders**, and
**order_items**, all linked together.

**Get started**

<ul>
<li><span class="suggestion">Show me a few example rows from each table</span></li>
<li><span class="suggestion">What's the average price of a round diamond over 1 carat?</span></li>
</ul>

**Explore across tables**

<ul>
<li><span class="suggestion">Which setting style is most often paired with princess-cut diamonds in engagement rings?</span></li>
<li><span class="suggestion">What's the average order value by acquisition channel?</span></li>
<li><span class="suggestion">Show total revenue by month over the last year</span></li>
</ul>
"""

DATA_DESCRIPTION = """\
Brilliant Retail is an online fine-jewelry retailer. This dataset covers its
diamond and setting catalog alongside customer order history.
"""

# Works around a ggsql bug (https://github.com/posit-dev/ggsql/issues/<TBD>):
# a date/timestamp column produced by an expression like DATE_TRUNC(...) fails
# ggsql's `SCALE ... VIA date` coercion unless it's explicitly cast to DATE.
EXTRA_INSTRUCTIONS = """\
When a `querychat_visualize` query buckets a date or timestamp column (e.g.
via DATE_TRUNC), always CAST the resulting expression to DATE in the SQL, for
example:

    SELECT CAST(DATE_TRUNC('month', order_date) AS DATE) AS month, ...

A column left as a raw TIMESTAMP will fail when referenced by
`SCALE ... VIA date` with a "Cannot coerce column ... to date" error.
"""

tables = load_tables(Path(__file__).parent / "data")

qc = QueryChat(
    tables["diamonds"],
    "diamonds",
    greeting=GREETING,
    data_description=DATA_DESCRIPTION,
    data_dict=Path(__file__).parent / "data-dict.yaml",
    extra_instructions=EXTRA_INSTRUCTIONS,
    client="anthropic",
)
qc.add_table(tables["settings"], "settings")
qc.add_table(tables["customers"], "customers")
qc.add_table(tables["orders"], "orders")
qc.add_table(tables["order_items"], "order_items")

app = qc.app()

if __name__ == "__main__":
    app.run()
