# Querychat Query Chaining Example

This example demonstrates how to use query chaining with the `querychat_server$tbl()` output. The app allows you to:

1. Use natural language to query a database through the chat sidebar
2. Chain additional dplyr operations to the query results programmatically

## Key Features

- Uses SQLite database with Titanic dataset
- Demonstrates how to apply additional filters, sorts, and aggregations after a chat query
- Shows how to materialize results with `collect()`

## Understanding Query Chaining

The querychat package supports query chaining through the `tbl()` reactive output from `querychat_server()`. This reactive returns a lazy `dbplyr::tbl()` object that can be further manipulated with dplyr verbs.

For example:

```r
# Start with chat-based query
base_query <- chat$tbl()

# Chain additional operations
results <- base_query %>%
  filter(Age == "Adult") %>%
  group_by(Class, Sex) %>%
  summarize(
    Total = n(),
    Survived = sum(Survived == "Yes"),
    Survival_Rate = round(sum(Survived == "Yes") / n() * 100, 1)
  ) %>%
  collect()
```

## How It Works

1. When a user asks a question in the chat sidebar, querychat generates a SQL query
2. The `querychat_server$tbl()` function returns a lazy dbplyr table based on this query
3. You can chain additional dplyr operations to further refine or transform the data
4. The operations remain lazy until you call `collect()` to execute the query and retrieve results

## Running This Example

To run this example:

1. Make sure you have all dependencies installed:
   - shiny, bslib, querychat, DBI, RSQLite, dplyr, DT, tidyr

2. Run the app with:
   ```r
   shiny::runApp("path/to/chained-query")
   ```

3. Try asking questions in the chat sidebar like:
   - "Show me all passengers"
   - "Show me passengers who survived"
   - "What was the survival rate by class?"

4. Notice how the app shows both the direct query results and additional chained transformations