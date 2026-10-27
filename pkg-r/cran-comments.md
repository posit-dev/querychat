## Resubmission

This is a resubmission of an archived package. querychat was archived on
2026-10-22 because R CMD check failed on `r-devel-linux-x86_64-fedora-clang`:
the test suite relied on DuckDB's JSON extension being available, but this
flavor runs with automatic extension loading disabled.

Tests no longer assume that a database engine is available: fixtures skip
when a required package listed in `Suggests` isn't installed, and queries
that read JSON pins now fall back to `pins::pin_read()` when DuckDB's JSON
extension cannot be installed or loaded (native DuckDB JSON reading is
retained when the extension is available). The dark-mode rendering fix in
the Shiny UI is also new in this version.

## R CMD check results

0 errors | 0 warnings | 1 note

* This is a new submission of a previously archived package.

* The CRAN incoming feasibility check flags https://platform.openai.com/
  (linked from README.md) with status 403. The site blocks automated
  requests; the link works in a browser.
