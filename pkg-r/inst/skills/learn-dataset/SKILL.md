---
name: learn-dataset
description: Explore a single data table together with a data analyst and produce a concise, reusable data description for future querychat sessions. Use when helping an analyst document what their data means — profiling the data, interviewing the analyst for meaning the data can't reveal, and writing it down.
---

# How to learn this dataset with the analyst

Your job is to build an accurate picture of **one table** and capture the parts
that only the analyst knows, then write it down as a reusable description.

The data tells you its *structure*; only the analyst knows its *meaning* — units,
codes, business rules, caveats, and the questions real users will ask. Most of
your value comes from eliciting that meaning, not from re-deriving structure.

## Principles

- **Research before you ask.** Never ask the analyst something a query can
  answer. Profile the data first, then bring concrete findings to the
  conversation.
- **A description you invented is worse than a question you asked.** Never
  silently guess the meaning of an ambiguous, coded, or abbreviated column. If
  the data can't tell you and you're not sure, ask.
- **Offer a hypothesis, not a blank.** Ask one focused thing at a time, and
  attach your best guess: "`amount` looks like it's in whole dollars — is that
  right?" is better than "What is `amount`?". Group questions only when they're
  tightly related.
- **Orient, don't dump.** Summarize what you find in a sentence or two. Don't
  paste large tables or raw profiling output at the analyst.
- **Write as you go.** Draft the description early and edit it in place as you
  learn more, so the analyst can watch it take shape.
- **These phases are a guide, not a script.** Skip ahead when the analyst
  already knows what they want, or when they've asked to drive.

## Phase 1 — Profile the data

You already have the schema (column names, types, and summary statistics) in
your system prompt. Don't re-query what the schema already tells you. Use the
`querychat_query` tool to fill the gaps that matter for understanding the table:

- **Grain** — what does a single row represent? (one order? one customer? one
  daily snapshot?) Check whether the apparent key is actually unique.
- **Size** — total row count.
- **Per-column profile** — for the columns that matter: null/completeness rate,
  number of distinct values (cardinality), value ranges (min/max), and the most
  common values for low-cardinality columns. Prefer a single query with
  conditional aggregation (e.g. `COUNT(*)`, `COUNT(col)`,
  `COUNT(DISTINCT col)`, `COUNT(CASE WHEN ... THEN 1 END)`) over many small
  queries — one table scan is faster and easier to read.
- **Silent defaults / sentinels** — values standing in for "missing" that aren't
  `NULL`: dates like `'1900-01-01'`, numbers like `0` / `-1`, strings like
  `'N/A'`, `'Unknown'`, `''`. These quietly distort aggregates, so look for them.
- **Date / time span** — for any date column, the earliest and latest values and
  any obvious gaps, so you know what period the data covers.
- **Anomalies** — out-of-range numbers, negative values where none should exist,
  unexpected categories.

Summarize the key findings for the analyst in a few tight bullets, then move on.

## Phase 2 — Draft the description

Write the first draft of `.querychat/<table>.md` now, using only what the data
and schema show you. Use the `write` tool to create it. Fill in what
you're confident about; for anything ambiguous, leave a short, explicit open
question (e.g. "_Units of `amount` unconfirmed — dollars?_") rather than a
confident-sounding guess. Those open questions become your interview agenda.

Keep the document tight and reuse-focused — see "Output document" below. Do not
restate the schema; querychat already supplies column names and types to every
future session. Document only what the schema can't convey.

## Phase 3 — Interview the analyst

This is where the real value is. Walk through the open questions one focused
topic at a time, each with your best hypothesis, and edit the document in place
(the `edit` tool) as each answer lands so the analyst sees it captured.

Ask about the things the data cannot tell you:

- **What a row represents and where the data comes from** — confirm the grain and
  the source/collection process if it isn't obvious.
- **Ambiguous, coded, or abbreviated columns** — what do `status` codes
  `A`/`B`/`C` mean? What are the region codes? What is `flag_3`?
- **Units and sentinel values** — currency, scale (dollars vs. cents vs.
  thousands), measurement units; confirm the meaning of any placeholder values
  you found.
- **Business rules and default filters** — which rows should normally be
  excluded (test records, cancelled/refunded, soft-deleted)? What does "active"
  mean here?
- **Trustworthiness** — are any columns deprecated, unreliable, or known to be
  partially populated? Which columns should users trust?
- **Audience and likely questions** — who will use the eventual querychat app,
  and what will they actually ask?

As you go, build a list of **good questions this data can answer**. Propose
candidate questions, and keep only the ones the analyst confirms are both
answerable from this table and genuinely useful — these seed the eventual app.

## Phase 4 — Confirm and hand off

Review the finished document with the analyst and offer to refine any section.
Explain that the file is saved at `.querychat/<table>.md` and that querychat will
automatically fold it into the system prompt whenever this table is used, so the
effort carries forward into the real app.

## Output document

The file you produce **is** the data description that future querychat sessions
will read. Write it for that audience — an LLM that already has the schema and
needs the meaning. Keep it concise. A good structure:

- **Overview** — one short paragraph: what the table is, what one row represents,
  and (if known) where the data comes from and how current it is.
- **Glossary** — domain terms, acronyms, and codes a newcomer wouldn't know.
  Define vocabulary first so the rest of the document reads clearly.
- **Column notes** — only the columns that need explanation: meaning, units,
  coded values, and any per-column caveats. Skip columns whose name and type are
  self-explanatory.
- **Business rules** — default filters and conventions queries should usually
  follow (e.g. "exclude rows where `status = 'test'`").
- **Limitations** — known data-quality issues, gaps, and the kinds of questions
  this table *cannot* answer.
- **Good questions this data can answer** — the analyst-vetted list from Phase 3.

Adapt the sections to the dataset; omit any that don't apply. Better a short,
accurate document than a long, speculative one.
