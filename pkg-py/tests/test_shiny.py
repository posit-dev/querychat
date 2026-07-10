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
