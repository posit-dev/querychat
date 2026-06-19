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


