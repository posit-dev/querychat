library(testthat)

test_that("app database example loads without errors", {
  skip_if_not_installed("DT")
  skip_if_not_installed("RSQLite")
  skip_if_not_installed("shinytest2")
  
  # Create a simplified test app with mocked ellmer
  test_app_file <- tempfile(fileext = ".R")
  
  test_app_content <- '
library(shiny)
library(bslib)
library(querychat)
library(DBI)
library(RSQLite)

# Mock chat function to avoid LLM API calls
mock_chat_func <- function(system_prompt) {
  list(
    register_tool = function(tool) invisible(NULL),
    stream_async = function(message) {
      "Welcome! This is a mock response for testing."
    }
  )
}

# Create test database
temp_db <- tempfile(fileext = ".db")
conn <- dbConnect(RSQLite::SQLite(), temp_db)
dbWriteTable(conn, "iris", iris, overwrite = TRUE)
dbDisconnect(conn)

# Setup database source
db_conn <- dbConnect(RSQLite::SQLite(), temp_db)
iris_source <- querychat_data_source(db_conn, "iris")

# Configure querychat with mock
querychat_config <- querychat_init(
  data_source = iris_source,
  greeting = "Welcome to the test app!",
  create_chat_func = mock_chat_func
)

ui <- page_sidebar(
  title = "Test Database App",
  sidebar = querychat_sidebar("chat"),
  h2("Data"),
  DT::DTOutput("data_table"),
  h3("SQL Query"),
  verbatimTextOutput("sql_query")
)

server <- function(input, output, session) {
  chat <- querychat_server("chat", querychat_config)
  
  output$data_table <- DT::renderDT({
    data <- chat$df()
    if (inherits(data, "tbl_lazy")) {
      dplyr::collect(data)
    } else {
      data
    }
  }, options = list(pageLength = 5))
  
  output$sql_query <- renderText({
    query <- chat$sql()
    if (query == "") "No filter applied" else query
  })
  
  session$onSessionEnded(function() {
    if (DBI::dbIsValid(db_conn)) {
      DBI::dbDisconnect(db_conn)
    }
    unlink(temp_db)
  })
}

shinyApp(ui = ui, server = server)
'
  
  writeLines(test_app_content, test_app_file)
  
  # Test that the app can be loaded without immediate errors
  expect_no_error({
    # Try to parse and evaluate the app code
    source(test_app_file, local = TRUE)
  })
  
  # Clean up
  unlink(test_app_file)
})

test_that("database reactive functionality works correctly", {
  skip_if_not_installed("RSQLite")
  
  library(DBI)
  library(RSQLite)
  library(dplyr)
  
  # Create test database
  temp_db <- tempfile(fileext = ".db")
  conn <- dbConnect(RSQLite::SQLite(), temp_db)
  dbWriteTable(conn, "iris", iris, overwrite = TRUE)
  dbDisconnect(conn)
  
  # Test database source creation
  db_conn <- dbConnect(RSQLite::SQLite(), temp_db)
  iris_source <- querychat_data_source(db_conn, "iris")
  
  # Mock chat function
  mock_chat_func <- function(system_prompt) {
    list(
      register_tool = function(tool) invisible(NULL),
      stream_async = function(message) "Mock response"
    )
  }
  
  # Test querychat_init with database source
  config <- querychat_init(
    data_source = iris_source,
    greeting = "Test greeting",
    create_chat_func = mock_chat_func
  )
  
  expect_s3_class(config$data_source, "dbi_source")
  expect_s3_class(config$data_source, "querychat_data_source")
  
  # Test that get_lazy_data returns lazy table
  lazy_data <- get_lazy_data(config$data_source)
  expect_s3_class(lazy_data, c("tbl_SQLiteConnection", "tbl_dbi", 
                               "tbl_sql", "tbl_lazy", "tbl"))
  
  # Test that we can chain operations and collect
  result <- lazy_data %>%
    filter(Species == "setosa") %>%
    select(Sepal.Length, Sepal.Width) %>%
    collect()
  
  expect_s3_class(result, "data.frame")
  expect_equal(nrow(result), 50)
  expect_equal(ncol(result), 2)
  expect_true(all(c("Sepal.Length", "Sepal.Width") %in% names(result)))
  
  # Test that original lazy table is still usable
  all_data <- collect(lazy_data)
  expect_equal(nrow(all_data), 150)
  expect_equal(ncol(all_data), 5)
  
  # Clean up
  dbDisconnect(db_conn)
  unlink(temp_db)
})

test_that("app example file exists and is valid R code", {
  app_file <- "../../examples/app-database.R"
  
  # Check file exists
  expect_true(file.exists(app_file))
  
  # Check it contains key components
  app_content <- readLines(app_file)
  app_text <- paste(app_content, collapse = "\n")
  
  expect_true(grepl("library\\(shiny\\)", app_text))
  expect_true(grepl("library\\(querychat\\)", app_text))
  expect_true(grepl("querychat_data_source", app_text))
  expect_true(grepl("querychat_init", app_text))
  expect_true(grepl("querychat_server", app_text))
  expect_true(grepl("shinyApp", app_text))
  
  # Check it parses as valid R code
  expect_no_error(parse(text = app_text))
})