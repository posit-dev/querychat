"""Tests for SnowflakeSource and semantic view functionality."""

import logging
from unittest.mock import MagicMock, patch

import pytest
from querychat._datasource import SemanticViewInfo, SnowflakeSource


class TestSemanticViewInfo:
    """Tests for SemanticViewInfo dataclass."""

    def test_creation(self):
        """Test basic creation of SemanticViewInfo."""
        info = SemanticViewInfo(name="db.schema.view", ddl="CREATE SEMANTIC VIEW...")
        assert info.name == "db.schema.view"
        assert info.ddl == "CREATE SEMANTIC VIEW..."

    def test_equality(self):
        """Test equality comparison."""
        info1 = SemanticViewInfo(name="db.schema.view", ddl="DDL")
        info2 = SemanticViewInfo(name="db.schema.view", ddl="DDL")
        info3 = SemanticViewInfo(name="db.schema.other", ddl="DDL")
        assert info1 == info2
        assert info1 != info3


class TestFormatSemanticViewsSection:
    """Tests for semantic view formatting."""

    def test_format_with_views(self):
        """Test that format produces expected markdown structure."""
        mock_engine = MagicMock()
        mock_engine.dialect.name = "snowflake"
        mock_inspector = MagicMock()
        mock_inspector.has_table.return_value = True
        mock_inspector.get_columns.return_value = [{"name": "id"}]

        with (
            patch("querychat._datasource.inspect", return_value=mock_inspector),
            patch.object(SnowflakeSource, "_discover_semantic_views", return_value=[]),
        ):
            source = SnowflakeSource(mock_engine, "test_table")
            # Manually add semantic views for formatting test
            source._semantic_views = [
                SemanticViewInfo(name="db.schema.view1", ddl="CREATE SEMANTIC VIEW v1"),
                SemanticViewInfo(name="db.schema.view2", ddl="CREATE SEMANTIC VIEW v2"),
            ]

            section = source._format_semantic_views_section()
            assert "## Snowflake Semantic Views" in section
            assert "db.schema.view1" in section
            assert "db.schema.view2" in section
            assert "CREATE SEMANTIC VIEW v1" in section
            assert "CREATE SEMANTIC VIEW v2" in section
            assert "```sql" in section


class TestSQLEscaping:
    """Tests for SQL injection prevention."""

    def test_single_quote_escaped(self):
        """Verify that names with single quotes are properly escaped."""
        mock_engine = MagicMock()
        mock_engine.dialect.name = "snowflake"
        mock_inspector = MagicMock()
        mock_inspector.has_table.return_value = True
        mock_inspector.get_columns.return_value = [{"name": "id"}]

        mock_conn = MagicMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = ["DDL result"]

        with (
            patch("querychat._datasource.inspect", return_value=mock_inspector),
            patch.object(SnowflakeSource, "_discover_semantic_views", return_value=[]),
        ):
            source = SnowflakeSource(mock_engine, "test_table")

        # Test the escaping logic directly
        with patch.object(source, "_get_connection") as mock_get_conn:
            mock_context = MagicMock()
            mock_context.__enter__ = MagicMock(return_value=mock_conn)
            mock_context.__exit__ = MagicMock(return_value=False)
            mock_get_conn.return_value = mock_context
            mock_conn.execute.return_value = mock_result

            # Call with a name containing single quotes
            source._get_semantic_view_ddl(mock_conn, "db.schema.test'view")

            # Verify the executed query has escaped quotes
            call_args = mock_conn.execute.call_args
            query_text = str(call_args[0][0])
            assert "test''view" in query_text

    def test_normal_name_unchanged(self):
        """Verify that normal names without special chars are not modified."""
        mock_engine = MagicMock()
        mock_engine.dialect.name = "snowflake"
        mock_inspector = MagicMock()
        mock_inspector.has_table.return_value = True
        mock_inspector.get_columns.return_value = [{"name": "id"}]

        mock_conn = MagicMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = ["DDL result"]

        with (
            patch("querychat._datasource.inspect", return_value=mock_inspector),
            patch.object(SnowflakeSource, "_discover_semantic_views", return_value=[]),
        ):
            source = SnowflakeSource(mock_engine, "test_table")

        mock_conn.execute.return_value = mock_result
        source._get_semantic_view_ddl(mock_conn, "db.schema.normal_view")

        call_args = mock_conn.execute.call_args
        query_text = str(call_args[0][0])
        assert "db.schema.normal_view" in query_text


class TestSnowflakeSourceDiscovery:
    """Tests for semantic view discovery with mocked connections."""

    def test_discovery_disabled(self):
        """Test that discover_semantic_views=False skips discovery."""
        mock_engine = MagicMock()
        mock_engine.dialect.name = "snowflake"
        mock_inspector = MagicMock()
        mock_inspector.has_table.return_value = True
        mock_inspector.get_columns.return_value = [{"name": "id"}]

        with patch("querychat._datasource.inspect", return_value=mock_inspector):
            # Should not call _discover_semantic_views when disabled
            source = SnowflakeSource(
                mock_engine, "test_table", discover_semantic_views=False
            )
            assert source._semantic_views == []
            assert not source.has_semantic_views

    def test_discovery_enabled_default(self):
        """Test that discovery is enabled by default."""
        mock_engine = MagicMock()
        mock_engine.dialect.name = "snowflake"
        mock_inspector = MagicMock()
        mock_inspector.has_table.return_value = True
        mock_inspector.get_columns.return_value = [{"name": "id"}]

        with (
            patch("querychat._datasource.inspect", return_value=mock_inspector),
            patch.object(
                SnowflakeSource, "_discover_semantic_views", return_value=[]
            ) as mock_discover,
        ):
            SnowflakeSource(mock_engine, "test_table")
            mock_discover.assert_called_once()

    def test_discovery_error_propagates(self):
        """Verify that discovery errors propagate (not swallowed)."""
        mock_engine = MagicMock()
        mock_engine.dialect.name = "snowflake"
        mock_inspector = MagicMock()
        mock_inspector.has_table.return_value = True
        mock_inspector.get_columns.return_value = [{"name": "id"}]

        mock_conn = MagicMock()
        mock_conn.execute.side_effect = Exception("Database connection failed")

        with (
            patch("querychat._datasource.inspect", return_value=mock_inspector),
            patch.object(mock_engine, "connect") as mock_connect,
        ):
            mock_context = MagicMock()
            mock_context.__enter__ = MagicMock(return_value=mock_conn)
            mock_context.__exit__ = MagicMock(return_value=False)
            mock_connect.return_value = mock_context

            # Error should propagate, not be swallowed
            with pytest.raises(Exception, match="Database connection failed"):
                SnowflakeSource(mock_engine, "test_table")

    def test_no_views_logs_debug(self, caplog):
        """Verify debug message when no views found."""
        mock_engine = MagicMock()
        mock_engine.dialect.name = "snowflake"
        mock_inspector = MagicMock()
        mock_inspector.has_table.return_value = True
        mock_inspector.get_columns.return_value = [{"name": "id"}]

        mock_conn = MagicMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []

        with (
            patch("querychat._datasource.inspect", return_value=mock_inspector),
            patch.object(mock_engine, "connect") as mock_connect,
            caplog.at_level(logging.DEBUG, logger="querychat._datasource"),
        ):
            mock_context = MagicMock()
            mock_context.__enter__ = MagicMock(return_value=mock_conn)
            mock_context.__exit__ = MagicMock(return_value=False)
            mock_connect.return_value = mock_context
            mock_conn.execute.return_value = mock_result

            SnowflakeSource(mock_engine, "test_table")
            assert "No semantic views found" in caplog.text


class TestSnowflakeSourceProperties:
    """Tests for SnowflakeSource properties."""

    def test_has_semantic_views_true(self):
        """Test has_semantic_views returns True when views exist."""
        mock_engine = MagicMock()
        mock_engine.dialect.name = "snowflake"
        mock_inspector = MagicMock()
        mock_inspector.has_table.return_value = True
        mock_inspector.get_columns.return_value = [{"name": "id"}]

        with (
            patch("querychat._datasource.inspect", return_value=mock_inspector),
            patch.object(SnowflakeSource, "_discover_semantic_views", return_value=[]),
        ):
            source = SnowflakeSource(mock_engine, "test_table")
            source._semantic_views = [SemanticViewInfo(name="test", ddl="DDL")]
            assert source.has_semantic_views is True

    def test_has_semantic_views_false(self):
        """Test has_semantic_views returns False when no views."""
        mock_engine = MagicMock()
        mock_engine.dialect.name = "snowflake"
        mock_inspector = MagicMock()
        mock_inspector.has_table.return_value = True
        mock_inspector.get_columns.return_value = [{"name": "id"}]

        with (
            patch("querychat._datasource.inspect", return_value=mock_inspector),
            patch.object(SnowflakeSource, "_discover_semantic_views", return_value=[]),
        ):
            source = SnowflakeSource(mock_engine, "test_table")
            assert source.has_semantic_views is False

    def test_semantic_views_property(self):
        """Test semantic_views property returns the list."""
        mock_engine = MagicMock()
        mock_engine.dialect.name = "snowflake"
        mock_inspector = MagicMock()
        mock_inspector.has_table.return_value = True
        mock_inspector.get_columns.return_value = [{"name": "id"}]

        views = [
            SemanticViewInfo(name="view1", ddl="DDL1"),
            SemanticViewInfo(name="view2", ddl="DDL2"),
        ]

        with (
            patch("querychat._datasource.inspect", return_value=mock_inspector),
            patch.object(
                SnowflakeSource, "_discover_semantic_views", return_value=views
            ),
        ):
            source = SnowflakeSource(mock_engine, "test_table")
            assert source.semantic_views == views


class TestGetSchemaWithSemanticViews:
    """Tests for get_schema with semantic views included."""

    def test_schema_includes_semantic_views(self):
        """Test that get_schema includes semantic view section."""
        mock_engine = MagicMock()
        mock_engine.dialect.name = "snowflake"
        mock_inspector = MagicMock()
        mock_inspector.has_table.return_value = True
        mock_inspector.get_columns.return_value = [{"name": "id", "type": MagicMock()}]

        views = [SemanticViewInfo(name="db.schema.metrics", ddl="CREATE SEMANTIC VIEW")]

        with (
            patch("querychat._datasource.inspect", return_value=mock_inspector),
            patch.object(
                SnowflakeSource, "_discover_semantic_views", return_value=views
            ),
        ):
            source = SnowflakeSource(mock_engine, "test_table")

            # Mock the parent get_schema
            with patch.object(
                SnowflakeSource.__bases__[0],
                "get_schema",
                return_value="Table: test_table\nColumns:\n- id",
            ):
                schema = source.get_schema(categorical_threshold=20)

                assert "Table: test_table" in schema
                assert "## Snowflake Semantic Views" in schema
                assert "db.schema.metrics" in schema

    def test_schema_without_semantic_views(self):
        """Test that get_schema works without semantic views."""
        mock_engine = MagicMock()
        mock_engine.dialect.name = "snowflake"
        mock_inspector = MagicMock()
        mock_inspector.has_table.return_value = True
        mock_inspector.get_columns.return_value = [{"name": "id", "type": MagicMock()}]

        with (
            patch("querychat._datasource.inspect", return_value=mock_inspector),
            patch.object(SnowflakeSource, "_discover_semantic_views", return_value=[]),
        ):
            source = SnowflakeSource(mock_engine, "test_table")

            with patch.object(
                SnowflakeSource.__bases__[0],
                "get_schema",
                return_value="Table: test_table\nColumns:\n- id",
            ):
                schema = source.get_schema(categorical_threshold=20)

                assert "Table: test_table" in schema
                assert "## Snowflake Semantic Views" not in schema
