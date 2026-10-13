"""Tests for ggsql integration helpers."""

import ggsql
import narwhals.stable.v1 as nw
import pandas as pd
import polars as pl
import pyarrow as pa
import pytest
from querychat._datasource import (
    DataFrameSource,
    IbisSource,
    PolarsLazySource,
    SQLAlchemySource,
)
from querychat._query_executor import (
    DataSourceExecutor,
    DuckDBExecutor,
    PolarsSQLExecutor,
)
from querychat._viz_altair_widget import AltairWidget
from querychat._viz_ggsql import ExecutorReader


def make_reader(source) -> ggsql.CachingReader:
    """Create a CachingReader over an ExecutorReader, as the viz tool does."""
    return ggsql.CachingReader(ExecutorReader(source))


class TestGgsqlValidate:
    """Tests for ggsql.validate() usage (split SQL and VISUALISE)."""

    def test_accepts_from_before_visualise(self):
        query = "FROM data VISUALISE x, y DRAW point"
        validated = ggsql.validate(query)
        assert validated.valid()
        assert validated.has_visual()
        assert validated.sql() == "SELECT * FROM data"
        assert validated.visual() == "VISUALISE x, y DRAW point"

    def test_accepts_from_before_visualise_for_test_data(self):
        query = "FROM test_data VISUALISE x, y DRAW point"
        validated = ggsql.validate(query)
        assert validated.valid()
        assert validated.has_visual()
        assert validated.sql() == "SELECT * FROM test_data"
        assert validated.visual() == "VISUALISE x, y DRAW point"

    def test_reports_upstream_error_for_expression_in_visualise(self):
        query = (
            "SELECT CAST(x AS DOUBLE) AS x2 "
            "FROM data "
            "VISUALISE CAST(x2 AS DOUBLE) AS x "
            "DRAW point"
        )
        validated = ggsql.validate(query)
        assert not validated.valid()
        messages = [error["message"] for error in validated.errors()]
        assert any(
            "VISUALISE clause was not recognized" in message
            and "column names only" in message
            for message in messages
        )

    def test_splits_query_with_visualise(self):
        query = "SELECT x, y FROM data VISUALISE x, y DRAW point"
        validated = ggsql.validate(query)
        assert validated.sql() == "SELECT x, y FROM data"
        assert validated.visual() == "VISUALISE x, y DRAW point"
        assert validated.has_visual()

    def test_returns_empty_viz_without_visualise(self):
        query = "SELECT x, y FROM data"
        validated = ggsql.validate(query)
        assert validated.sql() == "SELECT x, y FROM data"
        assert validated.visual() == ""
        assert not validated.has_visual()

    def test_handles_complex_query(self):
        query = """
        SELECT date, SUM(revenue) as total
        FROM sales
        GROUP BY date
        VISUALISE date AS x, total AS y
        DRAW line
        LABEL title => 'Revenue Over Time'
        """
        validated = ggsql.validate(query)
        assert "SELECT date, SUM(revenue)" in validated.sql()
        assert "GROUP BY date" in validated.sql()
        assert "VISUALISE date AS x" in validated.visual()
        assert "LABEL title" in validated.visual()


@pytest.fixture(autouse=True)
def _allow_widget_outside_session(monkeypatch):
    """Allow JupyterChart (an ipywidget) to be constructed without a Shiny session."""
    from ipywidgets.widgets.widget import Widget

    monkeypatch.setattr(Widget, "_widget_construction_callback", lambda _w: None)


class TestAltairWidget:
    @pytest.mark.ggsql
    def test_produces_jupyter_chart(self):
        import altair as alt
        import ggsql

        reader = ggsql.DuckDBReader("duckdb://memory")
        df = pl.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]})
        reader.register("data", df)
        spec = reader.execute("SELECT * FROM data VISUALISE x, y DRAW point")
        altair_widget = AltairWidget.from_ggsql(spec)
        assert isinstance(altair_widget.widget, alt.JupyterChart)
        result = altair_widget.widget.chart.to_dict()
        assert "$schema" in result
        assert "vega-lite" in result["$schema"]


class TestExecuteGgsql:
    @pytest.mark.ggsql
    def test_full_pipeline(self):
        nw_df = nw.from_native(pl.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]}))
        ds = DataFrameSource(nw_df, "test_data")
        query = "SELECT * FROM test_data VISUALISE x, y DRAW point"
        spec = make_reader(ds).execute(query)
        altair_widget = AltairWidget.from_ggsql(spec)
        result = altair_widget.widget.chart.to_dict()
        assert "$schema" in result

    @pytest.mark.ggsql
    def test_with_filtered_query(self):
        nw_df = nw.from_native(
            pl.DataFrame({"x": [1, 2, 3, 4, 5], "y": [10, 20, 30, 40, 50]})
        )
        ds = DataFrameSource(nw_df, "test_data")
        query = "SELECT * FROM test_data WHERE x > 2 VISUALISE x, y DRAW point"
        spec = make_reader(ds).execute(query)
        assert spec.metadata()["rows"] == 3

    @pytest.mark.ggsql
    def test_spec_has_visual(self):
        nw_df = nw.from_native(pl.DataFrame({"x": [1, 2], "y": [3, 4]}))
        ds = DataFrameSource(nw_df, "test_data")
        query = "SELECT * FROM test_data VISUALISE x, y DRAW point"
        spec = make_reader(ds).execute(query)
        assert "VISUALISE" in spec.visual()

    @pytest.mark.ggsql
    def test_visualise_from_path(self):
        nw_df = nw.from_native(pl.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]}))
        ds = DataFrameSource(nw_df, "test_data")
        query = "VISUALISE x, y FROM test_data DRAW point"
        spec = make_reader(ds).execute(query)
        assert spec.metadata()["rows"] == 3
        assert "VISUALISE" in spec.visual()

    @pytest.mark.ggsql
    def test_with_pandas_dataframe(self):
        import pandas as pd

        nw_df = nw.from_native(pd.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]}))
        ds = DataFrameSource(nw_df, "test_data")
        query = "SELECT * FROM test_data VISUALISE x, y DRAW point"
        spec = make_reader(ds).execute(query)
        altair_widget = AltairWidget.from_ggsql(spec)
        result = altair_widget.widget.chart.to_dict()
        assert "$schema" in result

    @pytest.mark.ggsql
    def test_supports_uppercase_column_references_without_renaming(self):
        nw_df = nw.from_native(
            pl.DataFrame(
                {
                    "ROOM_TYPE": ["Entire home", "Private room"],
                    "listings": [10, 20],
                }
            )
        )
        ds = DataFrameSource(nw_df, "upper_table")
        query = (
            "SELECT ROOM_TYPE, listings FROM upper_table "
            "VISUALISE ROOM_TYPE AS x, listings AS y "
            "DRAW bar"
        )
        spec = make_reader(ds).execute(query)
        assert "VISUALISE" in spec.visual()

    @pytest.mark.ggsql
    def test_supports_layer_level_from_sources(self):
        nw_df = nw.from_native(
            pl.DataFrame(
                {
                    "date": ["2024-01", "2024-01", "2024-02", "2024-02"],
                    "region": ["north", "south", "north", "south"],
                    "amount": [10, 20, 30, 40],
                }
            )
        )
        ds = DataFrameSource(nw_df, "sales")
        query = """
        WITH summary AS (
            SELECT region, SUM(amount) AS total
            FROM sales
            GROUP BY region
        )
        SELECT *
        FROM sales
        VISUALISE date AS x, amount AS y
        DRAW line
        DRAW bar MAPPING region AS x, total AS y FROM summary
        """

        # Previously raised "Layer-specific sources are not currently
        # supported"; CachingReader stages each layer source through its
        # cache, so the query now runs end to end.
        spec = make_reader(ds).execute(query)
        assert spec is not None
        assert "VISUALISE" in spec.visual()

    @pytest.mark.ggsql
    def test_supports_single_relation_raw_plus_summary_overlay(self):
        nw_df = nw.from_native(
            pl.DataFrame(
                {
                    "x": [1, 1, 2, 2],
                    "y": [10, 20, 30, 40],
                    "category": ["a", "b", "a", "b"],
                }
            )
        )
        ds = DataFrameSource(nw_df, "sales")
        query = """
        WITH raw AS (
            SELECT
                x,
                y,
                category,
                'raw' AS layer_type
            FROM sales
        ),
        summary AS (
            SELECT
                x,
                AVG(y) AS y,
                category,
                'summary' AS layer_type
            FROM sales
            GROUP BY x, category
        ),
        combined AS (
            SELECT * FROM raw
            UNION ALL
            SELECT * FROM summary
        )
        SELECT *
        FROM combined
        VISUALISE x AS x, y AS y
        DRAW point MAPPING category AS color FILTER layer_type = 'raw'
        DRAW line MAPPING category AS color FILTER layer_type = 'summary'
        """

        spec = make_reader(ds).execute(query)
        assert spec.metadata()["rows"] == 4
        assert "VISUALISE" in spec.visual()


class TestExecutorReaderResultTypes:
    """
    ExecutorReader.execute_sql normalizes every execute_query() result type
    (the QueryResult union) to a pyarrow Table, without requiring polars.
    """

    @staticmethod
    def check(executor):
        tbl = ExecutorReader(executor).execute_sql("SELECT x, y FROM t")
        assert isinstance(tbl, pa.Table)
        assert tbl.schema.names == ["x", "y"]
        assert tbl.num_rows == 2

    @pytest.fixture(
        params=[
            pd.DataFrame({"x": [1, 2], "y": [3, 4]}),
            pl.DataFrame({"x": [1, 2], "y": [3, 4]}),
            pa.table({"x": [1, 2], "y": [3, 4]}),
        ],
        ids=["pandas", "polars", "pyarrow"],
    )
    def frame(self, request):
        return request.param

    def test_dataframe_source_backends(self, frame):
        self.check(DataFrameSource(nw.from_native(frame), "t"))

    def test_duckdb_executor_backends(self, frame):
        source = DataFrameSource(nw.from_native(frame), "t")
        self.check(DuckDBExecutor({"t": source}))

    def test_polars_lazy_source(self):
        lf = nw.from_native(pl.LazyFrame({"x": [1, 2], "y": [3, 4]}))
        self.check(PolarsLazySource(lf, "t"))

    def test_polars_sql_executor(self):
        lf = nw.from_native(pl.LazyFrame({"x": [1, 2], "y": [3, 4]}))
        self.check(PolarsSQLExecutor({"t": PolarsLazySource(lf, "t")}))

    def test_sqlalchemy_source(self):
        sqlalchemy = pytest.importorskip("sqlalchemy")
        eng = sqlalchemy.create_engine("sqlite://")
        pd.DataFrame({"x": [1, 2], "y": [3, 4]}).to_sql("t", eng, index=False)
        self.check(SQLAlchemySource(eng, "t"))

    def test_ibis_source(self):
        ibis = pytest.importorskip("ibis")
        con = ibis.duckdb.connect()
        con.create_table("t", pd.DataFrame({"x": [1, 2], "y": [3, 4]}))
        self.check(IbisSource(con.table("t"), "t"))

    def test_datasource_executor_delegation(self):
        sqlalchemy = pytest.importorskip("sqlalchemy")
        eng = sqlalchemy.create_engine("sqlite://")
        pd.DataFrame({"x": [1, 2], "y": [3, 4]}).to_sql("t", eng, index=False)
        self.check(DataSourceExecutor({"t": SQLAlchemySource(eng, "t")}))

    def test_register_unregister_warn(self):
        # register/unregister are no-ops by design (CachingReader owns all
        # writes); they warn loudly in case a future ggsql routes writes
        # to the primary reader, which would otherwise silently drop them.
        ds = DataFrameSource(nw.from_native(pl.DataFrame({"x": [1]})), "t")
        reader = ExecutorReader(ds)
        with pytest.warns(UserWarning, match="no-op by design"):
            reader.register("t", None, replace=False)
        with pytest.warns(UserWarning, match="no-op by design"):
            reader.unregister("t")

    def test_empty_result(self):
        ds = DataFrameSource(nw.from_native(pl.DataFrame({"x": [1, 2]})), "t")
        tbl = ExecutorReader(ds).execute_sql("SELECT * FROM t WHERE x > 100")
        assert isinstance(tbl, pa.Table)
        assert tbl.num_rows == 0

    def test_null_column(self):
        ds = DataFrameSource(nw.from_native(pl.DataFrame({"x": [1, 2]})), "t")
        tbl = ExecutorReader(ds).execute_sql("SELECT NULL AS n FROM t")
        assert tbl.schema.names == ["n"]
        assert tbl.num_rows == 2

    def test_duplicate_column_names_raise(self):
        # Known limitation (pre-existing): narwhals requires unique column
        # names, so a JOIN with overlapping names through a DBAPI-backed
        # source fails conversion regardless of the arrow/polars cast.
        # (DuckDB-family sources auto-mangle duplicates to x, x_1, so this
        # only bites SQLAlchemy/Ibis-style sources.)
        import sqlalchemy

        eng = sqlalchemy.create_engine("sqlite://")
        pd.DataFrame({"id": [1, 2], "v": [10, 20]}).to_sql("a", eng, index=False)
        pd.DataFrame({"id": [1, 2], "w": [30, 40]}).to_sql("b", eng, index=False)
        src = SQLAlchemySource(eng, "a")
        with pytest.raises(Exception, match=r"[Uu]nique column names"):
            ExecutorReader(src).execute_sql("SELECT * FROM a JOIN b ON a.id = b.id")


class TestCachingBehavior:
    """CachingReader shares memoized source reads across viz executions."""

    @pytest.mark.ggsql
    def test_identical_queries_share_source_reads(self, monkeypatch):
        nw_df = nw.from_native(pl.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]}))
        ds = DataFrameSource(nw_df, "test_data")

        calls = 0
        original = ds.execute_query

        def counting(query):
            nonlocal calls
            calls += 1
            return original(query)

        monkeypatch.setattr(ds, "execute_query", counting)

        query = "SELECT * FROM test_data VISUALISE x, y DRAW point"
        reader = make_reader(ds)
        reader.execute(query)
        reader.execute(query)
        assert calls == 1

    @pytest.mark.ggsql
    def test_independent_readers_do_not_share_memo(self, monkeypatch):
        """Readers own their caches; nothing is shared implicitly."""
        nw_df = nw.from_native(pl.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]}))
        ds = DataFrameSource(nw_df, "test_data")

        calls = 0
        original = ds.execute_query

        def counting(query):
            nonlocal calls
            calls += 1
            return original(query)

        monkeypatch.setattr(ds, "execute_query", counting)

        query = "SELECT * FROM test_data VISUALISE x, y DRAW point"
        make_reader(ds).execute(query)
        make_reader(ds).execute(query)
        assert calls == 2


class TestRestoreVizWidgets:
    """
    Bookmark restore executes through a CachingReader (PR #321 follow-up).

    Regression guard: an earlier draft passed the executor itself where a
    reader was expected, so every widget silently failed to restore (the
    AttributeError was swallowed by restore_viz_widgets' except Exception).
    """

    @pytest.fixture
    def register_spy(self, monkeypatch):
        """Stub out the two places restore_viz_widgets needs a Shiny session."""
        import ipywidgets
        import shinywidgets

        registered = []
        monkeypatch.setattr(
            shinywidgets,
            "register_widget",
            lambda widget_id, widget: registered.append(widget_id),
        )
        # shinywidgets hooks ipywidgets construction (Widget.on_widget_constructed)
        # and requires an active session; unhook so widgets build session-free.
        monkeypatch.setattr(ipywidgets.Widget, "_widget_construction_callback", None)
        return registered

    @pytest.mark.ggsql
    def test_restores_and_registers_widgets(self, register_spy):
        from querychat._shiny_module import restore_viz_widgets

        nw_df = nw.from_native(pl.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]}))
        ds = DataFrameSource(nw_df, "test_data")
        entries = [
            {
                "widget_id": "w1",
                "ggsql": "SELECT * FROM test_data VISUALISE x, y DRAW point",
            },
            {
                "widget_id": "w2",
                "ggsql": "SELECT * FROM test_data WHERE x > 1 VISUALISE x, y DRAW point",
            },
        ]

        restored = restore_viz_widgets(ds, entries)

        assert [e["widget_id"] for e in restored] == ["w1", "w2"]
        assert register_spy == ["w1", "w2"]

    @pytest.mark.ggsql
    def test_shared_base_reads_are_memoized(self, monkeypatch, register_spy):
        """One reader per restore pass: identical queries share one source read."""
        from querychat._shiny_module import restore_viz_widgets

        nw_df = nw.from_native(pl.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]}))
        ds = DataFrameSource(nw_df, "test_data")

        calls = 0
        original = ds.execute_query

        def counting(query):
            nonlocal calls
            calls += 1
            return original(query)

        monkeypatch.setattr(ds, "execute_query", counting)

        query = "SELECT * FROM test_data VISUALISE x, y DRAW point"
        entries = [
            {"widget_id": "w1", "ggsql": query},
            {"widget_id": "w2", "ggsql": query},
        ]

        restored = restore_viz_widgets(ds, entries)

        assert len(restored) == 2
        assert calls == 1

    @pytest.mark.ggsql
    def test_invalid_entries_are_skipped_with_warning(self, register_spy):
        from querychat._shiny_module import restore_viz_widgets

        nw_df = nw.from_native(pl.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]}))
        ds = DataFrameSource(nw_df, "test_data")
        entries = [
            {
                "widget_id": "bad",
                "ggsql": "SELECT * FROM nope VISUALISE x, y DRAW point",
            },
            {
                "widget_id": "good",
                "ggsql": "SELECT * FROM test_data VISUALISE x, y DRAW point",
            },
        ]

        with pytest.warns(UserWarning, match="Failed to restore"):
            restored = restore_viz_widgets(ds, entries)

        assert [e["widget_id"] for e in restored] == ["good"]
        assert register_spy == ["good"]
