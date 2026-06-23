# Resolve a tag's render hooks now and return inert HTML plus its html
# dependencies. shinychat bookmarks chat turns with jsonlite::serializeJSON()
# and restores them with unserializeJSON(), which rebuilds any embedded closure
# from deparsed text and drops its environment. A live bslib/htmltools tag (e.g.
# input_code_editor()) carries render hooks that close over package internals,
# so after the round-trip re-rendering fails with "could not find function".
# Freezing here -- while the hooks can still reach those internals -- keeps only
# inert HTML and html_dependency objects, which survive the round-trip.
# See posit-dev/shinychat#261.
freeze_tags <- function(tags) {
  if (is.null(tags) || is.character(tags)) {
    return(tags)
  }
  rendered <- htmltools::renderTags(tags)
  htmltools::tagList(
    htmltools::HTML(rendered$html),
    if (nzchar(rendered$head)) {
      htmltools::tags$head(htmltools::HTML(rendered$head))
    },
    rendered$dependencies
  )
}
