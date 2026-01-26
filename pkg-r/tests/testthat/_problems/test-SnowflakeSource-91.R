# Extracted from test-SnowflakeSource.R:91

# test -------------------------------------------------------------------------
it("can disable semantic view discovery", {
  # This is a mock test - in reality you'd need a Snowflake connection
  # The actual behavior is tested through the discover_semantic_views param
  # which skips the discovery when FALSE

  # The parameter exists and should be accepted by the class
  expect_true(
    "discover_semantic_views" %in%
      formalArgs(
        SnowflakeSource$public_methods$initialize
      )
  )
})
it("inherits from DBISource", {
  expect_true("DBISource" %in% names(SnowflakeSource$get_inherit()))
})
