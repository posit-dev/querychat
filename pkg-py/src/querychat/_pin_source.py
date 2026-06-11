from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

import duckdb

from ._datasource import DataSource, MissingColumnsError, duckdb_get_schema
from ._utils import check_query

if TYPE_CHECKING:
    import pandas as pd

DUCKDB_FILE_TYPES = {"parquet", "csv", "json"}
DUCKDB_READER_FN = {
    "parquet": "read_parquet",
    "csv": "read_csv_auto",
    "json": "read_json_auto",
}


def _sanitize_table_name(name: str) -> str:
    if re.match(r"^[a-zA-Z][a-zA-Z0-9_]*$", name):
        return name
    out = re.sub(r"[^a-zA-Z0-9_]", "_", name)
    if not re.match(r"^[a-zA-Z]", out):
        out = "t_" + out
    out = re.sub(r"_+", "_", out)
    out = out.rstrip("_")
    return out


class PinSource(DataSource["pd.DataFrame"]):
    """DataSource backed by a pin from a pins board."""

    def __init__(
        self,
        board: Any,
        name: str,
        *,
        table_name: str | None = None,
        version: str | None = None,
    ):
        try:
            import pins  # noqa: F401
        except ImportError:
            raise ImportError(
                "The 'pins' package is required to use PinSource. "
                "Install it with: pip install querychat[pins]"
            ) from None

        effective_table_name = _sanitize_table_name(table_name or name)
        self.table_name = effective_table_name

        self._pin_meta_obj = board.pin_meta(name, version=version)
        pin_type = self._pin_meta_obj.type

        conn = duckdb.connect()
        try:
            if pin_type in DUCKDB_FILE_TYPES:
                paths = board.pin_download(name, version=version)
                if len(paths) != 1:
                    raise ValueError(
                        f"Pin '{name}' contains {len(paths)} files, but PinSource "
                        "requires a single-file pin (as created by pin_write())."
                    )
                reader_fn = DUCKDB_READER_FN[pin_type]
                conn.execute(
                    f'CREATE TABLE "{effective_table_name}" AS '
                    f"SELECT * FROM {reader_fn}(?)",
                    [paths[0]],
                )
            else:
                import pandas as pd

                data = board.pin_read(name, version=version)
                if not isinstance(data, pd.DataFrame):
                    raise TypeError(
                        f"Pin '{name}' contains {type(data).__name__}, not a DataFrame. "
                        "PinSource requires the pin to contain a pandas DataFrame."
                    )
                vname = f"__pin_staging_{effective_table_name}"
                conn.register(vname, data)
                conn.execute(
                    f'CREATE TABLE "{effective_table_name}" AS '
                    f'SELECT * FROM "{vname}"'
                )
                conn.unregister(vname)

            conn.execute("""
SET allow_community_extensions = false;
SET allow_unsigned_extensions = false;
SET autoinstall_known_extensions = false;
SET autoload_known_extensions = false;
SET enable_external_access = false;
SET disabled_filesystems = 'LocalFileSystem';
SET lock_configuration = true;
            """)
        except Exception:
            conn.close()
            raise

        self._conn = conn

        # Store column names for validation
        result = self._conn.execute(f'SELECT * FROM "{effective_table_name}" LIMIT 0')
        self._colnames = [desc[0] for desc in result.description]

    def get_db_type(self) -> str:
        return "DuckDB"

    def get_schema(self, *, categorical_threshold: int) -> str:
        return duckdb_get_schema(self._conn, self.table_name, categorical_threshold)

    def execute_query(self, query: str) -> pd.DataFrame:
        check_query(query)
        return self._conn.execute(query).df()

    def test_query(
        self, query: str, *, require_all_columns: bool = False
    ) -> pd.DataFrame:
        check_query(query)
        normalized = query.rstrip().removesuffix(";")
        result = self._conn.execute(
            f"SELECT * FROM ({normalized}) AS subquery LIMIT 1"
        ).df()

        if require_all_columns:
            result_columns = set(result.columns)
            missing = set(self._colnames) - result_columns
            if missing:
                missing_list = ", ".join(f"'{c}'" for c in sorted(missing))
                original_list = ", ".join(f"'{c}'" for c in self._colnames)
                raise MissingColumnsError(
                    f"Query result missing required columns: {missing_list}. "
                    f"The query must return all original table columns. "
                    f"Original columns: {original_list}"
                )

        return result

    def get_data(self) -> pd.DataFrame:
        return self._conn.execute(f'SELECT * FROM "{self.table_name}"').df()

    def cleanup(self) -> None:
        if self._conn:
            self._conn.close()

    @property
    def pin_meta(self) -> Any:
        return self._pin_meta_obj

    def get_data_description(self) -> str:
        meta = self._pin_meta_obj
        parts: list[str] = []
        if getattr(meta, "title", None):
            parts.append(meta.title)
        if getattr(meta, "description", None):
            parts.append(meta.description)
        tags = getattr(meta, "tags", None)
        if tags:
            parts.append(f"Tags: {', '.join(tags)}")
        return "\n\n".join(parts)
