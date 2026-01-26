"""Tests for Snowflake semantic view functionality."""

import logging
import os
from unittest.mock import MagicMock, patch

from querychat._snowflake import (
    SemanticViewInfo,
    discover_semantic_views,
    execute_raw_sql,
    format_semantic_views_section,
    get_semantic_view_ddl,
)


# Decorator to make MagicMock pass isinstance(mock, sqlalchemy.Engine)
def patch_sqlalchemy_engine(func):
    """Patch sqlalchemy.Engine so MagicMock instances pass isinstance checks."""
    return patch("querychat._snowflake.sqlalchemy.Engine", MagicMock)(func)


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

    @patch_sqlalchemy_engine
    def test_single_quote_escaped(self):
        """Verify that names with single quotes are properly escaped."""
        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_result = MagicMock()
        mock_result.keys.return_value = ["col"]
        mock_result.fetchall.return_value = [("DDL result",)]

        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)
        mock_conn.execute.return_value = mock_result

        get_semantic_view_ddl(mock_engine, "db.schema.test'view")

        # Verify the executed query has escaped quotes
        call_args = mock_conn.execute.call_args
        query_str = str(call_args[0][0])
        assert "test''view" in query_str

    @patch_sqlalchemy_engine
    def test_normal_name_unchanged(self):
        """Verify that normal names without special chars work correctly."""
        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_result = MagicMock()
        mock_result.keys.return_value = ["col"]
        mock_result.fetchall.return_value = [("DDL result",)]

        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)
        mock_conn.execute.return_value = mock_result

        get_semantic_view_ddl(mock_engine, "db.schema.normal_view")

        call_args = mock_conn.execute.call_args
        query_str = str(call_args[0][0])
        assert "db.schema.normal_view" in query_str


class TestExecuteRawSQL:
    """Tests for execute_raw_sql function."""

    @patch_sqlalchemy_engine
    def test_sqlalchemy_backend(self):
        """Test execute_raw_sql with SQLAlchemy backend."""
        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_result = MagicMock()
        mock_result.keys.return_value = ["col1", "col2"]
        mock_result.fetchall.return_value = [("a", "b"), ("c", "d")]

        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)
        mock_conn.execute.return_value = mock_result

        result = execute_raw_sql("SELECT 1", mock_engine)

        assert result == [{"col1": "a", "col2": "b"}, {"col1": "c", "col2": "d"}]

    def test_ibis_backend(self):
        """Test execute_raw_sql with Ibis backend."""
        mock_backend = MagicMock()
        mock_table = MagicMock()
        mock_df = MagicMock()
        mock_df.to_dict.return_value = [{"col1": "a"}, {"col1": "b"}]

        mock_backend.sql.return_value = mock_table
        mock_table.execute.return_value = mock_df

        result = execute_raw_sql("SELECT 1", mock_backend)

        assert result == [{"col1": "a"}, {"col1": "b"}]
        mock_backend.sql.assert_called_once_with("SELECT 1")
        mock_df.to_dict.assert_called_once_with(orient="records")


class TestDiscoverSemanticViews:
    """Tests for the discover_semantic_views function."""

    @patch_sqlalchemy_engine
    def test_discover_returns_views(self):
        """Test successful discovery of semantic views."""
        mock_engine = MagicMock()
        mock_conn = MagicMock()

        # Set up sequence of results for execute_raw_sql calls
        results = [
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
        call_count = [0]

        def mock_execute(_query):
            result = MagicMock()
            current_result = results[call_count[0]]
            call_count[0] += 1

            if isinstance(current_result, list) and current_result:
                keys = list(current_result[0].keys())
                rows = [tuple(r.values()) for r in current_result]
            else:
                keys = []
                rows = []

            result.keys.return_value = keys
            result.fetchall.return_value = rows
            return result

        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)
        mock_conn.execute.side_effect = mock_execute

        views = discover_semantic_views(mock_engine)

        assert len(views) == 2
        assert views[0].name == "DB.SCH.VIEW1"
        assert views[0].ddl == "DDL1"
        assert views[1].name == "DB.SCH.VIEW2"
        assert views[1].ddl == "DDL2"

    @patch_sqlalchemy_engine
    def test_discover_no_views(self, caplog):
        """Test discovery when no views exist."""
        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_result = MagicMock()
        mock_result.keys.return_value = []
        mock_result.fetchall.return_value = []

        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)
        mock_conn.execute.return_value = mock_result

        with caplog.at_level(logging.DEBUG, logger="querychat._snowflake"):
            views = discover_semantic_views(mock_engine)

        assert views == []
        assert "No semantic views found" in caplog.text

    def test_discover_disabled_via_env_var(self):
        """Test that QUERYCHAT_DISABLE_SEMANTIC_VIEWS disables discovery."""
        mock_engine = MagicMock()

        with patch.dict(os.environ, {"QUERYCHAT_DISABLE_SEMANTIC_VIEWS": "1"}):
            views = discover_semantic_views(mock_engine)

        assert views == []
        # Engine should not be accessed
        mock_engine.connect.assert_not_called()

    @patch_sqlalchemy_engine
    def test_discover_skips_null_names(self):
        """Test that rows with null names are skipped."""
        mock_engine = MagicMock()
        mock_conn = MagicMock()

        results = [
            # First call: SHOW SEMANTIC VIEWS with one null name
            [
                {"database_name": "DB", "schema_name": "SCH", "name": None},
                {"database_name": "DB", "schema_name": "SCH", "name": "VIEW1"},
            ],
            # Second call: GET_DDL for VIEW1 only
            [{"col": "DDL1"}],
        ]
        call_count = [0]

        def mock_execute(_query):
            result = MagicMock()
            current_result = results[call_count[0]]
            call_count[0] += 1

            if isinstance(current_result, list) and current_result:
                keys = list(current_result[0].keys())
                rows = [tuple(r.values()) for r in current_result]
            else:
                keys = []
                rows = []

            result.keys.return_value = keys
            result.fetchall.return_value = rows
            return result

        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)
        mock_conn.execute.side_effect = mock_execute

        views = discover_semantic_views(mock_engine)

        assert len(views) == 1
        assert views[0].name == "DB.SCH.VIEW1"


class TestSQLAlchemySourceSemanticViews:
    """Tests for SQLAlchemySource semantic view discovery."""

    def test_discovery_for_snowflake_backend(self):
        """Test that discovery is called for Snowflake backends in get_schema."""
        from querychat._datasource import SQLAlchemySource

        mock_engine = MagicMock()
        mock_engine.dialect.name = "snowflake"
        mock_inspector = MagicMock()
        mock_inspector.has_table.return_value = True
        mock_inspector.get_columns.return_value = [{"name": "id", "type": MagicMock()}]

        with (
            patch("querychat._datasource.inspect", return_value=mock_inspector),
            patch(
                "querychat._datasource.discover_semantic_views", return_value=[]
            ) as mock_discover,
        ):
            source = SQLAlchemySource(mock_engine, "test_table")
            mock_discover.assert_not_called()

            with patch.object(source, "_add_column_stats"):
                source.get_schema(categorical_threshold=20)

            mock_discover.assert_called_once_with(mock_engine)

    def test_discovery_skipped_for_non_snowflake(self):
        """Test that discovery is skipped for non-Snowflake backends."""
        from querychat._datasource import SQLAlchemySource

        mock_engine = MagicMock()
        mock_engine.dialect.name = "postgresql"
        mock_inspector = MagicMock()
        mock_inspector.has_table.return_value = True
        mock_inspector.get_columns.return_value = [{"name": "id", "type": MagicMock()}]

        with (
            patch("querychat._datasource.inspect", return_value=mock_inspector),
            patch(
                "querychat._datasource.discover_semantic_views"
            ) as mock_discover,
        ):
            source = SQLAlchemySource(mock_engine, "test_table")

            with patch.object(source, "_add_column_stats"):
                source.get_schema(categorical_threshold=20)

            mock_discover.assert_not_called()

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
        ):
            source = SQLAlchemySource(mock_engine, "test_table")

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

            with patch.object(source, "_add_column_stats"):
                schema = source.get_schema(categorical_threshold=20)

            assert "Table: test_table" in schema
            assert "## Snowflake Semantic Views" not in schema


class TestIbisSourceSemanticViews:
    """Tests for IbisSource semantic view discovery."""

    def test_discovery_for_snowflake_backend(self):
        """Test that discovery runs for Snowflake backends in get_schema."""
        from ibis.backends.sql import SQLBackend
        from querychat._datasource import IbisSource

        mock_table = MagicMock()
        mock_backend = MagicMock(spec=SQLBackend)
        mock_backend.name = "snowflake"
        mock_table.get_backend.return_value = mock_backend
        mock_schema = MagicMock()
        mock_dtype = MagicMock()
        mock_dtype.is_numeric.return_value = True
        mock_dtype.is_integer.return_value = True
        mock_schema.items.return_value = [("id", mock_dtype)]
        mock_schema.names = ["id"]
        mock_table.schema.return_value = mock_schema

        with patch(
            "querychat._datasource.discover_semantic_views", return_value=[]
        ) as mock_discover:
            source = IbisSource(mock_table, "test")
            mock_discover.assert_not_called()

            with patch.object(IbisSource, "_add_column_stats"):
                source.get_schema(categorical_threshold=20)

            mock_discover.assert_called_once_with(mock_backend)

    def test_discovery_skipped_for_non_snowflake(self):
        """Test that discovery is skipped for non-Snowflake backends."""
        from ibis.backends.sql import SQLBackend
        from querychat._datasource import IbisSource

        mock_table = MagicMock()
        mock_backend = MagicMock(spec=SQLBackend)
        mock_backend.name = "postgres"
        mock_table.get_backend.return_value = mock_backend
        mock_schema = MagicMock()
        mock_dtype = MagicMock()
        mock_dtype.is_numeric.return_value = True
        mock_dtype.is_integer.return_value = True
        mock_schema.items.return_value = [("id", mock_dtype)]
        mock_schema.names = ["id"]
        mock_table.schema.return_value = mock_schema

        with patch(
            "querychat._datasource.discover_semantic_views"
        ) as mock_discover:
            source = IbisSource(mock_table, "test")

            with patch.object(IbisSource, "_add_column_stats"):
                source.get_schema(categorical_threshold=20)

            mock_discover.assert_not_called()

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
        mock_dtype = MagicMock()
        mock_dtype.is_numeric.return_value = True
        mock_dtype.is_integer.return_value = True
        mock_schema.items.return_value = [("id", mock_dtype)]
        mock_schema.names = ["id"]
        mock_table.schema.return_value = mock_schema

        with patch(
            "querychat._datasource.discover_semantic_views",
            return_value=views,
        ):
            source = IbisSource(mock_table, "test_table")

            with patch.object(IbisSource, "_add_column_stats"):
                schema = source.get_schema(categorical_threshold=20)

            assert "Table: test_table" in schema
            assert "## Snowflake Semantic Views" in schema
            assert "db.schema.metrics" in schema
