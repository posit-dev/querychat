in_shiny_session <- function() {
  !is.null(shiny::getDefaultReactiveDomain()) # nocov
}
