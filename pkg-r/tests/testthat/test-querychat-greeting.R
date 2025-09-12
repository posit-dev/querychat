test_that("querychat_greeting without an initial greeting", {
  called <- NULL

  expect_warning(
    config <- querychat_init(
      mtcars,
      client = MockChat$new(response = "Hi there!")
    )
  )

  result <- querychat_greeting(config, generate = FALSE)
  expect_null(result)
})

test_that("querychat_greeting handles empty greeting correctly", {
  # Create a basic config
  mock_client <- ellmer::chat_openai(api_key = "boop")
  config <- querychat_init(mtcars, client = mock_client, greeting = "")

  # Test that empty greeting returns NULL when generate = FALSE
  result <- querychat_greeting(config, generate = FALSE)
  expect_null(result)
})

test_that("querychat_greeting returns existing greeting correctly", {
  # Create a config with a greeting
  mock_client <- ellmer::chat_openai(api_key = "boop")
  test_greeting <- "Hello! This is a test greeting."
  config <- querychat_init(
    mtcars,
    greeting = test_greeting,
    client = mock_client
  )

  # Test that existing greeting is returned when generate = FALSE
  result <- querychat_greeting(config, generate = FALSE)
  expect_equal(result, test_greeting)
})

test_that("querychat_greeting validates input type", {
  # Test that non-querychat_config input raises error
  expect_error(
    querychat_greeting("not a config"),
    "`querychat_config` must be a `querychat_config` object."
  )
})
