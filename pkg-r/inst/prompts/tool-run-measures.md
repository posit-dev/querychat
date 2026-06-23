Execute one or more trusted measures and stage the results in a temporary database.

Pass a JSON array of `{"name": "<measure_name>", "arguments": {<args>}}` objects. Data frame results are registered as `_run_1`, `_run_2`, etc. in a temporary database; their column schemas are returned so you can write the visualization query. Scalar results are returned as values directly.

Use the returned table names and schemas in the next step: `querychat_prepare_visualization`.
