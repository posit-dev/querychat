"""
DataFrame compatibility: try polars first, fall back to pandas.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import narwhals.stable.v1 as nw

if TYPE_CHECKING:
    import duckdb
    from sqlalchemy.engine import Connection
    from sqlalchemy.sql.elements import TextClause

_INSTALL_MSG = "Install one with: pip install polars  OR  pip install pandas"


def read_sql(query: TextClause, conn: Connection) -> nw.DataFrame:
    try:
        import polars as pl  # pyright: ignore[reportMissingImports]

        return nw.from_native(pl.read_database(query, connection=conn))
    except Exception:  # noqa: S110
        # Catches ImportError for polars, and other errors (e.g., missing pyarrow)
        # Intentional fallback to pandas - no logging needed
        pass

    try:
        import pandas as pd  # pyright: ignore[reportMissingImports]

        return nw.from_native(pd.read_sql_query(query, conn))
    except ImportError:
        pass

    raise ImportError(f"SQLAlchemySource requires 'polars' or 'pandas'. {_INSTALL_MSG}")


def read_sql_polars(query: TextClause, conn: Connection):
    """Read SQL query and return native polars DataFrame."""
    import polars as pl

    return pl.read_database(query, connection=conn)


def read_sql_pandas(query: TextClause, conn: Connection):
    """Read SQL query and return native pandas DataFrame."""
    import pandas as pd

    return pd.read_sql_query(query, conn)


def duckdb_result_to_nw(
    result: duckdb.DuckDBPyRelation | duckdb.DuckDBPyConnection,
) -> nw.DataFrame:
    # Check for polars first without consuming the result
    try:
        import polars  # noqa: F401, ICN001  # pyright: ignore[reportMissingImports]

        return nw.from_native(result.pl())
    except ImportError:
        pass
    except Exception:  # noqa: S110
        # Other polars errors (e.g., missing pyarrow) - fall through to pandas
        pass

    try:
        import pandas  # noqa: F401, ICN001  # pyright: ignore[reportMissingImports]

        return nw.from_native(result.df())
    except ImportError:
        pass

    raise ImportError(f"DataFrameSource requires 'polars' or 'pandas'. {_INSTALL_MSG}")


def duckdb_result_to_polars(
    result: duckdb.DuckDBPyRelation | duckdb.DuckDBPyConnection,
):
    """Convert DuckDB result to native polars DataFrame."""
    return result.pl()


def duckdb_result_to_pandas(
    result: duckdb.DuckDBPyRelation | duckdb.DuckDBPyConnection,
):
    """Convert DuckDB result to native pandas DataFrame."""
    return result.df()


def read_csv(path: str) -> nw.DataFrame:
    try:
        import polars as pl  # pyright: ignore[reportMissingImports]

        return nw.from_native(pl.read_csv(path))
    except Exception:  # noqa: S110
        # Catches ImportError for polars, and other errors (e.g., missing pyarrow)
        # Intentional fallback to pandas - no logging needed
        pass

    try:
        import pandas as pd  # pyright: ignore[reportMissingImports]

        return nw.from_native(pd.read_csv(path, compression="gzip"))
    except ImportError:
        pass

    raise ImportError(f"Loading data requires 'polars' or 'pandas'. {_INSTALL_MSG}")
