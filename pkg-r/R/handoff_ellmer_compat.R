# Internal ellmer APIs used by the handoff feature.
#
# Neither symbol is exported by ellmer, so they carry no API-stability
# guarantee. No public equivalent exists yet; the dependencies are isolated
# behind these wrappers so an upstream rename or removal breaks in exactly
# one place and is easy to patch.

ellmer_content_json_class <- function() {
  asNamespace("ellmer")[["ContentJson"]]
}

ellmer_turn_contents_expand <- function(turn) {
  asNamespace("ellmer")[["turn_contents_expand"]](turn)
}
