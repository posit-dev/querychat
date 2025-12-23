# TblLazySource$new() / errors with non-tbl_sql input

    Code
      TblLazySource$new(data.frame(a = 1))
    Condition
      Error in `initialize()`:
      ! `tbl` must be a lazy tibble connected to a database, not a data frame

---

    Code
      TblLazySource$new(list(a = 1, b = 2))
    Condition
      Error in `initialize()`:
      ! `tbl` must be a lazy tibble connected to a database, not a list

