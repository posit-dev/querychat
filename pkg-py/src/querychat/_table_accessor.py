"""TableAccessor class for accessing per-table state and data."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from shiny import ui

    from ._datasource import DataSource


class TableAccessor:
    """
    Accessor for a specific table's reactive state and data.

    Returned by ``qc_vals.table("name")`` in Shiny server callbacks, and by
    ``qc.table("name")`` in Streamlit. Provides ``df()``, ``sql()``, and
    ``title()`` backed by per-session reactive state.

    Parameters
    ----------
    table_name
        The name of the table this accessor represents.
    data_source
        The DataSource for this table.
    state
        Per-table reactive state, wired up by the framework.

    """

    def __init__(
        self,
        table_name: str,
        data_source: DataSource,
        *,
        state: Any,
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

    def df(self) -> Any:
        """Return the current filtered data for this table (reactive)."""
        return self._state.df()

    def sql(self) -> str | None:
        """Return the current SQL filter for this table (reactive)."""
        return self._state.sql.get()

    def title(self) -> str | None:
        """Return the current filter title for this table (reactive)."""
        return self._state.title.get()

    def ui(self) -> ui.Tag:
        """Render the UI for this table (data table + SQL display)."""
        from shiny import ui as shiny_ui

        table_id = f"{self._table_name}"

        return shiny_ui.card(
            shiny_ui.card_header(self._table_name),
            shiny_ui.output_data_frame(f"{table_id}_dt"),
            shiny_ui.output_text(f"{table_id}_sql"),
        )
