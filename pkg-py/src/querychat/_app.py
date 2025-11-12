"""Convenience function for creating a simple querychat app."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, Optional

import chatlas
from shiny import App, Inputs, Outputs, Session, reactive, render, req, ui
from shinychat import output_markdown_stream

from ._icons import bs_icon
from .datasource import DataSource
from .querychat import QueryChatConfig, _resolve_querychat_client, init
from .querychat import mod_server as server
from .querychat import sidebar

if TYPE_CHECKING:
    import sqlalchemy
    from narwhals.stable.v1.typing import IntoFrame


def app(
    x: IntoFrame | sqlalchemy.Engine | QueryChatConfig | DataSource,
    *,
    name: Optional[str] = None,
    client: Optional[str | chatlas.Chat] = None,
    bookmark_store: Literal["url", "server", "disable"] = "url",
    **kwargs,
) -> App:
    """
    Quickly chat with a dataset.

    Creates a Shiny app with a chat sidebar and data table view -- providing a
    quick-and-easy way to start chatting with your data.

    Parameters
    ----------
    x
        The dataset to chat with. Can be any one of the following:
            - A Narwhals-compatible data frame (e.g., Polars or Pandas)
            - A SQLAlchemy engine containing the table to query against.
            - The result of `querychat.init()` (for more advanced configuration).
            - A `DataSource` object.
    name
        The name of the dataset.
    client
        A `chatlas.Chat` object or a string to be passed to `chatlas.ChatAuto()`
        describing the model to use (e.g. `"openai/gpt-4.1"`). If no client is
        provided, querychat will look for the `QUERYCHAT_CLIENT` environment
        variable. If that variable is not set, it will default to
        `chatlas.ChatOpenAI()`.
    bookmark_store
        The bookmarking store to use for the Shiny app. Options are:
            - `"url"`: Store bookmarks in the URL (default).
            - `"server"`: Store bookmarks on the server.
            - `"disable"`: Disable bookmarking.
    **kwargs
        Additional keyword arguments to pass to `querychat.init()` if `x`
        is not already a QueryChatConfig object.

    Returns
    -------
    App
        A Shiny App object that can be run with `app.run()` or served with `shiny run`.

    """
    if not isinstance(x, QueryChatConfig):
        data_source = x.get_data() if isinstance(x, DataSource) else x
        x = init(data_source, table_name=name or "data", **kwargs)

    if client is not None:
        x.client = _resolve_querychat_client(client)

    enable_bookmarking = bookmark_store != "disable"

    def app_ui(request):
        return ui.page_sidebar(
            sidebar("chat"),
            ui.card(
                ui.card_header(
                    ui.div(
                        ui.div(
                            bs_icon("terminal-fill"),
                            ui.output_text("query_title", inline=True),
                            class_="d-flex align-items-center gap-2",
                        ),
                        ui.output_ui("ui_reset", inline=True),
                        class_="hstack gap-3",
                    ),
                ),
                ui.output_ui("sql_output"),
                fill=False,
                style="max-height: 33%;",
            ),
            ui.card(
                ui.card_header(bs_icon("table"), " Data"),
                ui.output_data_frame("dt"),
            ),
            title=ui.span(
                "querychat with ",
                ui.code(x.data_source.table_name),
            ),
            class_="bslib-page-dashboard",
            fillable=True,
        )

    def app_server(input: Inputs, output: Outputs, session: Session):
        qc = server("chat", x, enable_bookmarking=enable_bookmarking)

        @render.text
        def query_title():
            return qc.title() or "SQL Query"

        @render.ui
        def ui_reset():
            req(qc.sql())
            return ui.input_action_button(
                "reset_query",
                "Reset Query",
                class_="btn btn-outline-danger btn-sm lh-1 ms-auto",
            )

        @reactive.effect
        @reactive.event(input.reset_query)
        def _():
            qc.sql("")
            qc.title(None)

        @render.data_frame
        def dt():
            return qc.df()

        @render.ui
        def sql_output():
            sql = qc.sql() or f"SELECT * FROM {x.data_source.table_name}"
            sql_code = f"```sql\n{sql}\n```"
            return output_markdown_stream(
                "sql_code",
                content=sql_code,
                auto_scroll=False,
                width="100%",
            )

    return App(app_ui, app_server, bookmark_store=bookmark_store)