# querychat: Chat with your data in any language

querychat is a multilingual package that allows you to chat with your data using natural language queries. It's available for:

- [R - Shiny](pkg-r/README.md)
- [Python - Shiny for Python](pkg-py/README.md)

## Overview

Imagine typing questions like these directly into your dashboard, and seeing the results in realtime:

* "Show only penguins that are not species Gentoo and have a bill length greater than 50mm."
* "Show only blue states with an incidence rate greater than 100 per 100,000 people."
* "What is the average mpg of cars with 6 cylinders?"

querychat is a drop-in component for Shiny that allows users to query a data frame using natural language. The results are available as a reactive data frame, so they can be easily used from Shiny outputs, reactive expressions, downloads, etc.

| ![Animation of a dashboard being filtered by a chatbot in the sidebar](animation.gif) |
|-|

[Live demo](https://jcheng.shinyapps.io/sidebot/)

**This is not as terrible an idea as you might think!** We need to be very careful when bringing LLMs into data analysis, as we all know that they are prone to hallucinations and other classes of errors. querychat is designed to excel in reliability, transparency, and reproducibility by using this one technique: denying it raw access to the data, and forcing it to write SQL queries instead.

## How it works

### Powered by LLMs

querychat's natural language chat experience is powered by LLMs (like GPT-4o, Claude 3.5 Sonnet, etc.) that support function/tool calling capabilities.

### Powered by SQL

querychat does not have direct access to the raw data; it can _only_ read or filter the data by writing SQL `SELECT` statements. This means we're not sending the raw data to the LLM and asking it to filter or calculate summary statistics directly, as LLMs can be inconsistent at such tasks. Instead, when you ask something like 'how many penguins have bills longer than 40mm?', the LLM writes SQL to answer the question and sees only the result of that SQL query, ensuring the answer is guaranteed to be accurate with your data. This is crucial for ensuring relability, transparency, and reproducibility:

- **Reliability:** Today's LLMs are excellent at writing SQL, but bad at direct calculation.
- **Transparency:** querychat always displays the SQL to the user, so it can be vetted instead of blindly trusted.
- **Reproducibility:** The SQL query can be easily copied and reused.

Currently, querychat uses DuckDB for its SQL engine when working with data frames. For database sources, it uses the native SQL dialect of the connected database.

## Language-specific Documentation

For detailed information on how to use querychat in your preferred language, see the language-specific READMEs:

- [R Documentation](pkg-r/README.md)
- [Python Documentation](pkg-py/README.md)