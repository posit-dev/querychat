from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal, Protocol

import narwhals as nw

from ._datasource import DataFrameSource

if TYPE_CHECKING:
    from collections.abc import Mapping

    from ._handoff_types import HandoffLanguage

MAX_BUNDLE_SIZE = 5 * 1024 * 1024  # 5 MB

DataMode = Literal["dataframe", "database"]


class HandoffDataError(ValueError):
    """Handoff data cannot satisfy the generated source contract."""


class DatabaseTypeSource(Protocol):
    def get_db_type(self) -> str: ...


@dataclass(frozen=True)
class HandoffDataEntry:
    table_name: str
    db_type: str
    mode: DataMode


@dataclass(frozen=True)
class HandoffDataCatalog:
    entries: dict[str, HandoffDataEntry]
    prompt_instructions: str
    language: HandoffLanguage


@dataclass(frozen=True)
class HandoffDataContext:
    data_instructions: str
    bundled_files: dict[str, bytes] = field(default_factory=dict)
    bundled_tables: list[str] = field(default_factory=list)


def prepare_handoff_data(
    data_sources: Mapping[str, DatabaseTypeSource],
    language: HandoffLanguage,
) -> HandoffDataCatalog:
    entries = {
        name: prepare_table_catalog_entry(name, source)
        for name, source in data_sources.items()
    }
    instructions = "\n\n".join(
        render_data_instructions(
            entry,
            bundled=entry.mode == "dataframe",
            language=language,
        )
        for entry in entries.values()
    )
    return HandoffDataCatalog(
        entries=entries,
        prompt_instructions=instructions,
        language=language,
    )


def materialize_handoff_data(
    catalog: HandoffDataCatalog,
    data_sources: Mapping[str, DatabaseTypeSource],
    referenced_tables: list[str],
) -> HandoffDataContext:
    validate_table_names(catalog, referenced_tables)
    unique_tables = list(dict.fromkeys(referenced_tables))
    bundled_files: dict[str, bytes] = {}
    bundled_tables: list[str] = []
    combined_size = 0

    for name in unique_tables:
        entry = catalog.entries[name]
        if entry.mode != "dataframe":
            continue
        source = data_sources.get(name)
        if not isinstance(source, DataFrameSource):
            raise HandoffDataError(f"Handoff dataframe source is unavailable: {name}")
        try:
            csv_bytes = export_csv(source)
        except Exception as error:
            raise HandoffDataError(
                f"Handoff data could not export dataframe table '{name}' as CSV."
            ) from error

        if len(csv_bytes) > MAX_BUNDLE_SIZE:
            raise HandoffDataError(
                f"Handoff CSV for table '{name}' exceeds the 5 MB limit."
            )

        combined_size += len(csv_bytes)
        if combined_size > MAX_BUNDLE_SIZE:
            raise HandoffDataError(
                "The combined handoff CSV bundle exceeds the 5 MB limit."
            )
        bundled_files[f"{name}.csv"] = csv_bytes
        bundled_tables.append(name)

    return build_data_context(
        catalog,
        unique_tables,
        bundled_files,
        bundled_tables,
    )


def prepare_table_catalog_entry(
    table_name: str,
    data_source: DatabaseTypeSource,
) -> HandoffDataEntry:
    db_type = data_source.get_db_type()
    return HandoffDataEntry(
        table_name=table_name,
        db_type=db_type,
        mode="dataframe" if isinstance(data_source, DataFrameSource) else "database",
    )


def export_csv(data_source: DataFrameSource) -> bytes:
    native_df = data_source.get_data()
    csv_text = nw.from_native(native_df, eager_only=True).write_csv()
    if csv_text is None:
        raise HandoffDataError(
            f"CSV export returned no data for table '{data_source.table_name}'."
        )
    return csv_text.encode("utf-8")


def build_data_context(
    catalog: HandoffDataCatalog,
    referenced_tables: list[str],
    bundled_files: dict[str, bytes],
    bundled_tables: list[str],
) -> HandoffDataContext:
    bundled_set = set(bundled_tables)

    instructions = "\n\n".join(
        render_data_instructions(
            catalog.entries[name],
            bundled=name in bundled_set,
            language=catalog.language,
        )
        for name in referenced_tables
    )
    return HandoffDataContext(
        data_instructions=instructions,
        bundled_files=bundled_files,
        bundled_tables=list(bundled_tables),
    )


def validate_table_names(
    catalog: HandoffDataCatalog,
    table_names: list[str],
) -> None:
    missing = [name for name in table_names if name not in catalog.entries]
    if missing:
        raise HandoffDataError(
            "Handoff referenced unknown tables: " + ", ".join(missing)
        )


def render_data_instructions(
    entry: HandoffDataEntry,
    *,
    bundled: bool,
    language: HandoffLanguage,
) -> str:
    if bundled:
        return bundled_csv_instructions(entry.table_name, language)
    if entry.mode == "database":
        return database_instructions(entry.table_name, entry.db_type, language)
    return external_dataframe_instructions(
        entry.table_name,
        entry.db_type,
        language,
    )


def bundled_csv_instructions(
    table_name: str,
    language: HandoffLanguage,
) -> str:
    introduction = (
        f"A CSV file named `{table_name}.csv` is bundled alongside this handoff "
        "in the download.\n"
    )
    if language == "python":
        setup = (
            "Generate Python code that loads this CSV with `duckdb.connect()` "
            "and DuckDB's `read_csv_auto()`, registering it as the "
            f'`"{table_name}"` table.\n'
        )
    else:
        setup = (
            "Generate R code that connects with "
            "`DBI::dbConnect(duckdb::duckdb())`, loads this CSV, and registers "
            f'it as the `"{table_name}"` table with `DBI::dbWriteTable()`.\n'
        )
    return (
        introduction
        + setup
        + "The handoff must run with the bundled CSV in the same directory."
    )


def external_dataframe_instructions(
    table_name: str,
    db_type: str,
    language: HandoffLanguage,
) -> str:
    instructions = (
        f"The data comes from a {db_type} in-memory database with a table named "
        f'"{table_name}".\n'
        "The dataset is not bundled, so the user must provide a data source.\n\n"
        "Generate a clearly marked DATA SETUP section at the top of the handoff.\n"
        "Include a prominent TODO comment for the data file or database path.\n"
    )
    if language == "python":
        instructions += (
            'Use `duckdb.connect("path/to/your/database.db")` as the '
            "placeholder connection.\n"
        )
    else:
        instructions += (
            "Use `DBI::dbConnect(duckdb::duckdb(), "
            'dbdir = "path/to/your/database.duckdb")` as the placeholder '
            "connection.\n"
        )
    return (
        instructions + "Make the required user change clear before the handoff runs."
    )


def database_instructions(
    table_name: str,
    db_type: str,
    language: HandoffLanguage,
) -> str:
    instructions = (
        f"The data comes from a {db_type} database with a table named "
        f'"{table_name}".\n\n'
        "Generate a clearly marked DATA SETUP section at the top of the handoff.\n"
        f"Include a TODO comment for the {db_type} database connection.\n"
    )
    if language == "python":
        instructions += (
            "Use the appropriate Python database client. For credentials, use "
            'environment variables such as `os.environ["DATABASE_URL"]`.\n'
        )
    else:
        instructions += (
            "Use DBI with the appropriate database backend. For credentials, "
            'use environment variables such as `Sys.getenv("DATABASE_URL")`.\n'
        )
    return (
        instructions
        + "Do not hardcode passwords or connection strings.\n"
        + "Make the required user change clear before the handoff runs."
    )
