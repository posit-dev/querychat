"""Tests for Snowflake semantic view functionality."""

import logging
import os
from unittest.mock import MagicMock, patch

from querychat._snowflake import (
    IbisExecutor,
    SemanticViewInfo,
    SQLAlchemyConnectionExecutor,
    SQLAlchemyExecutor,
    discover_semantic_views,
    format_semantic_views_section,
    get_semantic_view_ddl,
)


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

    def test_format_single_view(self):
        """Test that format produces expected markdown structure for single view."""
        views = [SemanticViewInfo(name="db.schema.view1", ddl="CREATE SEMANTIC VIEW v1")]
        section = format_semantic_views_section(views)

        assert "## Snowflake Semantic Views" in section
        assert "db.schema.view1" in section
        assert "CREATE SEMANTIC VIEW v1" in section
        assert "```sql" in section
        assert "**IMPORTANT**" in section

    def test_format_multiple_views(self):
        """Test formatting with multiple views."""
        views = [
            SemanticViewInfo(name="db.schema.view1", ddl="CREATE SEMANTIC VIEW v1"),
            SemanticViewInfo(name="db.schema.view2", ddl="CREATE SEMANTIC VIEW v2"),
        ]
        section = format_semantic_views_section(views)

        assert "db.schema.view1" in section
        assert "db.schema.view2" in section
        assert "CREATE SEMANTIC VIEW v1" in section
        assert "CREATE SEMANTIC VIEW v2" in section


class TestSQLEscaping:
    """Tests for SQL injection prevention in get_semantic_view_ddl."""

    def test_single_quote_escaped(self):
        """Verify that names with single quotes are properly escaped."""
        mock_executor = MagicMock()
        mock_executor.execute_raw_sql.return_value = [{"col": "DDL result"}]

        get_semantic_view_ddl(mock_executor, "db.schema.test'view")

        # Verify the executed query has escaped quotes
        call_args = mock_executor.execute_raw_sql.call_args
        query = call_args[0][0]
        assert "test''view" in query

    def test_normal_name_unchanged(self):
        """Verify that normal names without special chars work correctly."""
        mock_executor = MagicMock()
        mock_executor.execute_raw_sql.return_value = [{"col": "DDL result"}]

        get_semantic_view_ddl(mock_executor, "db.schema.normal_view")

        call_args = mock_executor.execute_raw_sql.call_args
        query = call_args[0][0]
        assert "db.schema.normal_view" in query
        assert "''" not in query


class TestDiscoverSemanticViews:
    """Tests for the standalone discover_semantic_views function."""

    def test_discover_returns_views(self):
        """Test successful discovery of semantic views."""
        mock_executor = MagicMock()
        mock_executor.execute_raw_sql.side_effect = [
            # First call: SHOW SEMANTIC VIEWS
            [
                {"database_name": "DB", "schema_name": "SCH", "name": "VIEW1"},
                {"database_name": "DB", "schema_name": "SCH", "name": "VIEW2"},
            ],
            # Second call: GET_DDL for VIEW1
            [{"col": "DDL1"}],
            # Third call: GET_DDL for VIEW2
            [{"col": "DDL2"}],
        ]

        views = discover_semantic_views(mock_executor)

        assert len(views) == 2
        assert views[0].name == "DB.SCH.VIEW1"
        assert views[0].ddl == "DDL1"
        assert views[1].name == "DB.SCH.VIEW2"
        assert views[1].ddl == "DDL2"

    def test_discover_no_views(self, caplog):
        """Test discovery when no views exist."""
        mock_executor = MagicMock()
        mock_executor.execute_raw_sql.return_value = []

        with caplog.at_level(logging.DEBUG, logger="querychat._snowflake"):
            views = discover_semantic_views(mock_executor)

        assert views == []
        assert "No semantic views found" in caplog.text

    def test_discover_skips_null_names(self):
        """Test that rows with null names are skipped."""
        mock_executor = MagicMock()
        mock_executor.execute_raw_sql.side_effect = [
            [
                {"database_name": "DB", "schema_name": "SCH", "name": None},
                {"database_name": "DB", "schema_name": "SCH", "name": "VIEW1"},
            ],
            [{"col": "DDL1"}],
        ]

        views = discover_semantic_views(mock_executor)

        assert len(views) == 1
        assert views[0].name == "DB.SCH.VIEW1"


class TestSQLAlchemyExecutor:
    """Tests for SQLAlchemyExecutor."""

    def test_execute_raw_sql(self):
        """Test that execute_raw_sql returns list of dicts."""
        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_result = MagicMock()
        mock_result.keys.return_value = ["col1", "col2"]
        mock_result.fetchall.return_value = [("a", "b"), ("c", "d")]

        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)
        mock_conn.execute.return_value = mock_result

        executor = SQLAlchemyExecutor(mock_engine)
        result = executor.execute_raw_sql("SELECT 1")

        assert result == [{"col1": "a", "col2": "b"}, {"col1": "c", "col2": "d"}]


class TestSQLAlchemyConnectionExecutor:
    """Tests for SQLAlchemyConnectionExecutor."""

    def test_execute_raw_sql(self):
        """Test that execute_raw_sql uses existing connection."""
        mock_conn = MagicMock()
        mock_result = MagicMock()
        mock_result.keys.return_value = ["col1"]
        mock_result.fetchall.return_value = [("value",)]
        mock_conn.execute.return_value = mock_result

        executor = SQLAlchemyConnectionExecutor(mock_conn)
        result = executor.execute_raw_sql("SELECT 1")

        assert result == [{"col1": "value"}]
        mock_conn.execute.assert_called_once()


class TestIbisExecutor:
    """Tests for IbisExecutor."""

    def test_execute_raw_sql(self):
        """Test that execute_raw_sql converts ibis result to list of dicts."""
        mock_backend = MagicMock()
        mock_table = MagicMock()
        mock_df = MagicMock()
        mock_df.to_dict.return_value = [{"col1": "a"}, {"col1": "b"}]

        mock_backend.sql.return_value = mock_table
        mock_table.execute.return_value = mock_df

        executor = IbisExecutor(mock_backend)
        result = executor.execute_raw_sql("SELECT 1")

        assert result == [{"col1": "a"}, {"col1": "b"}]
        mock_backend.sql.assert_called_once_with("SELECT 1")
        mock_df.to_dict.assert_called_once_with(orient="records")


class TestSQLAlchemySourceSemanticViews:
    """Tests for SQLAlchemySource semantic view discovery."""

    def test_discovery_for_snowflake_backend(self):
        """Test that discovery is called for Snowflake backends."""
        from querychat._datasource import SQLAlchemySource

        mock_engine = MagicMock()
        mock_engine.dialect.name = "snowflake"
        mock_inspector = MagicMock()
        mock_inspector.has_table.return_value = True
        mock_inspector.get_columns.return_value = [{"name": "id"}]

        with (
            patch("querychat._datasource.inspect", return_value=mock_inspector),
            patch(
                "querychat._datasource.discover_semantic_views", return_value=[]
            ) as mock_discover,
            patch.dict(os.environ, {}, clear=False),
        ):
            # Remove the disable env var if present
            os.environ.pop("QUERYCHAT_DISABLE_SEMANTIC_VIEWS", None)
            SQLAlchemySource(mock_engine, "test_table")
            mock_discover.assert_called_once()

    def test_discovery_skipped_for_non_snowflake(self):
        """Test that discovery is skipped for non-Snowflake backends."""
        from querychat._datasource import SQLAlchemySource

        mock_engine = MagicMock()
        mock_engine.dialect.name = "postgresql"
        mock_inspector = MagicMock()
        mock_inspector.has_table.return_value = True
        mock_inspector.get_columns.return_value = [{"name": "id"}]

        with (
            patch("querychat._datasource.inspect", return_value=mock_inspector),
            patch(
                "querychat._datasource.discover_semantic_views"
            ) as mock_discover,
        ):
            source = SQLAlchemySource(mock_engine, "test_table")
            mock_discover.assert_not_called()
            assert source._semantic_views == []

    def test_discovery_disabled_via_env_var(self):
        """Test that QUERYCHAT_DISABLE_SEMANTIC_VIEWS disables discovery."""
        from querychat._datasource import SQLAlchemySource

        mock_engine = MagicMock()
        mock_engine.dialect.name = "snowflake"
        mock_inspector = MagicMock()
        mock_inspector.has_table.return_value = True
        mock_inspector.get_columns.return_value = [{"name": "id"}]

        with (
            patch("querychat._datasource.inspect", return_value=mock_inspector),
            patch(
                "querychat._datasource.discover_semantic_views"
            ) as mock_discover,
            patch.dict(os.environ, {"QUERYCHAT_DISABLE_SEMANTIC_VIEWS": "1"}),
        ):
            source = SQLAlchemySource(mock_engine, "test_table")
            mock_discover.assert_not_called()
            assert source._semantic_views == []

    def test_get_schema_includes_semantic_views(self):
        """Test that get_schema includes semantic view section."""
        from querychat._datasource import SQLAlchemySource

        views = [SemanticViewInfo(name="db.schema.metrics", ddl="CREATE SEMANTIC VIEW")]

        mock_engine = MagicMock()
        mock_engine.dialect.name = "snowflake"
        mock_inspector = MagicMock()
        mock_inspector.has_table.return_value = True
        mock_inspector.get_columns.return_value = [{"name": "id", "type": MagicMock()}]

        with (
            patch("querychat._datasource.inspect", return_value=mock_inspector),
            patch(
                "querychat._datasource.discover_semantic_views",
                return_value=views,
            ),
            patch.dict(os.environ, {}, clear=False),
        ):
            os.environ.pop("QUERYCHAT_DISABLE_SEMANTIC_VIEWS", None)
            source = SQLAlchemySource(mock_engine, "test_table")

            # Mock the stats query to avoid needing a real connection
            with patch.object(source, "_add_column_stats"):
                schema = source.get_schema(categorical_threshold=20)

            assert "Table: test_table" in schema
            assert "## Snowflake Semantic Views" in schema
            assert "db.schema.metrics" in schema

    def test_get_schema_without_semantic_views(self):
        """Test that get_schema works without semantic views."""
        from querychat._datasource import SQLAlchemySource

        mock_engine = MagicMock()
        mock_engine.dialect.name = "postgresql"
        mock_inspector = MagicMock()
        mock_inspector.has_table.return_value = True
        mock_inspector.get_columns.return_value = [{"name": "id", "type": MagicMock()}]

        with patch("querychat._datasource.inspect", return_value=mock_inspector):
            source = SQLAlchemySource(mock_engine, "test_table")

            # Mock the stats query
            with patch.object(source, "_add_column_stats"):
                schema = source.get_schema(categorical_threshold=20)

            assert "Table: test_table" in schema
            assert "## Snowflake Semantic Views" not in schema


class TestIbisSourceSemanticViews:
    """Tests for IbisSource semantic view discovery."""

    def test_discovery_for_snowflake_backend(self):
        """Test that discovery runs for Snowflake backends."""
        from ibis.backends.sql import SQLBackend
        from querychat._datasource import IbisSource

        mock_table = MagicMock()
        mock_backend = MagicMock(spec=SQLBackend)
        mock_backend.name = "snowflake"
        mock_table.get_backend.return_value = mock_backend
        mock_schema = MagicMock()
        mock_schema.items.return_value = []
        mock_schema.names = []
        mock_table.schema.return_value = mock_schema

        with (
            patch(
                "querychat._datasource.discover_semantic_views", return_value=[]
            ) as mock_discover,
            patch.dict(os.environ, {}, clear=False),
        ):
            os.environ.pop("QUERYCHAT_DISABLE_SEMANTIC_VIEWS", None)
            IbisSource(mock_table, "test")
            mock_discover.assert_called_once()

    def test_discovery_skipped_for_non_snowflake(self):
        """Test that discovery is skipped for non-Snowflake backends."""
        from ibis.backends.sql import SQLBackend
        from querychat._datasource import IbisSource

        mock_table = MagicMock()
        mock_backend = MagicMock(spec=SQLBackend)
        mock_backend.name = "postgres"
        mock_table.get_backend.return_value = mock_backend
        mock_schema = MagicMock()
        mock_schema.items.return_value = []
        mock_schema.names = []
        mock_table.schema.return_value = mock_schema

        with patch(
            "querychat._datasource.discover_semantic_views"
        ) as mock_discover:
            source = IbisSource(mock_table, "test")
            mock_discover.assert_not_called()
            assert source._semantic_views == []

    def test_discovery_disabled_via_env_var(self):
        """Test that QUERYCHAT_DISABLE_SEMANTIC_VIEWS disables discovery."""
        from ibis.backends.sql import SQLBackend
        from querychat._datasource import IbisSource

        mock_table = MagicMock()
        mock_backend = MagicMock(spec=SQLBackend)
        mock_backend.name = "snowflake"
        mock_table.get_backend.return_value = mock_backend
        mock_schema = MagicMock()
        mock_schema.items.return_value = []
        mock_schema.names = []
        mock_table.schema.return_value = mock_schema

        with (
            patch(
                "querychat._datasource.discover_semantic_views"
            ) as mock_discover,
            patch.dict(os.environ, {"QUERYCHAT_DISABLE_SEMANTIC_VIEWS": "1"}),
        ):
            source = IbisSource(mock_table, "test")
            mock_discover.assert_not_called()
            assert source._semantic_views == []

    def test_get_schema_includes_semantic_views(self):
        """Test that get_schema includes semantic view section."""
        from ibis.backends.sql import SQLBackend
        from querychat._datasource import IbisSource

        views = [SemanticViewInfo(name="db.schema.metrics", ddl="CREATE SEMANTIC VIEW")]

        mock_table = MagicMock()
        mock_backend = MagicMock(spec=SQLBackend)
        mock_backend.name = "snowflake"
        mock_table.get_backend.return_value = mock_backend
        mock_schema = MagicMock()
        mock_schema.items.return_value = [("id", MagicMock())]
        mock_schema.names = ["id"]
        mock_table.schema.return_value = mock_schema

        with (
            patch(
                "querychat._datasource.discover_semantic_views",
                return_value=views,
            ),
            patch.dict(os.environ, {}, clear=False),
        ):
            os.environ.pop("QUERYCHAT_DISABLE_SEMANTIC_VIEWS", None)
            source = IbisSource(mock_table, "test_table")

            # Mock _add_column_stats to avoid complex aggregation setup
            with patch.object(IbisSource, "_add_column_stats"):
                schema = source.get_schema(categorical_threshold=20)

            assert "Table: test_table" in schema
            assert "## Snowflake Semantic Views" in schema
            assert "db.schema.metrics" in schema
