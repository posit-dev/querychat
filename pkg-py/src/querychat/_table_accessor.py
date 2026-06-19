"""TableAccessor class for accessing per-table state and data."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from shiny import ui

    from ._datasource import DataSource


NO_STATE_MSG = (
    "Reactive methods are not available on qc.table(). "
    "Use the server return value: qc_vals.table('{name}').{method}()."
)


class TableAccessor:
    """
    Accessor for a specific table's state and data.

    When constructed with ``state``, provides reactive ``df()``, ``sql()``,
    ``title()`` methods. When constructed without ``state`` (config-only),
    those methods raise with guidance to use the server return value.

    Parameters
    ----------
    table_name
        The name of the table this accessor represents.
    data_source
        The DataSource for this table.
    state
        Optional per-table reactive state. When provided, enables
        ``df()``, ``sql()``, ``title()`` methods.

    """

    def __init__(
        self,
        table_name: str,
        data_source: DataSource,
        *,
        state: Any = None,
    ):
        self._table_name = table_name
        self._data_source = data_source
        self._state = state

    @property
    def table_name(self) -> str:
        """The name of this table."""
        return self._table_name

    @property
    def data_source(self) -> DataSource:
        """The data source for this table."""
        return self._data_source

    def _require_state(self, method: str) -> Any:
        if self._state is None:
            raise RuntimeError(
                NO_STATE_MSG.format(name=self._table_name, method=method)
            )
        return self._state

    def df(self) -> Any:
        """Return the current filtered data for this table (reactive)."""
        return self._require_state("df").df()

    def sql(self) -> str | None:
        """Return the current SQL filter for this table (reactive)."""
        return self._require_state("sql").sql.get()

    def title(self) -> str | None:
        """Return the current filter title for this table (reactive)."""
        return self._require_state("title").title.get()

    def ui(self) -> ui.Tag:
        """Render the UI for this table (data table + SQL display)."""
        from shiny import ui as shiny_ui

        table_id = f"{self._table_name}"

        return shiny_ui.card(
            shiny_ui.card_header(self._table_name),
            shiny_ui.output_data_frame(f"{table_id}_dt"),
            shiny_ui.output_text(f"{table_id}_sql"),
        )


class StateDictTableAccessor(TableAccessor):
    """
    Per-table accessor for frameworks that use a state dict (Dash, Gradio).

    ``data_source`` and ``table_name`` work normally. ``df()``, ``sql()``, and
    ``title()`` raise ``NotImplementedError`` — those frameworks pass state
    explicitly, so use ``qc.df(state, table=name)`` inside your callback.
    """

    def df(self) -> Any:
        raise NotImplementedError(
            f"TableAccessor.df() is not available for this framework. "
            f"Use qc.df(state, table='{self._table_name}') inside your callback instead."
        )

    def sql(self) -> str | None:
        raise NotImplementedError(
            f"TableAccessor.sql() is not available for this framework. "
            f"Use qc.sql(state, table='{self._table_name}') inside your callback instead."
        )

    def title(self) -> str | None:
        raise NotImplementedError(
            f"TableAccessor.title() is not available for this framework. "
            f"Use qc.title(state, table='{self._table_name}') inside your callback instead."
        )
