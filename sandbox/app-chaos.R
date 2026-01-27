library(shiny)
library(DBI)
library(querychat)

# Database/table parameters
WAREHOUSE <- "DEFAULT_WH"
DATABASE <- "DEMO_CHAOS_DB"
SCHEMA <- "ERP_DUMP"
TABLE_NAME <- "T_DATA_LOG"

# Snowflake account
ACCOUNT <- "duloftf-posit-software-pbc-dev"

# Get greeting from file in same directory
script_dir <- tryCatch(
  dirname(sys.frame(1)$ofile),
  error = function(e) "."
)
if (is.null(script_dir) || script_dir == "") {
  script_dir <- "sandbox"
}
greeting <- paste(readLines(file.path(script_dir, "greeting.md")), collapse = "\n")



conn <- DBI::dbConnect(
  odbc::snowflake(),
  #driver = odbc:::snowflake_default_driver(),
  authenticator = "externalbrowser",
  account = ACCOUNT,
  #warehouse = WAREHOUSE,
  #database = DATABASE,
  #schema = SCHEMA
)

# Print first few rows to verify connection
print(DBI::dbGetQuery(conn, sprintf("SELECT * FROM %s LIMIT 5", TABLE_NAME)))

# Create QueryChat
qc <- QueryChat$new(
  conn,
  table_name = TABLE_NAME,
  greeting = greeting
)

# Run the app
qc$app()
