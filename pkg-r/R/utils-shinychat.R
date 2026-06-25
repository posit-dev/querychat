# shinychat compatibility helpers

chat_greeting_persistent <- function(content) {
  if (utils::packageVersion("shinychat") > "0.4.0") {
    shinychat::chat_greeting(content, persistent = TRUE)
  } else {
    shinychat::chat_greeting(content, dismissible = FALSE)
  }
}
