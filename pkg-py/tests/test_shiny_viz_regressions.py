"""Regression tests for Shiny ggsql tool wiring and bookmark restore."""

import inspect
import os
from types import SimpleNamespace
from unittest.mock import patch

import chatlas
import pytest
from querychat import QueryChat
from querychat._shiny import QueryChatExpress
from querychat._shiny_module import mod_server
from querychat.data import tips

from shiny import reactive


@pytest.fixture(autouse=True)
def set_dummy_api_key():
    old_api_key = os.environ.get("OPENAI_API_KEY")
    os.environ["OPENAI_API_KEY"] = "sk-dummy-api-key-for-testing"
    yield
    if old_api_key is not None:
        os.environ["OPENAI_API_KEY"] = old_api_key
    else:
        del os.environ["OPENAI_API_KEY"]


@pytest.fixture
def sample_df():
    return tips()


def _identity(fn):
    return fn


def _event(*_args, **_kwargs):
    def wrapper(fn):
        return fn

    return wrapper


def _raw_mod_server():
    return inspect.getclosurevars(mod_server).nonlocals["fn"]


class DummyBookmark:
    def on_bookmark(self, fn):
        self.bookmark_fn = fn
        return fn

    def on_restore(self, fn):
        self.restore_fn = fn
        return fn


class DummySession:
    def __init__(self):
        self.bookmark = DummyBookmark()

    def is_stub_session(self):
        return False


class DummyStubSession(DummySession):
    def is_stub_session(self):
        return True


class DummyChatUi:
    def __init__(self, *_args, **_kwargs):
        pass

    def on_user_submit(self, fn):
        return fn

    async def append_message_stream(self, _stream):
        return None

    async def append_message(self, _message):
        return None

    def enable_bookmarking(self, _chat):
        return None


class DummyProvider(chatlas.Provider):
    def __init__(self, *, name, model):
        super().__init__(name=name, model=model)

    def list_models(self):
        return []

    def chat_perform(self, *, stream, turns, tools, data_model, kwargs):
        return () if stream else SimpleNamespace()

    async def chat_perform_async(
        self, *, stream, turns, tools, data_model, kwargs
    ):
        return () if stream else SimpleNamespace()

    def stream_content(self, chunk):
        return None

    def stream_text(self, chunk):
        return None

    def stream_merge_chunks(self, completion, chunk):
        return completion or {}

    def stream_turn(self, completion, has_data_model):
        return SimpleNamespace()

    def value_turn(self, completion, has_data_model):
        return SimpleNamespace()

    def value_tokens(self, completion):
        return (0, 0, 0)

    def token_count(self, *args, tools, data_model):
        return 0

    async def token_count_async(self, *args, tools, data_model):
        return 0

    def translate_model_params(self, params):
        return params

    def supported_model_params(self):
        return set()


def test_app_passes_callable_client_to_mod_server(sample_df):
    qc = QueryChat(sample_df, "tips", tools=("query", "visualize_query"))
    app = qc.app()
    captured = {}

    def fake_mod_server(*args, **kwargs):
        captured.update(kwargs)
        vals = SimpleNamespace()
        vals.title = lambda: None
        vals.sql = lambda: None
        vals.df = list
        vals.title.set = lambda _value: None
        vals.sql.set = lambda _value: None
        return vals

    with (
        patch("querychat._shiny.mod_server", fake_mod_server),
        patch("querychat._shiny.render.text", _identity),
        patch("querychat._shiny.render.ui", _identity),
        patch("querychat._shiny.render.data_frame", _identity),
        patch("querychat._shiny.reactive.effect", _identity),
        patch("querychat._shiny.reactive.event", _event),
        patch("querychat._shiny.req", lambda value: value),
        patch("querychat._shiny.output_markdown_stream", lambda *a, **k: None),
    ):
        app.server(
            SimpleNamespace(reset_query=lambda: None),
            SimpleNamespace(),
            SimpleNamespace(),
        )

    assert callable(captured["client"])
    assert not isinstance(captured["client"], chatlas.Chat)


def test_express_passes_callable_client_to_mod_server(sample_df, monkeypatch):
    captured = {}

    class CurrentSession:
        pass

    monkeypatch.setattr("querychat._shiny.get_current_session", lambda: CurrentSession())
    monkeypatch.setattr(
        "querychat._shiny.mod_server",
        lambda *args, **kwargs: captured.update(kwargs) or SimpleNamespace(),
    )

    QueryChatExpress(
        sample_df,
        "tips",
        tools=("query", "visualize_query"),
        enable_bookmarking=False,
    )

    assert callable(captured["client"])
    assert not isinstance(captured["client"], chatlas.Chat)


def test_server_passes_callable_client_to_mod_server(sample_df, monkeypatch):
    qc = QueryChat(sample_df, "tips", tools=("query", "visualize_query"))
    captured = {}

    class CurrentSession:
        pass

    monkeypatch.setattr("querychat._shiny.get_current_session", lambda: CurrentSession())
    monkeypatch.setattr(
        "querychat._shiny.mod_server",
        lambda *args, **kwargs: captured.update(kwargs) or SimpleNamespace(),
    )

    qc.server(enable_bookmarking=False)

    assert callable(captured["client"])
    assert not isinstance(captured["client"], chatlas.Chat)


def test_mod_server_rejects_raw_chat_instance(sample_df):
    qc = QueryChat(sample_df, "tips", tools=("query", "visualize_query"))
    raw_chat = chatlas.Chat(provider=DummyProvider(name="dummy", model="dummy"))

    with (
        patch("querychat._shiny_module.preload_viz_deps_server", lambda: None),
        patch("querychat._shiny_module.shinychat.Chat", DummyChatUi),
        pytest.raises(TypeError, match="callable"),
    ):
        _raw_mod_server()(
            SimpleNamespace(chat_update=lambda: None),
            SimpleNamespace(),
            DummySession(),
            data_source=qc.data_source,
            greeting=qc.greeting,
            client=raw_chat,
            enable_bookmarking=False,
            tools=qc.tools,
        )


def test_mod_server_stub_session_deferred_client_factory_does_not_raise():
    qc = QueryChat(None, "users")

    vals = _raw_mod_server()(
        SimpleNamespace(chat_update=lambda: None),
        SimpleNamespace(),
        DummyStubSession(),
        data_source=None,
        greeting=qc.greeting,
        client=qc.client,
        enable_bookmarking=False,
        tools=qc.tools,
    )

    with pytest.raises(RuntimeError, match="unavailable during stub session"):
        _ = vals.client.stream_async


def test_callable_mod_server_passes_visualize_callback_and_tools(sample_df):
    qc = QueryChat(sample_df, "tips", tools=("query", "visualize_query"))
    captured = {}

    def client_factory(**kwargs):
        captured.update(kwargs)
        return qc.client(**kwargs)

    with (
        patch("querychat._shiny_module.preload_viz_deps_server", lambda: None),
        patch("querychat._shiny_module.shinychat.Chat", DummyChatUi),
    ):
        _raw_mod_server()(
            SimpleNamespace(chat_update=lambda: None),
            SimpleNamespace(),
            DummySession(),
            data_source=qc.data_source,
            greeting=qc.greeting,
            client=client_factory,
            enable_bookmarking=False,
            tools=qc.tools,
        )

    assert captured["tools"] == ("query", "visualize_query")
    assert callable(captured["visualize_query"])
    assert callable(captured["update_dashboard"])
    assert callable(captured["reset_dashboard"])


def test_mod_server_preloads_viz_for_each_real_session_instance(sample_df):
    qc = QueryChat(sample_df, "tips", tools=("query", "visualize_query"))
    session = DummySession()
    preload_calls = []

    with (
        patch(
            "querychat._shiny_module.preload_viz_deps_server",
            lambda: preload_calls.append("called"),
        ),
        patch("querychat._shiny_module.shinychat.Chat", DummyChatUi),
    ):
        _raw_mod_server()(
            SimpleNamespace(chat_update=lambda: None),
            SimpleNamespace(),
            session,
            data_source=qc.data_source,
            greeting=qc.greeting,
            client=qc.client,
            enable_bookmarking=False,
            tools=qc.tools,
        )
        _raw_mod_server()(
            SimpleNamespace(chat_update=lambda: None),
            SimpleNamespace(),
            session,
            data_source=qc.data_source,
            greeting=qc.greeting,
            client=qc.client,
            enable_bookmarking=False,
            tools=qc.tools,
        )

    assert preload_calls == ["called", "called"]


def test_mod_server_stub_session_does_not_preload_viz(sample_df):
    qc = QueryChat(sample_df, "tips", tools=("query", "visualize_query"))
    preload_calls = []

    with (
        patch(
            "querychat._shiny_module.preload_viz_deps_server",
            lambda: preload_calls.append("called"),
        ),
        patch("querychat._shiny_module.shinychat.Chat", DummyChatUi),
    ):
        _raw_mod_server()(
            SimpleNamespace(chat_update=lambda: None),
            SimpleNamespace(),
            DummyStubSession(),
            data_source=qc.data_source,
            greeting=qc.greeting,
            client=qc.client,
            enable_bookmarking=False,
            tools=qc.tools,
        )

    assert preload_calls == []


def test_restored_viz_widgets_survive_second_bookmark_cycle(sample_df):
    qc = QueryChat(sample_df, "tips", tools=("query", "visualize_query"))
    callbacks = {}
    session = DummySession()

    def client_factory(**kwargs):
        callbacks.update(kwargs)
        return qc.client(**kwargs)

    with (
        patch("querychat._shiny_module.preload_viz_deps_server", lambda: None),
        patch("querychat._shiny_module.shinychat.Chat", DummyChatUi),
        patch(
            "querychat._shiny_module.restore_viz_widgets",
            lambda _data_source, saved_widgets: list(saved_widgets),
        ),
    ):
        _raw_mod_server()(
            SimpleNamespace(chat_update=lambda: None),
            SimpleNamespace(),
            session,
            data_source=qc.data_source,
            greeting=qc.greeting,
            client=client_factory,
            enable_bookmarking=True,
            tools=qc.tools,
        )
        saved = [
            {
                "widget_id": "querychat_viz_1",
                "ggsql": "SELECT 1 VISUALISE 1 AS x DRAW point",
            }
        ]
        callbacks["visualize_query"](saved[0])

        first_bookmark = SimpleNamespace(values={})
        with reactive.isolate():
            session.bookmark.bookmark_fn(first_bookmark)
        assert first_bookmark.values["querychat_viz_widgets"] == saved

        with reactive.isolate():
            session.bookmark.restore_fn(SimpleNamespace(values=first_bookmark.values))

        second_bookmark = SimpleNamespace(values={})
        with reactive.isolate():
            session.bookmark.bookmark_fn(second_bookmark)
        assert second_bookmark.values["querychat_viz_widgets"] == saved
