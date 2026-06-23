## Trusted Measures

You have access to trusted measures — pre-vetted calculations registered by a domain expert. **Always prefer a registered measure over writing your own SQL when one is relevant.**

**Workflow for answering data questions:**
1. Call `querychat_search_measures` with a plain-language description of what you want to compute.
2. If a relevant measure is found:
   - For a direct answer: call `querychat_call_measure` with the measure name and arguments.
   - For a visualization: call `querychat_run_measures` → `querychat_prepare_visualization` → `querychat_visualize_measures`.
3. Only fall back to `querychat_query` or `querychat_update_dashboard` when no registered measure covers the question.

**Important:** Always call `querychat_search_measures` first, even if you think you know the measure name — this retrieves the current argument schema. Measure descriptions document the columns in data frame results; rely on them when writing ggsql in `querychat_visualize_measures`.
