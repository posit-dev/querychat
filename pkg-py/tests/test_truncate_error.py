"""Tests for truncate_error."""

from querychat._utils import truncate_error


class TestTruncateError:
    def test_short_message_unchanged(self):
        msg = "Column 'foo' not found"
        assert truncate_error(msg) == msg

    def test_empty_string(self):
        assert truncate_error("") == ""

    def test_short_message_with_blank_line_unchanged(self):
        msg = "line1\n\nline2"
        assert truncate_error(msg) == msg

    def test_truncates_at_blank_line(self):
        msg = "Something went wrong\n\n" + "x" * 500
        result = truncate_error(msg)
        assert result == "Something went wrong\n\n(error truncated)"

    def test_truncates_at_schema_dump_line(self):
        msg = "Bad property\nFailed validating 'additionalProperties' in schema[0]:\n" + "x" * 500
        result = truncate_error(msg)
        assert "Bad property" in result
        assert "(error truncated)" in result
        assert "{'additionalProperties'" not in result

    def test_hard_cap_on_long_single_line(self):
        msg = "x " * 300  # 600 chars, single line, no schema markers
        result = truncate_error(msg, max_chars=500)
        assert len(result) <= 500 + len("\n\n(error truncated)")
        assert result.endswith("\n\n(error truncated)")

    def test_hard_cap_cuts_on_word_boundary(self):
        msg = "word " * 200
        result = truncate_error(msg, max_chars=100)
        assert not result.split("\n\n(error truncated)")[0].endswith(" w")

    def test_preserves_first_line_of_altair_error(self):
        first_line = "Additional properties are not allowed ('offset' was unexpected)"
        schema_dump = "\n\nFailed validating 'additionalProperties' in schema[0]['properties']['encoding']:\n    {'additionalProperties': False,\n     'properties': {'angle': " + "x" * 10000
        msg = first_line + schema_dump
        result = truncate_error(msg)
        assert result.startswith(first_line)
        assert len(result) < 600

    def test_custom_max_chars(self):
        msg = "a" * 200
        result = truncate_error(msg, max_chars=100)
        assert len(result) <= 100 + len("\n\n(error truncated)")
