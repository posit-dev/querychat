from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from ._datasource import ColumnMeta, format_schema

if TYPE_CHECKING:
    from ._query_executor import QueryExecutor


class ColumnRange(BaseModel):
    """Inclusive numeric range for a column, used instead of live min/max queries."""

    min: Any = None
    max: Any = None


class ColumnSpec(BaseModel):
    """
    Per-column metadata entry in a :class:`DataDict`.

    All fields are optional. Only ``name`` is required, and is used to match
    this spec against columns returned by the data source.

    Parameters
    ----------
    name
        Column name as it appears in the data source.
    type
        Human-readable type override (e.g. ``"date"``, ``"currency"``). When
        supplied, this replaces the inferred SQL type in the LLM schema view.
    constraints
        Free-text constraints conveyed to the LLM (e.g. ``"non-negative"``).
    description
        Short description forwarded verbatim to the LLM's schema view.
    details
        Longer narrative about the column, used only in the on-demand
        ``get_schema`` tool response.
    units
        Unit label (e.g. ``"kg"``, ``"USD"``), included in the schema view.
    values
        Exhaustive list of valid values. Replaces categorical inference for
        this column — querychat will not query the data source for distinct
        values when this is set.
    range
        Inclusive min/max bounds. Replaces live min/max statistics queries
        when set.
    examples
        Representative sample values shown to the LLM as context.

    """

    name: str
    type: str | None = None
    constraints: list[str] = []
    description: str | None = None
    details: str | None = None
    units: str | None = None
    values: list[Any] | None = None
    range: ColumnRange | None = None
    examples: list[Any] | None = None


class TableSpec(BaseModel):
    """
    Metadata for a single table in a :class:`DataDict`.

    Parameters
    ----------
    description
        Short description of the table, forwarded to the LLM's schema view.
    details
        Longer narrative shown only in the on-demand ``get_schema`` tool
        response.
    columns
        Per-column specifications. Columns not listed here are documented
        using live statistics inferred from the data.

    """

    description: str | None = None
    details: str | None = None
    columns: list[ColumnSpec] = []


class RelationshipSpec(BaseModel):
    """
    A declared relationship between two tables.

    Parameters
    ----------
    description
        Human-readable description of the relationship.
    cardinality
        Cardinality string (e.g. ``"one-to-many"``).
    join
        SQL JOIN clause or expression that links the tables.

    """

    description: str | None = None
    cardinality: str | None = None
    join: str


class DataDict(BaseModel):
    """
    A data dictionary providing rich per-table and per-column metadata.

    Pass a ``DataDict`` to ``QueryChat`` (or load one from YAML via
    :meth:`from_yaml`) to give the LLM better context about your data without
    querying the data source for statistics at startup.

    For columns listed in a ``DataDict``:

    * ``values`` replaces categorical inference (no ``SELECT DISTINCT`` query).
    * ``range`` replaces live min/max statistics queries.
    * ``description`` is forwarded verbatim to the LLM's schema view.

    Columns not listed fall back to the normal live-statistics path.

    Parameters
    ----------
    name
        Short identifier for this dictionary's domain (e.g. ``"sales"``).
        Used as the ``name`` attribute on the ``<data-dict>`` tag in the system
        prompt. When loading from YAML via :meth:`from_yaml`, defaults to the
        file stem if not set explicitly.
    description
        One-line summary of the domain, shown alongside ``name`` in the
        system prompt.
    tables
        Per-table metadata, keyed by table name. Each value is a
        :class:`TableSpec` with optional description and column specs.
        Table names must match those registered with ``QueryChat``.
    relationships
        Cross-table relationship declarations. Useful context for multi-table
        apps where the LLM needs to know how tables join.
    glossary
        Domain-specific term definitions passed to the LLM as context
        (e.g. ``{"ARR": "Annual Recurring Revenue"}``).

    Examples
    --------
    Load from a YAML file:

    ```python
    from querychat import QueryChat, DataDict

    qc = QueryChat(df, "sales", data_dict=DataDict.from_yaml("data_dict.yaml"))
    ```

    Or pass a path directly and let QueryChat load it:

    ```python
    qc = QueryChat(df, "sales", data_dict="data_dict.yaml")
    ```

    """

    name: str | None = None
    description: str | None = None
    tables: dict[str, TableSpec] = {}
    relationships: list[RelationshipSpec] = []
    glossary: dict[str, str] = {}

    def to_prompt_dict(self) -> dict[str, Any]:
        """Return a filtered dict for the system prompt (excludes per-column details)."""
        result: dict[str, Any] = {}
        if self.name is not None:
            result["name"] = self.name
        if self.description is not None:
            result["description"] = self.description
        if self.tables:
            result["tables"] = {
                name: ({"description": spec.description} if spec.description else None)
                for name, spec in self.tables.items()
            }
        if self.relationships:
            result["relationships"] = [
                {k: v for k, v in rel.model_dump().items() if v is not None}
                for rel in self.relationships
            ]
        if self.glossary:
            result["glossary"] = self.glossary
        return result

    def get_table_schema(
        self,
        table_name: str,
        executor: QueryExecutor,
        categorical_threshold: int,
    ) -> str:
        # Get authoritative column names + types via cheap LIMIT 0
        metas: list[ColumnMeta] = executor.get_column_metas(table_name)

        # Build lookup from data_dict for this table
        table_spec = self.tables.get(table_name)
        documented: dict[str, ColumnSpec] = (
            {col.name: col for col in table_spec.columns} if table_spec else {}
        )

        undocumented: list[ColumnMeta] = []
        for meta in metas:
            spec = documented.get(meta.name)
            if spec is not None:
                if spec.range is not None:
                    meta.min_val = spec.range.min
                    meta.max_val = spec.range.max
                if spec.values is not None:
                    meta.categories = [str(v) for v in spec.values]
                if spec.description is not None:
                    meta.description = spec.description
            else:
                undocumented.append(meta)

        if undocumented:
            executor.populate_column_stats(table_name, undocumented, categorical_threshold)

        return format_schema(table_name, metas)

    @classmethod
    def from_yaml(cls, path: Path | str) -> DataDict:
        """
        Load a :class:`DataDict` from a YAML file.

        Parameters
        ----------
        path
            Path to the YAML file.

        """
        import yaml

        path = Path(path)
        with path.open() as f:
            data = yaml.safe_load(f) or {}
        dd = cls.model_validate(data)
        if dd.name is None:
            dd = dd.model_copy(update={"name": path.stem})
        return dd
