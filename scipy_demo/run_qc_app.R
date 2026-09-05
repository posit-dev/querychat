pkgload::load_all("/Users/cpsievert/github/shinychat/pkg-r", quiet = TRUE)
pkgload::load_all("/Users/cpsievert/github/querychat/pkg-r", quiet = TRUE)
library(palmerpenguins)

qc <- querychat::QueryChat$new(
  penguins,
  table_name = "penguins",
  greeting = "hello"
)
app <- qc$app_obj()
shiny::runApp(app, port = 4011, host = "127.0.0.1", launch.browser = FALSE)
