Execute one or more trusted measures and stage the results in a temporary database.

Pass a JSON array of `{"name": "<measure_name>", "arguments": {<args>}}` objects. Data frame results are registered as tables named after the measure (e.g., measure `revenue_by_region` → table `revenue_by_region`). If the same measure is called more than once, subsequent tables are named `revenue_by_region_2`, `revenue_by_region_3`, etc. Column schemas are returned so you can write the visualization query. Scalar results are returned as values directly.

Use the returned table names and schemas in the next step: `querychat_visualize_measures`.
