"""
Tests for QueryChat's Shiny-specific public API: history/enable_bookmarking
resolution and deprecation, and $app()'s bookmark inference.
"""

from __future__ import annotations

import os

import pytest


@pytest.fixture(autouse=True)
def set_dummy_api_key():
    old = os.environ.get("OPENAI_API_KEY")
    os.environ["OPENAI_API_KEY"] = "sk-dummy"
    yield
    if old is not None:
        os.environ["OPENAI_API_KEY"] = old
    else:
        del os.environ["OPENAI_API_KEY"]


def test_server_history_stored_verbatim_before_resolution():
    """Constructor-level history isn't substituted until .server()/.app() resolve it."""
    import pandas as pd
    from querychat._shiny import QueryChat

    qc_no_history = QueryChat(pd.DataFrame({"a": [1]}), "a_table")
    assert qc_no_history.history is None

    qc_explicit = QueryChat(pd.DataFrame({"a": [1]}), "a_table2", history=False)
    assert qc_explicit.history is False


def test_server_resolves_history_and_warns_on_explicit_enable_bookmarking(monkeypatch):
    import warnings
    from unittest.mock import MagicMock, patch

    import pandas as pd
    from querychat._shiny import QueryChat

    qc = QueryChat(pd.DataFrame({"a": [1, 2, 3]}), "a_table")

    captured = {}

    def fake_mod_server(*args, **kwargs):
        captured.update(kwargs)
        return MagicMock()

    fake_session = MagicMock()
    with (
        patch("querychat._shiny.get_current_session", return_value=fake_session),
        patch("querychat._shiny.mod_server", side_effect=fake_mod_server),
    ):
        # Not passing enable_bookmarking or history: no warning, history resolves to True.
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            qc.server()
        assert captured["history"] is True

        # Explicit enable_bookmarking=True warns, and -- since history wasn't
        # otherwise set -- resolves to bookmark-mode history (the equivalent
        # of the old bookmarking behavior).
        from shinychat.types import HistoryOptions

        with pytest.warns(FutureWarning, match="history"):
            qc.server(enable_bookmarking=True)
        assert isinstance(captured["history"], HistoryOptions)
        assert captured["history"].restore_mode == "bookmark"

        # enable_bookmarking=False warns but has no effect on its own.
        with pytest.warns(FutureWarning, match="history"):
            qc.server(enable_bookmarking=False)
        assert captured["history"] is True

        # Explicit history= still takes precedence over enable_bookmarking.
        with pytest.warns(FutureWarning, match="history"):
            qc.server(history=False, enable_bookmarking=True)
        assert captured["history"] is False

        # Explicit history= takes precedence over self.history.
        qc.history = False
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            qc.server(history=True)
        assert captured["history"] is True

        # self.history takes precedence over the True fallback when history= not passed.
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            qc.server()
        assert captured["history"] is False

        # self.history also takes precedence over the enable_bookmarking mapping.
        with pytest.warns(FutureWarning, match="history"):
            qc.server(enable_bookmarking=True)
        assert captured["history"] is False


def test_app_defaults_history_to_bookmark_restore_mode_and_enables_shiny_bookmarking():

    import pandas as pd
    from querychat._shiny import QueryChat

    qc = QueryChat(pd.DataFrame({"a": [1, 2, 3]}), "a_table")
    app = qc.app()

    assert app.bookmark_store == "server"


def test_app_disables_shiny_bookmarking_when_history_is_not_bookmark_mode():
    import pandas as pd
    from querychat._shiny import QueryChat

    qc = QueryChat(pd.DataFrame({"a": [1, 2, 3]}), "a_table", history=True)
    app = qc.app()

    assert app.bookmark_store == "disable"


def test_app_respects_explicit_constructor_history_over_apps_own_default():
    """
    An explicit QueryChat(history=False) must not be silently overridden by
    $app()'s own restore_mode='bookmark' default.
    """
    import pandas as pd
    from querychat._shiny import QueryChat

    qc = QueryChat(pd.DataFrame({"a": [1, 2, 3]}), "a_table", history=False)
    app = qc.app()

    assert app.bookmark_store == "disable"


def test_express_enable_bookmarking_auto_emits_no_warning_and_uses_history():
    from unittest.mock import MagicMock, patch

    import pandas as pd
    from querychat._shiny import QueryChatExpress
    from shiny.express._stub_session import ExpressStubSession

    fake_stub_session = MagicMock(spec=ExpressStubSession)
    fake_stub_session.app_opts = {}

    with patch("querychat._shiny.get_current_session", return_value=fake_stub_session):
        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter("error")
            QueryChatExpress(pd.DataFrame({"a": [1, 2, 3]}), "a_table")


def test_express_enable_bookmarking_resolves_to_bookmark_mode_history(monkeypatch):
    """
    enable_bookmarking=True at construction time must map to bookmark-mode
    history once the real server starts, mirroring QueryChat.server()'s
    resolution (see test_server_resolves_history_and_warns_on_explicit_enable_bookmarking).
    """
    from unittest.mock import MagicMock

    import pandas as pd
    from querychat._shiny import QueryChatExpress
    from shiny._namespaces import Root
    from shiny.session import session_context
    from shinychat.types import HistoryOptions

    captured = {}

    def fake_mod_server(*args, **kwargs):
        captured.update(kwargs)
        return MagicMock()

    monkeypatch.setattr("querychat._shiny.mod_server", fake_mod_server)

    mock_session = MagicMock()
    mock_session.ns = Root
    with session_context(mock_session):
        with pytest.warns(FutureWarning, match="history"):
            qc = QueryChatExpress(
                pd.DataFrame({"a": [1, 2, 3]}), "a_table", enable_bookmarking=True
            )
        qc._ensure_server_started()

    assert isinstance(captured["history"], HistoryOptions)
    assert captured["history"].restore_mode == "bookmark"


def test_ensure_server_started_does_not_retry_after_failed_attempt(monkeypatch):
    """
    A mod_server() failure must not be retried within the same session by a
    later lazy call (e.g. from .df()/.sql()/.ui()) -- retrying would
    re-register mod_server()'s non-idempotent reactive effects and
    bookmark/history hooks a second time.
    """
    from unittest.mock import MagicMock

    import pandas as pd
    from querychat._shiny import QueryChatExpress
    from shiny._namespaces import Root
    from shiny.session import session_context

    calls = 0

    def failing_mod_server(*args, **kwargs):
        nonlocal calls
        calls += 1
        raise RuntimeError("mod_server failed")

    monkeypatch.setattr("querychat._shiny.mod_server", failing_mod_server)

    mock_session = MagicMock()
    mock_session.ns = Root
    with session_context(mock_session):
        qc = QueryChatExpress(pd.DataFrame({"a": [1, 2, 3]}), "a_table")

        with pytest.raises(RuntimeError, match="mod_server failed"):
            qc._ensure_server_started()
        assert calls == 1

        # A later lazy call must not retry mod_server() a second time.
        with pytest.raises(RuntimeError, match="not initialized"):
            qc._require_vals()
        assert calls == 1


def test_express_explicit_enable_bookmarking_warns():
    from unittest.mock import MagicMock, patch

    import pandas as pd
    from querychat._shiny import QueryChatExpress
    from shiny.express._stub_session import ExpressStubSession

    fake_stub_session = MagicMock(spec=ExpressStubSession)
    fake_stub_session.app_opts = {}

    with (
        patch("querychat._shiny.get_current_session", return_value=fake_stub_session),
        pytest.warns(FutureWarning, match="history"),
    ):
        QueryChatExpress(
            pd.DataFrame({"a": [1, 2, 3]}), "a_table", enable_bookmarking=True
        )


def test_app_ui_uses_page_layout_with_drawer():
    """
    $app() builds on the page_chat() layout, with the data table as the
    drawer's primary content and the SQL editor tucked into a collapsible
    "Show Query" footer control -- the drawer is auto-opened server-side on
    query, and sized with a clamp-based width so it doesn't dominate
    mid-size viewports.
    """
    import re

    import pandas as pd
    from querychat._shiny import QueryChat

    qc = QueryChat(pd.DataFrame({"a": [1]}), "a_table")
    app = qc.app()
    html = str(app.ui(None))

    # Chat-primary page layout (page_chat), not the old page_sidebar dashboard
    assert 'id="querychat_a_table-chat_page"' in html
    drawer = re.search(r"<shiny-chat-drawer\b[^>]*>", html)
    assert drawer, "no <shiny-chat-drawer> found in app UI"
    # htmltools omits False-valued attributes; no `open` means initially closed
    assert "open=" not in drawer.group(0)
    assert 'width="calc(min(clamp(360px, 55vw, 720px), 100%))"' in drawer.group(0)
    assert 'title="Data Sources"' in drawer.group(0)
    # Data views live inside the drawer
    drawer_html = html[drawer.start() :]
    assert 'id="dt"' in drawer_html
    # SQL editor is a second-class citizen: tucked into the data card's
    # footer behind a "Show Query" toggle, not its own top-level card
    assert 'id="sql_output"' in drawer_html
    assert 'class="querychat-show-query-btn' in drawer_html
    assert 'data-querychat-action="show-query"' in drawer_html
    assert 'id="ui_reset"' in drawer_html
    # A single-table app has nothing to browse on demand, so no accordion
    assert 'id="data_sources_accordion"' not in drawer_html
    # Handoff panel still present via the page extras
    assert 'id="querychat_a_table-handoff_download"' in html


def test_app_ui_drawer_multi_table_accordion():
    """
    With more than one table, the drawer adds a fully static accordion below
    the pinned "active table" card, giving on-demand access to every
    registered table without disturbing the active-table-follows-the-chat
    behavior of the pinned card.
    """
    import pandas as pd
    from querychat._shiny import QueryChat

    qc = QueryChat(pd.DataFrame({"a": [1]}), "orders")
    qc.add_table(pd.DataFrame({"b": [2]}), "customers")
    app = qc.app()
    html = str(app.ui(None))

    assert 'id="data_sources_accordion"' in html
    for name in ("orders", "customers"):
        assert f'id="dt_{name}"' in html
        assert f'id="active_badge_{name}"' in html
        assert f'data-target="sql_query_section_{name}"' in html
        assert f'id="sql_query_section_{name}"' in html
    # The pinned "active table" card is unaffected by the accordion
    assert 'id="dt"' in html
    assert 'id="ui_reset"' in html
