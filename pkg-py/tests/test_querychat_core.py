"""Tests for querychat._querychat_core formatting helpers."""

import pytest
from chatlas import ContentToolResult
from shinychat.types import ToolResultDisplay

from querychat._querychat_core import format_chunk, format_tool_result


def test_format_tool_result_without_display_returns_value():
    result = ContentToolResult(value="schema text")
    assert format_tool_result(result) == "schema text"


def test_format_tool_result_with_markdown_display_returns_markdown():
    result = ContentToolResult(
        value="schema text",
        extra={"display": ToolResultDisplay(markdown="**schema**")},
    )
    assert format_tool_result(result) == "**schema**"


def test_format_tool_result_with_none_markdown_falls_back_to_value():
    # ToolResultDisplay.markdown defaults to None; the display's mere
    # existence must not shadow the result value.
    result = ContentToolResult(
        value="schema text",
        extra={"display": ToolResultDisplay(label="titanic")},
    )
    assert format_tool_result(result) == "schema text"


def test_format_tool_result_without_value_returns_empty_string():
    result = ContentToolResult(
        value=None,
        extra={"display": ToolResultDisplay(label="titanic")},
    )
    assert format_tool_result(result) == ""


def test_format_chunk_wraps_tool_result_without_crashing():
    result = ContentToolResult(
        value="schema text",
        extra={"display": ToolResultDisplay(label="titanic")},
    )
    assert format_chunk(result) == "\n\nschema text\n\n"


def test_format_chunk_rejects_unknown_type():
    with pytest.raises(ValueError, match="Unknown chunk type"):
        format_chunk(42)  # type: ignore[arg-type]
