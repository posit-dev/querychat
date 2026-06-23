Visualize measure results using a ggsql query.

Write the ggsql query against the table names returned by `querychat_run_measures`. You may filter rows or join tables in the SQL portion, but avoid aggregating or computing new values — the measures already provide the certified computations. After the chart renders, all ephemeral tables are cleaned up.
