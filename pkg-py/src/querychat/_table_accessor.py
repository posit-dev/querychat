"""TableAccessor class for accessing per-table state and data."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from shiny import ui

    from ._datasource import DataSource
    from ._querychat_base import QueryChatBase
    from ._shiny_module import ServerValues


class TableAccessor:
    """
    Accessor for a specific table's state and data.

    This class provides access to per-table data source and (when server is initialized)
    reactive state. It is returned by QueryChat.table("name").

    Parameters
    ----------
    querychat
        The parent QueryChat instance.
    table_name
        The name of the table this accessor represents.

    """

    def __init__(self, querychat: QueryChatBase, table_name: str):
        self._querychat = querychat
        self._table_name = table_name

    @property
    def table_name(self) -> str:
        """The name of this table."""
        return self._table_name

    @property
    def data_source(self) -> DataSource:
        """The data source for this table."""
        return self._querychat._data_sources[self._table_name]

    def _require_server_values(self) -> ServerValues[Any]:
        """Return typed per-session state after verifying server initialization."""
        vals = getattr(self._querychat, "_vals", None)
        if vals is None:
            raise RuntimeError("Server not initialized. Call .server() first.")
        return cast("ServerValues[Any]", vals)

    def df(self) -> Any:
        """
        Return the current filtered data for this table (reactive).

        Returns the native DataFrame type (polars, pandas, ibis.Table, etc.)
        for this table's data source.

        Raises
        ------
        RuntimeError
            If called before server initialization.

        """
        return self._require_server_values().tables[self._table_name].df()

    def sql(self) -> str | None:
        """
        Return the current SQL filter for this table (reactive).

        Raises
        ------
        RuntimeError
            If called before server initialization.

        """
        return self._require_server_values().tables[self._table_name].sql.get()

    def title(self) -> str | None:
        """
        Return the current filter title for this table (reactive).

        Raises
        ------
        RuntimeError
            If called before server initialization.

        """
        return self._require_server_values().tables[self._table_name].title.get()

    def ui(self) -> ui.Tag:
        """
        Render the UI for this table (data table + SQL display).

        Returns
        -------
        Tag
            A Shiny UI element containing the data table and SQL display.

        """
        from shiny import ui as shiny_ui

        querychat_id = getattr(self._querychat, "id", None)
        if not isinstance(querychat_id, str):
            raise RuntimeError("QueryChat instance is missing an id.")

        table_id = f"{querychat_id}_{self._table_name}"

        return shiny_ui.card(
            shiny_ui.card_header(self._table_name),
            shiny_ui.output_data_frame(f"{table_id}_dt"),
            shiny_ui.output_text(f"{table_id}_sql"),
        )
