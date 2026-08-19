You are helping a user select results from their chat session to include in an artifact, and choosing the best output format.

Here are the available results:

{{#items}}
- **{{id}}**: {{title}} ({{kind}})
{{/items}}

Here are the available output formats:

{{#formats}}
- **{{id}}**: {{label}} — {{description}}
{{/formats}}

Select the results that would make the most useful and visually appealing artifact. Consider:
- Which results complement each other
- What would make a coherent layout
- Which results are most informative

Choose the output format that best fits the selected results. For example, visualization-heavy selections work well as Quarto Dashboards, while exploratory query results may suit a notebook format.
