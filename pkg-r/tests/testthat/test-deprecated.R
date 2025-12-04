test_that("deprecated functions throw deprecation warnings", {
  lifecycle::expect_defunct(querychat_init())
  lifecycle::expect_defunct(querychat_sidebar())
  lifecycle::expect_defunct(querychat_ui())
  lifecycle::expect_defunct(querychat_server())
  lifecycle::expect_defunct(querychat_greeting())
  lifecycle::expect_defunct(querychat_data_source())
})
