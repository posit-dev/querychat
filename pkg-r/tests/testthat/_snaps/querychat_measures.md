# validate_measures() errors for non-ToolDef elements

    Code
      validate_measures(list("not a tool"))
    Condition
      Error:
      ! Every item in `measures` must be an <ellmer::ToolDef> created by `ellmer::tool()`.

---

    Code
      validate_measures(list(42))
    Condition
      Error:
      ! Every item in `measures` must be an <ellmer::ToolDef> created by `ellmer::tool()`.

# tool_call_measure() errors informatively for unknown measure name

    Code
      tool(name = "unknown_measure", arguments = "{}")
    Condition
      Error in `tool()`:
      ! No measure named "unknown_measure".
      i Registered measures: "my_measure".

