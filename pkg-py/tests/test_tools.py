"""Tests for tool functions and utilities."""

import warnings

from querychat._utils import querychat_tool_starts_open


def test_querychat_tool_starts_open_default_behavior(monkeypatch):
    """Test default behavior when no setting is provided."""
    monkeypatch.delenv("QUERYCHAT_TOOL_DETAILS", raising=False)

    assert querychat_tool_starts_open("query") is True
    assert querychat_tool_starts_open("update") is True
    assert querychat_tool_starts_open("reset") is False
    assert querychat_tool_starts_open("visualize_dashboard") is True
    assert querychat_tool_starts_open("visualize_query") is True


def test_querychat_tool_starts_open_expanded(monkeypatch):
    """Test 'expanded' setting."""
    monkeypatch.setenv("QUERYCHAT_TOOL_DETAILS", "expanded")

    assert querychat_tool_starts_open("query") is True
    assert querychat_tool_starts_open("update") is True
    assert querychat_tool_starts_open("reset") is True
    assert querychat_tool_starts_open("visualize_dashboard") is True
    assert querychat_tool_starts_open("visualize_query") is True


def test_querychat_tool_starts_open_collapsed(monkeypatch):
    """Test 'collapsed' setting."""
    monkeypatch.setenv("QUERYCHAT_TOOL_DETAILS", "collapsed")

    assert querychat_tool_starts_open("query") is False
    assert querychat_tool_starts_open("update") is False
    assert querychat_tool_starts_open("reset") is False
    assert querychat_tool_starts_open("visualize_dashboard") is False
    assert querychat_tool_starts_open("visualize_query") is False


def test_querychat_tool_starts_open_default_setting(monkeypatch):
    """Test 'default' setting."""
    monkeypatch.setenv("QUERYCHAT_TOOL_DETAILS", "default")

    assert querychat_tool_starts_open("query") is True
    assert querychat_tool_starts_open("update") is True
    assert querychat_tool_starts_open("reset") is False
    assert querychat_tool_starts_open("visualize_dashboard") is True
    assert querychat_tool_starts_open("visualize_query") is True


def test_querychat_tool_starts_open_case_insensitive(monkeypatch):
    """Test that setting is case-insensitive."""
    monkeypatch.setenv("QUERYCHAT_TOOL_DETAILS", "EXPANDED")
    assert querychat_tool_starts_open("query") is True

    monkeypatch.setenv("QUERYCHAT_TOOL_DETAILS", "Collapsed")
    assert querychat_tool_starts_open("query") is False

    monkeypatch.setenv("QUERYCHAT_TOOL_DETAILS", "DeFaUlT")
    assert querychat_tool_starts_open("query") is True


def test_querychat_tool_starts_open_invalid_setting(monkeypatch):
    """Test warning on invalid setting."""
    monkeypatch.setenv("QUERYCHAT_TOOL_DETAILS", "invalid")

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        result = querychat_tool_starts_open("query")

        assert len(w) == 1
        assert "Invalid value" in str(w[0].message)
        assert result is True  # Falls back to default behavior
