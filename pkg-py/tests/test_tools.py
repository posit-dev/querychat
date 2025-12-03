"""Tests for tool functions and utilities."""

import warnings

import pytest

from querychat._utils import resolve_tool_open_state


def test_resolve_tool_open_state_default_behavior(monkeypatch):
    """Test default behavior when no setting is provided."""
    monkeypatch.delenv("QUERYCHAT_TOOL_DETAILS", raising=False)

    assert resolve_tool_open_state("query", False) is True
    assert resolve_tool_open_state("update", False) is True
    assert resolve_tool_open_state("reset", False) is False
    assert resolve_tool_open_state("query", True) is False


def test_resolve_tool_open_state_expanded(monkeypatch):
    """Test 'expanded' setting."""
    monkeypatch.setenv("QUERYCHAT_TOOL_DETAILS", "expanded")

    assert resolve_tool_open_state("query", False) is True
    assert resolve_tool_open_state("update", False) is True
    assert resolve_tool_open_state("reset", False) is True
    assert resolve_tool_open_state("query", True) is False


def test_resolve_tool_open_state_collapsed(monkeypatch):
    """Test 'collapsed' setting."""
    monkeypatch.setenv("QUERYCHAT_TOOL_DETAILS", "collapsed")

    assert resolve_tool_open_state("query", False) is False
    assert resolve_tool_open_state("update", False) is False
    assert resolve_tool_open_state("reset", False) is False
    assert resolve_tool_open_state("query", True) is False


def test_resolve_tool_open_state_default_setting(monkeypatch):
    """Test 'default' setting."""
    monkeypatch.setenv("QUERYCHAT_TOOL_DETAILS", "default")

    assert resolve_tool_open_state("query", False) is True
    assert resolve_tool_open_state("update", False) is True
    assert resolve_tool_open_state("reset", False) is False
    assert resolve_tool_open_state("query", True) is False


def test_resolve_tool_open_state_case_insensitive(monkeypatch):
    """Test that setting is case-insensitive."""
    monkeypatch.setenv("QUERYCHAT_TOOL_DETAILS", "EXPANDED")
    assert resolve_tool_open_state("query", False) is True

    monkeypatch.setenv("QUERYCHAT_TOOL_DETAILS", "Collapsed")
    assert resolve_tool_open_state("query", False) is False

    monkeypatch.setenv("QUERYCHAT_TOOL_DETAILS", "DeFaUlT")
    assert resolve_tool_open_state("query", False) is True


def test_resolve_tool_open_state_invalid_setting(monkeypatch):
    """Test warning on invalid setting."""
    monkeypatch.setenv("QUERYCHAT_TOOL_DETAILS", "invalid")

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        result = resolve_tool_open_state("query", False)

        assert len(w) == 1
        assert "Invalid value" in str(w[0].message)
        assert result is True  # Falls back to default behavior


def test_resolve_tool_open_state_error_always_collapsed(monkeypatch):
    """Test that errors always result in collapsed state."""
    monkeypatch.setenv("QUERYCHAT_TOOL_DETAILS", "expanded")
    assert resolve_tool_open_state("query", True) is False

    monkeypatch.setenv("QUERYCHAT_TOOL_DETAILS", "collapsed")
    assert resolve_tool_open_state("query", True) is False

    monkeypatch.delenv("QUERYCHAT_TOOL_DETAILS", raising=False)
    assert resolve_tool_open_state("query", True) is False
