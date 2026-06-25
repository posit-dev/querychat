# shinychat compatibility helpers

# TODO: remove once shinychat >= 0.5.0 is the minimum (persistent added in 0.4.0.9000)
chat_greeting_persistent <- function(content) {
  if (utils::packageVersion("shinychat") > "0.4.0") {
    shinychat::chat_greeting(content, persistent = TRUE)
  } else {
    shinychat::chat_greeting(content, dismissible = FALSE)
  }
}
