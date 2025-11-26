library(querychat)
library(palmerpenguins)

# Create a QueryChat object and generate a complete app with $app()
qc <- QueryChat$new(penguins, "penguins")
qc$app()

# That's it! The app includes:
# - A sidebar with the chat interface
# - SQL query display with syntax highlighting
# - Data table showing filtered results
# - Reset button to clear queries
