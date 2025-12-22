# Greet Users

``` r
library(querychat)
library(palmerpenguins)
```

## Provide a greeting

When the querychat UI first appears, you will usually want it to greet
the user with some basic instructions. By default, these instructions
are auto-generated every time a user arrives. In a production setting
with multiple users/visitors, this approach has some downsides: it’s
slower, uses more API tokens, and produces different results each time.
Instead, you should create a greeting file and pass it when creating
your `QueryChat` object:

``` r
qc <- querychat(
  penguins,
  greeting = "greeting.md"
)
qc$app()  # Launch the app
```

You can provide suggestions to the user by using the
`<span class="suggestion"> </span>` tag:

``` markdown
* **Filter and sort the data:**
  * <span class="suggestion">Show only Adelie penguins</span>
  * <span class="suggestion">Filter to penguins with body mass over 4000g</span>
  * <span class="suggestion">Sort by flipper length from longest to shortest</span>

* **Answer questions about the data:**
  * <span class="suggestion">What is the average bill length by species?</span>
  * <span class="suggestion">How many penguins are in each island?</span>
  * <span class="suggestion">Which species has the largest average body mass?</span>
```

These suggestions appear in the greeting and automatically populate the
chat text box when clicked.

## Generate a greeting

If you need help coming up with a greeting, you can use the
`$generate_greeting()` method:

``` r
library(querychat)

# Create QueryChat object with your dataset
qc <- querychat(penguins)

# Generate a greeting (this calls the LLM)
greeting_text <- qc$generate_greeting(echo = "text")
#> Hello! I'm here to help you explore and analyze the penguins dataset.
#> Here are some example prompts you can try:
#> ...

# Save it for reuse
writeLines(greeting_text, "penguins_greeting.md")
```

This approach generates a greeting once and saves it for reuse, avoiding
the latency and cost of generating it for every user.

``` r
# Then use the saved greeting in your app
querychat_app(
  penguins,
  greeting = "penguins_greeting.md"
)
```
