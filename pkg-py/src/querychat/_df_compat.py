"""
DataFrame compatibility: try polars first, fall back to pandas.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import narwhals.stable.v1 as nw

if TYPE_CHECKING:
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
