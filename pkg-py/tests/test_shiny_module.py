"""Tests for the Shiny module UI and server wiring."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from shiny import ui


@pytest.fixture(autouse=True)
def set_dummy_api_key():
    old = os.environ.get("OPENAI_API_KEY")
    os.environ["OPENAI_API_KEY"] = "sk-dummy"
    yield
    if old is not None:
        os.environ["OPENAI_API_KEY"] = old
    else:
        del os.environ["OPENAI_API_KEY"]


def _fake_chat_ui(*args, **kwargs):
    """Return a real Tag so htmltools accepts it; stash kwargs for inspection."""
    _fake_chat_ui.last_kwargs = kwargs
    return ui.div()


_fake_chat_ui.last_kwargs: dict = {}


def test_mod_ui_enables_attachments_by_default():
    """mod_ui() should pass allow_attachments=True to shinychat.chat_ui by default."""
    from querychat._shiny_module import mod_ui

    with patch("querychat._shiny_module.shinychat.chat_ui", side_effect=_fake_chat_ui):
        mod_ui("test")  # id is required — @module.ui injects it as first positional arg
        assert _fake_chat_ui.last_kwargs.get("allow_attachments") is True


def test_mod_ui_allow_attachments_can_be_overridden():
    """Passing allow_attachments=False should disable the affordance."""
    from querychat._shiny_module import mod_ui

    with patch("querychat._shiny_module.shinychat.chat_ui", side_effect=_fake_chat_ui):
        mod_ui("test", allow_attachments=False)
        assert _fake_chat_ui.last_kwargs.get("allow_attachments") is False


def _unwrap_module_server(decorated):
    """
    Recover the undecorated function wrapped by @module.server.

    shiny's module.server decorator closes over the original function under the
    freevar name "fn"; look it up by name rather than assuming a cell index, since
    the closure's cell order isn't part of shiny's public contract.
    """
    code = decorated.__code__
    idx = code.co_freevars.index("fn")
    return decorated.__closure__[idx].cell_contents


def test_mod_server_passes_client_and_history_to_chat():
    """After this change, Chat is constructed with client= and history=."""
    from unittest.mock import MagicMock, patch

    from querychat._shiny_module import mod_server

    captured = {}

    fake_chat_instance = MagicMock()

    def fake_chat_constructor(
        id, *, client=None, greeting=None, history=None, **kwargs
    ):
        captured["client"] = client
        captured["greeting"] = greeting
        captured["history"] = history
        return fake_chat_instance

    fake_source = MagicMock()
    fake_source.get_data.return_value = []
    fake_executor = MagicMock()
    fake_executor.execute_query.return_value = []

    def client_factory(**kwargs):
        return MagicMock(spec=["stream_async"])

    inner_fn = _unwrap_module_server(mod_server)

    fake_input = MagicMock()
    fake_input.__getitem__ = MagicMock(return_value=MagicMock())
    fake_session = MagicMock()
    fake_session.is_stub_session.return_value = False

    with (
        patch(
            "querychat._shiny_module.shinychat.Chat", side_effect=fake_chat_constructor
        ),
        patch("querychat._shiny_module.has_viz_tool", return_value=False),
    ):
        inner_fn(
            fake_input,
            MagicMock(),
            fake_session,
            data_sources={"t": fake_source},
            executor=fake_executor,
            greeting=None,
            client=client_factory,
            history=True,
            tools=None,
            greeter=MagicMock(),
        )

    assert captured.get("client") is not None, "client= should be passed to Chat"
    assert captured.get("history") is True, "history= should be forwarded verbatim"
    assert callable(captured.get("greeting")), "greeting= should be a callable"


def test_mod_server_always_registers_chat_bookmarking_with_no_auto_trigger():
    """
    Chat.enable_bookmarking() must always be called -- independent of `history`
    -- so the chat client's own state round-trips through Shiny bookmarks
    whenever the host app has bookmarking enabled. It's called with
    bookmark_on=None so `history` (or the host app) remains the sole source of
    *when* to bookmark, not shinychat's own auto-trigger.
    """
    from unittest.mock import MagicMock, patch

    from querychat._shiny_module import mod_server

    fake_chat_instance = MagicMock()

    def fake_chat_constructor(
        id, *, client=None, greeting=None, history=None, **kwargs
    ):
        return fake_chat_instance

    fake_source = MagicMock()
    fake_source.get_data.return_value = []
    fake_executor = MagicMock()
    fake_executor.execute_query.return_value = []

    def client_factory(**kwargs):
        return MagicMock(spec=["stream_async"])

    inner_fn = _unwrap_module_server(mod_server)

    fake_input = MagicMock()
    fake_input.__getitem__ = MagicMock(return_value=MagicMock())
    fake_session = MagicMock()
    fake_session.is_stub_session.return_value = False

    with (
        patch(
            "querychat._shiny_module.shinychat.Chat", side_effect=fake_chat_constructor
        ),
        patch("querychat._shiny_module.has_viz_tool", return_value=False),
    ):
        inner_fn(
            fake_input,
            MagicMock(),
            fake_session,
            data_sources={"t": fake_source},
            executor=fake_executor,
            greeting=None,
            client=client_factory,
            history=True,
            tools=None,
            greeter=MagicMock(),
        )

    fake_chat_instance.enable_bookmarking.assert_called_once()
    _, kwargs = fake_chat_instance.enable_bookmarking.call_args
    assert kwargs.get("bookmark_on") is None


def test_mod_server_registers_table_state_with_both_bookmark_and_history_hooks():
    """Table/viz state callbacks must always register with both APIs, unconditionally."""
    from unittest.mock import MagicMock, patch

    from querychat._shiny_module import mod_server

    fake_chat_instance = MagicMock()

    def fake_chat_constructor(
        id, *, client=None, greeting=None, history=None, **kwargs
    ):
        return fake_chat_instance

    fake_source = MagicMock()
    fake_source.get_data.return_value = []
    fake_executor = MagicMock()
    fake_executor.execute_query.return_value = []

    def client_factory(**kwargs):
        return MagicMock(spec=["stream_async"])

    inner_fn = _unwrap_module_server(mod_server)

    fake_input = MagicMock()
    fake_input.__getitem__ = MagicMock(return_value=MagicMock())
    fake_session = MagicMock()
    fake_session.is_stub_session.return_value = False
    fake_session.bookmark = MagicMock()
    fake_session.bookmark.exclude = []

    with (
        patch(
            "querychat._shiny_module.shinychat.Chat", side_effect=fake_chat_constructor
        ),
        patch("querychat._shiny_module.has_viz_tool", return_value=False),
    ):
        inner_fn(
            fake_input,
            MagicMock(),
            fake_session,
            data_sources={"t": fake_source},
            executor=fake_executor,
            greeting=None,
            client=client_factory,
            history=False,  # even with history disabled, registration must still happen
            tools=None,
            greeter=MagicMock(),
        )

    assert "chat_update" in fake_session.bookmark.exclude
    fake_session.bookmark.on_bookmark.assert_called_once()
    fake_session.bookmark.on_restore.assert_called_once()
    fake_chat_instance.history.on_save.assert_called_once()
    fake_chat_instance.history.on_restore.assert_called_once()
