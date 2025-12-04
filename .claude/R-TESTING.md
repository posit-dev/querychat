# R Testing Guide

## Test Organization

Use testthat 3rd-edition style tests. For tests covering a single behavior, use standard `test_that()` style. For testing classes, methods and functions, use **BDD style** with `describe()` and `it()` blocks.

Test files should be placed in `pkg-r/tests/testthat/`. Test file names should directly match the R source file, e.g. `R/{name}.R` --> `tests/testthat/test-{name}.R`.

### Key BDD Principles

1. **Flat structure**: No nested `describe()` blocks
2. **Group by method/function**: One `describe()` block per method or function being tested
3. **Shared fixtures**: Set up at the top of `describe()` blocks, not inside `it()` blocks, when possible
4. **Self-contained tests**: Each `it()` block should be runnable independently after running the shared setup

### Describe Block Structure

```r
describe("ClassName$method()", {
  # Shared fixtures here
  test_data <- new_test_df()

  it("describes what the method does", {
    # Test implementation
  })
})
```

## Fixture Helpers

Common test fixtures are stored in `pkg-r/tests/testthat/helper-fixtures.R`.

### Usage Pattern

```r
describe("DataSource$execute_query()", {
  # Shared fixture at top
  test_df <- new_test_df()
  df_source <- local_data_frame_source(test_df)

  it("executes basic queries", {
    result <- df_source$execute_query("SELECT * FROM test_table")
    expect_s3_class(result, "data.frame")
  })
})
```

## Cleanup

- Use `withr::defer()` for cleanup when not using local_* helpers
- Use `withr::local_*` functions for temporary state (options, envvars, files)
- The fixture helpers handle cleanup automatically via `withr::defer()`

## Test Descriptions

- `describe()`: Use method/function names like `"ClassName$method()"` or `"function_name()"`
- `it()`: Describe behavior at the right level - what does it do, not how
- Group related assertions in a single `it()` block rather than splitting into many small tests

### Good Examples

```r
describe("querychat_tool_starts_open()", {
  it("uses the tool default when options are unset", {
    withr::local_options(querychat.tool_details = NULL)

    expect_true(querychat_tool_starts_open("query"))
    expect_true(querychat_tool_starts_open("update"))
    expect_false(querychat_tool_starts_open("reset"))
  })
})
```

## Common patterns

### Testing Errors

Prefer snapshot testing around expected errors so that the error message is captured in the snapshot.

```r
# Don't do this
expect_error(foo_will_error())

# Do this
expect_snapshot(error = TRUE, foo_will_error())
```

## Running Tests

```bash
# All tests (from repo root)
make r-check-tests

# Single file (e.g. to test tests/testthat/test-data-source.R)
testthat::test(filter = "data-source", reporter = "check")
```
