from __future__ import annotations

import math
import warnings
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

if TYPE_CHECKING:
    from ._datasource import ColumnMeta
    from ._query_executor import QueryExecutor


class ConstraintAssertion(BaseModel):
    """
    A column constraint expressed as a boolean expression.

    In the data-dict spec, entries in a column's ``constraints`` list are either
    barewords (``primary_key``, ``foreign_key``, ``required``, ``unique``) or
    assertion objects with an ``assert`` expression.

    Parameters
    ----------
    assert_
        The boolean expression (e.g. ``"amount >= 0"``). Populated from the
        YAML key ``assert``.
    language
        The language ``assert`` is written in (``sql``, ``r``, or ``python``).
    description
        Human-readable explanation of the assertion.

    """

    # populate_by_name allows construction with `assert_=` and round-trips
    # through model_dump() (which emits the field name, not the YAML alias)
    model_config = ConfigDict(populate_by_name=True)

    assert_: str = Field(alias="assert")
    language: Literal["sql", "r", "python"] | None = None
    description: str | None = None

    def __str__(self) -> str:
        if self.description:
            return f"{self.assert_} ({self.description})"
        return self.assert_


class ColumnSpec(BaseModel):
    """
    Per-column metadata entry in a :class:`DataDict`.

    Follows the column format of the `data-dict spec
    <https://data-dict.tidyverse.org/spec.html>`_. Only ``name`` is required;
    it is used to match this spec against columns returned by the data source.

    Parameters
    ----------
    name
        Column name as it appears in the data source.
    type
        Type override (e.g. ``"date"``, ``"number(quantity)"``). When
        supplied, this replaces the inferred SQL type in the LLM schema view.
    constraints
        Bareword constraints (``primary_key``, ``required``, ...) and/or
        :class:`ConstraintAssertion` objects, conveyed to the LLM.
    description
        Short description forwarded verbatim to the LLM's schema view.
    details
        Longer narrative about the column, used only in the on-demand
        ``get_schema`` tool response.
    units
        Unit label (e.g. ``"kg"``, ``"USD"``), included in the schema view.
    values
        Valid values for the column, either a list (``[M, F, U]``) or a
        value-to-label map (``{M: Male, F: Female}``). Replaces categorical
        inference for this column — querychat will not query the data source
        for distinct values when this is set. For the map form, the values
        (keys) are used.
    range
        Inclusive ``[min, max]`` bounds; either end may be ``None`` for an
        open range. Replaces live min/max statistics queries when set.
    examples
        Representative sample values shown to the LLM as context.
    label
        Display title for the column.
    time_zone
        Time zone for ``datetime`` columns, shown in the schema view.
    display
        When ``"restricted"``, the column is flagged as not for user-facing
        output.

    """

    name: str
    type: str | None = None
    constraints: list[str | ConstraintAssertion] = []
    description: str | None = None
    details: str | None = None
    units: str | None = None
    values: list[Any] | dict[str, str] | None = None
    range: list[Any] | None = None
    examples: list[Any] | None = None
    label: str | None = None
    time_zone: str | None = None
    display: Literal["restricted"] | None = None

    @field_validator("values", mode="before")
    @classmethod
    def _values_map_keys_are_strings(cls, v: Any) -> Any:
        # YAML parses numeric map keys (e.g. {0: Control, 1: Treatment}) as
        # ints; the spec allows them, so coerce keys to strings.
        if isinstance(v, dict):
            return {str(k): val for k, val in v.items()}
        return v

    @field_validator("range", mode="before")
    @classmethod
    def _range_open_bound_sentinels(cls, v: Any) -> Any:
        # The spec's open-bound sentinels (-.inf/.inf) parse as float
        # infinities; normalize them to None for an open end.
        if isinstance(v, list):
            return [None if isinstance(x, float) and math.isinf(x) else x for x in v]
        return v

    @field_validator("range")
    @classmethod
    def _range_is_two_elements(cls, v: list[Any] | None) -> list[Any] | None:
        if v is not None and len(v) != 2:  # noqa: PLR2004
            raise ValueError(
                "range must be a two-element list [min, max]; "
                "use null (or the spec's -.inf/.inf sentinels) for an open end"
            )
        return v


class TableSpec(BaseModel):
    """
    Metadata for a single table in a :class:`DataDict`.

    Parameters
    ----------
    name
        Table name. Must match a table registered with ``QueryChat``.
    description
        Short description of the table, forwarded to the LLM's schema view.
    details
        Longer narrative shown only in the on-demand ``get_schema`` tool
        response.
    columns
        Per-column specifications. Columns not listed here are documented
        using live statistics inferred from the data.
    label
        Display title for the table.
    constraints
        Table-level assertions conveyed to the LLM in the ``get_schema``
        response.

    """

    name: str
    description: str | None = None
    details: str | None = None
    columns: list[ColumnSpec] = []
    label: str | None = None
    constraints: list[str | ConstraintAssertion] = []


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
    aliases
        Alias-to-table map naming the role each join side plays (required
        for self-joins).
    conflicts
        Column names that appear on both sides of the join with different
        meanings.

    """

    description: str | None = None
    cardinality: str | None = None
    join: str
    aliases: dict[str, str] | None = None
    conflicts: list[str] | None = None


_LEGACY_TABLES_MESSAGE = """\
This data dictionary uses an outdated format: `tables` must be a list of
tables, each with a `name` field — not a mapping of name to definition.

    # before
    tables:
      orders:
        columns: [...]

    # after
    tables:
      - name: orders
        columns: [...]

Also changed in the current spec: column `range` is a two-element list
[min, max], and `values` may be a value-to-label map ({M: Male, F: Female}).

Run `data-dict validate-spec <file>` to check the file against the spec:
https://data-dict.tidyverse.org/spec.html
"""

# The newest data-dict spec version this version of querychat fully
# understands. Files declaring a newer `$version` are still read, on a
# best-effort basis (unknown fields are ignored), with a warning. Bump this
# opportunistically to keep the warning calibrated — it is not a hard gate.
_KNOWN_SPEC_VERSION = (0, 1, 0)


def _parse_spec_version(value: Any) -> tuple[int, int, int] | None:
    """
    Parse a `$version` value into a (major, minor, patch) tuple.

    Returns ``None`` when ``value`` is not a recognizable version string.
    Short forms are zero-padded, so ``"0.1"`` parses as ``(0, 1, 0)``.
    """
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        return None
    parts = str(value).split(".")
    if len(parts) > 3 or not all(p.isdigit() for p in parts):  # noqa: PLR2004
        return None
    nums = [int(p) for p in parts]
    # Zero-pad short forms, so "0.1" parses as (0, 1, 0)
    nums.extend([0] * (3 - len(nums)))
    return (nums[0], nums[1], nums[2])


def _check_spec_version(version: Any) -> None:
    parsed = _parse_spec_version(version)
    if parsed is None:
        warnings.warn(
            f"This data dictionary has an invalid `$version`: {version!r}. "
            'Expected a version like "0.1.0"; see '
            "https://data-dict.tidyverse.org/spec.html",
            stacklevel=3,
        )
        return
    if parsed < (0, 1, 0):
        warnings.warn(
            f'This data dictionary declares `$version: "{version}"`, which '
            "predates the first data-dict spec version (0.1.0). See "
            "https://data-dict.tidyverse.org/spec.html",
            stacklevel=3,
        )
        return
    if parsed > _KNOWN_SPEC_VERSION:
        known = ".".join(str(p) for p in _KNOWN_SPEC_VERSION)
        warnings.warn(
            f'This data dictionary declares `$version: "{version}"`, which is '
            "newer than the newest data-dict spec version this version of "
            f"querychat fully understands ({known}). The file is read on a "
            "best-effort basis — spec fields querychat doesn't know about are "
            "ignored. If anything looks off, upgrade querychat, or check the "
            "file against the spec with `data-dict validate-spec <file>`: "
            "https://data-dict.tidyverse.org/spec.html",
            stacklevel=3,
        )


class DataDict(BaseModel):
    """
    A data dictionary providing rich per-table and per-column metadata.

    Pass a ``DataDict`` to ``QueryChat`` (or load one from YAML via
    :meth:`from_yaml`) to give the LLM better context about your data without
    querying the data source for statistics at startup. Files must follow the
    current `data-dict spec <https://data-dict.tidyverse.org/spec.html>`_.

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
        Per-table metadata. Each :class:`TableSpec` has a required ``name``
        that must match a table registered with ``QueryChat``.
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

    qc = QueryChat(df, "sales", data_dict=DataDict.from_yaml("data-dict.yaml"))
    ```

    Or pass a path directly and let QueryChat load it:

    ```python
    qc = QueryChat(df, "sales", data_dict="data-dict.yaml")
    ```

    """

    name: str | None = None
    description: str | None = None
    tables: list[TableSpec] = []
    relationships: list[RelationshipSpec] = []
    glossary: dict[str, str] = {}

    @model_validator(mode="before")
    @classmethod
    def _reject_legacy_tables(cls, data: Any) -> Any:
        if isinstance(data, dict) and isinstance(data.get("tables"), dict):
            # ValueError (not TypeError) so pydantic wraps it in ValidationError
            raise ValueError(_LEGACY_TABLES_MESSAGE)  # noqa: TRY004
        return data

    @model_validator(mode="before")
    @classmethod
    def _reject_unsupported_spec_version(cls, data: Any) -> Any:
        if isinstance(data, dict) and "$version" in data:
            _check_spec_version(data["$version"])
        return data

    def get_table(self, table_name: str) -> TableSpec | None:
        """Return the :class:`TableSpec` for ``table_name``, or ``None``."""
        return next((t for t in self.tables if t.name == table_name), None)

    def to_prompt_dict(self) -> dict[str, Any]:
        """Return a filtered dict for the system prompt (excludes per-column details)."""
        result: dict[str, Any] = {}
        if self.name is not None:
            result["name"] = self.name
        if self.description is not None:
            result["description"] = self.description
        if self.tables:
            result["tables"] = {
                t.name: (
                    {
                        k: v
                        for k, v in {
                            "description": t.description,
                            "label": t.label,
                        }.items()
                        if v is not None
                    }
                    or None
                )
                for t in self.tables
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
    ) -> list[ColumnMeta]:
        # Get authoritative column names + types via cheap LIMIT 0
        metas: list[ColumnMeta] = executor.get_column_metas(table_name)

        # Build lookup from data_dict for this table
        table_spec = self.get_table(table_name)
        documented: dict[str, ColumnSpec] = (
            {col.name: col for col in table_spec.columns} if table_spec else {}
        )

        undocumented: list[ColumnMeta] = []
        for meta in metas:
            spec = documented.get(meta.name)
            if spec is not None:
                apply_column_spec(meta, spec)
            else:
                undocumented.append(meta)

        if undocumented:
            executor.populate_column_stats(
                table_name, undocumented, categorical_threshold
            )

        return metas

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


def apply_column_spec(meta: ColumnMeta, spec: ColumnSpec) -> None:
    """Overlay a :class:`ColumnSpec` onto a live :class:`ColumnMeta`."""
    if spec.type is not None:
        meta.sql_type = spec.type
    if spec.range is not None:
        meta.min_val = spec.range[0]
        meta.max_val = spec.range[1]
    if spec.values is not None:
        if isinstance(spec.values, dict):
            meta.categories = [str(k) for k in spec.values]
            meta.value_labels = dict(spec.values)
        else:
            meta.categories = [str(v) for v in spec.values]
    if spec.description is not None:
        meta.description = spec.description
    if spec.units is not None:
        meta.units = spec.units
    if spec.constraints:
        meta.constraints = [str(c) for c in spec.constraints]
    if spec.label is not None:
        meta.label = spec.label
    if spec.time_zone is not None:
        meta.time_zone = spec.time_zone
    if spec.display is not None:
        meta.display = spec.display
    if spec.examples is not None and spec.display != "restricted":
        meta.examples = [str(e) for e in spec.examples]
