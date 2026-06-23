Transform and name the staged measure results before visualization.

Pass a JSON array of `{"name": "<table_name>", "query": "<SELECT ...>"}` objects. Each query runs against the `_run_*` tables registered by `querychat_run_measures` and creates a named table you can reference in `querychat_visualize_measures`. The `_run_*` staging tables are dropped after this step.

Use this step to combine, pivot, or filter measure results. For a simple case with no reshaping needed, pass `"SELECT * FROM _run_1"`.
