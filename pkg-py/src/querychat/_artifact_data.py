from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import narwhals as nw

if TYPE_CHECKING:
    from ._datasource import DataSource

MAX_BUNDLE_SIZE = 5 * 1024 * 1024  # 5 MB


@dataclass
class ArtifactDataContext:
    data_instructions: str
    bundled_files: dict[str, bytes] = field(default_factory=dict)


def get_artifact_data_context(data_source: DataSource | None) -> ArtifactDataContext:
    if data_source is None:
        return no_data_context()

    table_name = data_source.table_name
    db_type = data_source.get_db_type()
    csv_bytes = try_export_csv(data_source)

    if csv_bytes is not None and len(csv_bytes) <= MAX_BUNDLE_SIZE:
        return bundled_csv_context(table_name, csv_bytes)
    elif csv_bytes is not None:
        return large_data_context(table_name, db_type)
    else:
        return database_context(table_name, db_type)


def try_export_csv(data_source: DataSource) -> bytes | None:
    from ._datasource import DataFrameSource

    if not isinstance(data_source, DataFrameSource):
        return None

    try:
        native_df = data_source.get_data()
        csv_text = nw.from_native(native_df, eager_only=True).write_csv()
        return csv_text.encode("utf-8") if csv_text is not None else None
    except Exception:
        return None


def bundled_csv_context(table_name: str, csv_bytes: bytes) -> ArtifactDataContext:
    return ArtifactDataContext(
        data_instructions=(
            f'A CSV file named `{table_name}.csv` is bundled alongside this artifact in the download.\n'
            f"Generate code that loads data from this CSV file. For SQL queries, load the CSV into a\n"
            f'DuckDB in-memory database and register it as the "{table_name}" table.\n'
            f"The artifact should be runnable as-is with the bundled CSV in the same directory."
        ),
        bundled_files={f"{table_name}.csv": csv_bytes},
    )


def large_data_context(table_name: str, db_type: str) -> ArtifactDataContext:
    return ArtifactDataContext(
        data_instructions=(
            f'The data comes from a {db_type} in-memory database with a table named "{table_name}".\n'
            f"The dataset is too large to bundle, so the user must provide their own data source.\n\n"
            f"Generate a clearly marked DATA SETUP section at the top of the artifact.\n"
            f"Include a prominent comment like:\n\n"
            f"  # ⚠️ TODO: Update the path below to point to your data file or database\n\n"
            f'Use `duckdb.connect("path/to/your/database.db")` as the placeholder connection.\n'
            f"Make it obvious what the user needs to change before the artifact is runnable."
        ),
    )


def database_context(table_name: str, db_type: str) -> ArtifactDataContext:
    return ArtifactDataContext(
        data_instructions=(
            f'The data comes from a {db_type} database with a table named "{table_name}".\n\n'
            f"Generate a clearly marked DATA SETUP section at the top of the artifact.\n"
            f"Include a prominent comment like:\n\n"
            f"  # ⚠️ TODO: Update the connection string below to point to your {db_type} database\n\n"
            f'For credentials, use environment variables (e.g., `os.environ["DATABASE_URL"]`).\n'
            f"Do not hardcode any passwords or connection strings.\n"
            f"Make it obvious what the user needs to change before the artifact is runnable."
        ),
    )


def no_data_context() -> ArtifactDataContext:
    return ArtifactDataContext(
        data_instructions=(
            "No data source is configured.\n\n"
            "Generate a clearly marked DATA SETUP section at the top of the artifact\n"
            "with a prominent TODO comment showing the user where to configure their data connection."
        ),
    )
