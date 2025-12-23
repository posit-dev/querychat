# TblSqlSource$new() / errors with non-tbl_sql input

    Code
      TblSqlSource$new(data.frame(a = 1))
    Condition
      Error in `initialize()`:
      ! `tbl` must be a SQL tibble connected to a database, not a data frame

---

    Code
      TblSqlSource$new(list(a = 1, b = 2))
    Condition
      Error in `initialize()`:
      ! `tbl` must be a SQL tibble connected to a database, not a list

