"""Unit tests for QueryChatSystemPrompt class."""

import tempfile
from pathlib import Path

import narwhals.stable.v1 as nw
import pandas as pd
import pytest
from querychat._datasource import DataFrameSource
from querychat._system_prompt import QueryChatSystemPrompt


@pytest.fixture
def sample_data_source():
    """Create a sample DataFrameSource for testing."""
    df = nw.from_native(
        pd.DataFrame(
            {
                "id": [1, 2, 3],
                "name": ["Alice", "Bob", "Charlie"],
                "age": [25, 30, 35],
            }
        )
    )
    return DataFrameSource(df, "test_table")


@pytest.fixture
def sample_prompt_template():
    """Create a sample prompt template for testing."""
    return """Database Type: {{db_type}}
Schema: {{schema}}
{{#data_description}}Data: {{data_description}}{{/data_description}}
{{#extra_instructions}}Instructions: {{extra_instructions}}{{/extra_instructions}}
{{#has_tool_update}}UPDATE TOOL ENABLED{{/has_tool_update}}
{{#has_tool_query}}QUERY TOOL ENABLED{{/has_tool_query}}
{{#include_query_guidelines}}QUERY GUIDELINES{{/include_query_guidelines}}
"""


class TestQueryChatSystemPromptInit:
    """Tests for QueryChatSystemPrompt initialization."""

    def test_init_with_string_template(
        self, sample_data_source, sample_prompt_template
    ):
        """Test initialization with string template."""
        prompt = QueryChatSystemPrompt(
            prompt_template=sample_prompt_template,
            data_source=sample_data_source,
        )

        assert prompt.template == sample_prompt_template
        assert prompt.data_source == sample_data_source
        assert prompt.data_description is None
        assert prompt.extra_instructions is None
        assert prompt.schema is not None
        assert prompt.categorical_threshold == 10

    def test_init_with_path_template(self, sample_data_source):
        """Test initialization with Path template."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("Template from file: {{db_type}}")
            template_path = Path(f.name)

        try:
            prompt = QueryChatSystemPrompt(
                prompt_template=template_path,
                data_source=sample_data_source,
            )

            assert prompt.template == "Template from file: {{db_type}}"
        finally:
            template_path.unlink()

    def test_init_with_string_data_description(
        self, sample_data_source, sample_prompt_template
    ):
        """Test initialization with string data description."""
        prompt = QueryChatSystemPrompt(
            prompt_template=sample_prompt_template,
            data_source=sample_data_source,
            data_description="This is test data",
        )

        assert prompt.data_description == "This is test data"

    def test_init_with_path_data_description(
        self, sample_data_source, sample_prompt_template
    ):
        """Test initialization with Path data description."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Data description from file")
            desc_path = Path(f.name)

        try:
            prompt = QueryChatSystemPrompt(
                prompt_template=sample_prompt_template,
                data_source=sample_data_source,
                data_description=desc_path,
            )

            assert prompt.data_description == "Data description from file"
        finally:
            desc_path.unlink()

    def test_init_with_string_extra_instructions(
        self, sample_data_source, sample_prompt_template
    ):
        """Test initialization with string extra instructions."""
        prompt = QueryChatSystemPrompt(
            prompt_template=sample_prompt_template,
            data_source=sample_data_source,
            extra_instructions="Be concise",
        )

        assert prompt.extra_instructions == "Be concise"

    def test_init_with_path_extra_instructions(
        self, sample_data_source, sample_prompt_template
    ):
        """Test initialization with Path extra instructions."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Instructions from file")
            instr_path = Path(f.name)

        try:
            prompt = QueryChatSystemPrompt(
                prompt_template=sample_prompt_template,
                data_source=sample_data_source,
                extra_instructions=instr_path,
            )

            assert prompt.extra_instructions == "Instructions from file"
        finally:
            instr_path.unlink()

    def test_init_with_custom_categorical_threshold(
        self, sample_data_source, sample_prompt_template
    ):
        """Test initialization with custom categorical threshold."""
        prompt = QueryChatSystemPrompt(
            prompt_template=sample_prompt_template,
            data_source=sample_data_source,
            categorical_threshold=15,
        )

        assert prompt.categorical_threshold == 15


class TestQueryChatSystemPromptRender:
    """Tests for QueryChatSystemPrompt.render() method."""

    def test_render_with_both_tools(self, sample_data_source, sample_prompt_template):
        """Test rendering with both tools enabled."""
        prompt = QueryChatSystemPrompt(
            prompt_template=sample_prompt_template,
            data_source=sample_data_source,
        )

        rendered = prompt.render(tools=("update", "query"))

        assert "UPDATE TOOL ENABLED" in rendered
        assert "QUERY TOOL ENABLED" in rendered
        assert "QUERY GUIDELINES" in rendered
        assert "Database Type:" in rendered
        assert "Schema:" in rendered

    def test_render_with_query_only(self, sample_data_source, sample_prompt_template):
        """Test rendering with only query tool enabled."""
        prompt = QueryChatSystemPrompt(
            prompt_template=sample_prompt_template,
            data_source=sample_data_source,
        )

        rendered = prompt.render(tools=("query",))

        assert "UPDATE TOOL ENABLED" not in rendered
        assert "QUERY TOOL ENABLED" in rendered
        assert "QUERY GUIDELINES" in rendered

    def test_render_with_update_only(self, sample_data_source, sample_prompt_template):
        """Test rendering with only update tool enabled."""
        prompt = QueryChatSystemPrompt(
            prompt_template=sample_prompt_template,
            data_source=sample_data_source,
        )

        rendered = prompt.render(tools=("update",))

        assert "UPDATE TOOL ENABLED" in rendered
        assert "QUERY TOOL ENABLED" not in rendered
        assert "QUERY GUIDELINES" in rendered

    def test_render_with_no_tools(self, sample_data_source, sample_prompt_template):
        """Test rendering with no tools enabled."""
        prompt = QueryChatSystemPrompt(
            prompt_template=sample_prompt_template,
            data_source=sample_data_source,
        )

        rendered = prompt.render(tools=None)

        assert "UPDATE TOOL ENABLED" not in rendered
        assert "QUERY TOOL ENABLED" not in rendered
        assert "QUERY GUIDELINES" not in rendered

    def test_render_includes_data_description(
        self, sample_data_source, sample_prompt_template
    ):
        """Test that rendering includes data description when provided."""
        prompt = QueryChatSystemPrompt(
            prompt_template=sample_prompt_template,
            data_source=sample_data_source,
            data_description="Test data description",
        )

        rendered = prompt.render(tools=("query",))

        assert "Data: Test data description" in rendered

    def test_render_includes_extra_instructions(
        self, sample_data_source, sample_prompt_template
    ):
        """Test that rendering includes extra instructions when provided."""
        prompt = QueryChatSystemPrompt(
            prompt_template=sample_prompt_template,
            data_source=sample_data_source,
            extra_instructions="Be very concise",
        )

        rendered = prompt.render(tools=("query",))

        assert "Instructions: Be very concise" in rendered

    def test_render_includes_schema(self, sample_data_source, sample_prompt_template):
        """Test that rendering includes schema information."""
        prompt = QueryChatSystemPrompt(
            prompt_template=sample_prompt_template,
            data_source=sample_data_source,
        )

        rendered = prompt.render(tools=("query",))

        assert "Schema:" in rendered
        # Schema should contain table and column information
        # Note: chevron escapes HTML entities, so we check for key schema content
        assert "test_table" in rendered
        assert "id" in rendered
        assert "name" in rendered
        assert "age" in rendered

    def test_render_includes_db_type(self, sample_data_source, sample_prompt_template):
        """Test that rendering includes database type."""
        prompt = QueryChatSystemPrompt(
            prompt_template=sample_prompt_template,
            data_source=sample_data_source,
        )

        rendered = prompt.render(tools=("query",))

        assert "Database Type:" in rendered
        assert sample_data_source.get_db_type() in rendered


