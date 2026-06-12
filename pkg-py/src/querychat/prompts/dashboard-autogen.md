The user just opened their dashboard drawer for the first time. Generate a
first-pass dashboard from what you know: the conversation so far (if any),
the results already produced (listed below), and the data schema.

Guidelines:

- 4 to 7 cards. Lead with 2-3 `value_box` KPIs (h=2), then 1-2 charts
  (h=4), then a table (h=4) and/or a `markdown` takeaways card (h=2).
- Reuse the session's existing results where relevant (their ggsql/SQL is
  listed below) — the user has already shown interest in them.
- With no conversation history, build a sensible overview of the dataset.
- Provide a `layout` for EVERY card on the 12-column grid; don't overlap.
- Card rules are the same as the `querychat_canvas_set_cards` tool: chart →
  `ggsql`, table/value_box → `sql` ({{db_type}} dialect; value_box SQL must
  return exactly one row and one column), markdown → `text`.
- Give the dashboard a short `title` reflecting the data or the user's focus.

Existing session results:

{{session_results}}
