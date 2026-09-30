## Resubmission

This is a resubmission of an archived package. querychat was archived on
2026-09-27 because R CMD check failed on `r-devel-linux-x86_64-fedora-clang`:
the test suite assumed that duckdb (a package listed in Suggests) was
installed on the checking machine.

The failing tests have been fixed: tests that require a package listed in
`Suggests` now skip when that package isn't installed, rather than erroring
or silently falling back to another engine. No changes were made to runtime
package code.

## R CMD check results

0 errors | 0 warnings | 1 note

* This is a new submission of a previously archived package.

* The CRAN incoming feasibility check flags https://platform.openai.com/
  (linked from README.md) with status 403. The site blocks automated
  requests; the link works in a browser.
