"""Tests for the Shiny module UI and server wiring."""

from __future__ import annotations

import inspect
import os
from unittest.mock import patch

import pandas as pd
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


@pytest.fixture
def sample_df():
    return pd.DataFrame({"id": [1, 2, 3], "value": [10, 20, 30]})


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


def _unwrap_module_server(wrapped):
    """
    Retrieve the original function from a @module.server-decorated callable.

    Shiny's @module.server decorator stores the original function as a cell in
    the wrapper's __closure__. We locate it by scanning the closure for callables
    whose signature includes the expected module server parameters.
    """
    if wrapped.__closure__ is None:
        return wrapped
    for cell in wrapped.__closure__:
        try:
            val = cell.cell_contents
        except ValueError:
            continue
        if callable(val) and "data_sources" in inspect.signature(val).parameters:
            return val
    return wrapped


def test_mod_server_accepts_greeting_tables_and_categorical_threshold():
    """mod_server must expose greeting_tables and categorical_threshold params."""
    from querychat._shiny_module import mod_server

    fn = _unwrap_module_server(mod_server)
    params = inspect.signature(fn).parameters
    assert "greeting_tables" in params, "mod_server missing greeting_tables param"
    assert "categorical_threshold" in params, "mod_server missing categorical_threshold param"
    assert params["greeting_tables"].default is None
    assert params["categorical_threshold"].default == 20


def test_build_greeting_prompt_imported_into_shiny_module(sample_df):
    """
    Checks that build_greeting_prompt is imported into _shiny_module (so the
    module uses the shared implementation) and that calling it directly with a
    single-table source produces a schema-embedded prompt.

    Note: triggering the actual greeting reactive event requires a live Shiny
    session, which is not available in unit tests.
    """
    import narwhals.stable.v1 as nw
    import querychat._shiny_module as shiny_module
    from querychat._datasource import DataFrameSource
    from querychat._querychat_core import GREETING_MARKER, build_greeting_prompt

    # Verify build_greeting_prompt is accessible in _shiny_module
    assert hasattr(shiny_module, "build_greeting_prompt"), (
        "build_greeting_prompt must be imported into _shiny_module"
    )
    assert shiny_module.build_greeting_prompt is build_greeting_prompt

    # Verify single-table auto-mode produces a schema-containing prompt
    source = DataFrameSource(nw.from_native(sample_df), "sample")
    prompt = build_greeting_prompt(
        data_sources={"sample": source},
        categorical_threshold=20,
        greeting_tables=None,
    )
    assert prompt.startswith(GREETING_MARKER)
    assert "<schema>" in prompt


def test_build_greeting_prompt_called_with_multi_table_no_greeting_tables():
    """
    With two tables and greeting_tables=None, build_greeting_prompt omits schema.

    This mirrors the assertion from the brief: multi-table with no greeting_tables
    → GREETING_MARKER prefix present, <schema> absent.
    """
    import narwhals.stable.v1 as nw
    from querychat._datasource import DataFrameSource
    from querychat._querychat_core import GREETING_MARKER, build_greeting_prompt

    sources = {
        "orders": DataFrameSource(nw.from_native(pd.DataFrame({"id": [1]})), "orders"),
        "customers": DataFrameSource(
            nw.from_native(pd.DataFrame({"id": [1]})), "customers"
        ),
    }
    prompt = build_greeting_prompt(
        data_sources=sources,
        categorical_threshold=20,
        greeting_tables=None,
    )
    assert prompt.startswith(GREETING_MARKER)
    assert "<schema>" not in prompt


