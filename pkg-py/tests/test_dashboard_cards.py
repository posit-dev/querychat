from __future__ import annotations

import narwhals.stable.v1 as nw
import pandas as pd
import pytest
from querychat._dashboard_cards import (
    card_html,
    format_value,
    validate_card,
)
from querychat._dashboard_state import CardSpec
from querychat._datasource import DataFrameSource


@pytest.fixture
def source() -> DataFrameSource:
    df = nw.from_native(pd.DataFrame({"mpg": [21.0, 22.8, 33.9], "cyl": [6, 4, 4]}))
    return DataFrameSource(df, "mtcars")


class TestFormatValue:
    def test_plain_format_spec(self):
        assert format_value(1234.5, ",.1f") == "1,234.5"

    def test_currency_prefix(self):
        assert format_value(1234.5, "$,.0f") == "$1,234"

    def test_empty_format_int_passthrough(self):
        assert format_value(42, "") == "42"

    def test_empty_format_float_two_decimals(self):
        assert format_value(20.0906, "") == "20.09"


class TestValidateCard:
    def test_table_with_bad_sql_raises(self, source):
        card = CardSpec(name="t", type="table", title="t", sql="SELECT nope FROM nada")
        with pytest.raises(ValueError, match=r"nope|nada|does not exist|column|table"):
            validate_card(source, card)

    def test_table_with_good_sql_passes(self, source):
        card = CardSpec(name="t", type="table", title="t", sql="SELECT * FROM mtcars")
        validate_card(source, card)  # no raise

    def test_value_box_must_be_scalar(self, source):
        card = CardSpec(
            name="v", type="value_box", title="v", sql="SELECT * FROM mtcars"
        )
        with pytest.raises(ValueError, match="single value"):
            validate_card(source, card)

    def test_markdown_always_valid(self, source):
        card = CardSpec(name="m", type="markdown", title="", text="hi")
        validate_card(source, card)


@pytest.mark.ggsql
class TestValidateCardChart:
    def test_chart_without_visualise_raises(self, source):
        card = CardSpec(
            name="c",
            type="chart",
            title="chart",
            ggsql="SELECT mpg, cyl FROM mtcars",
        )
        with pytest.raises(ValueError, match="VISUALISE"):
            validate_card(source, card)

    def test_valid_chart_passes(self, source):
        card = CardSpec(
            name="c",
            type="chart",
            title="chart",
            ggsql="SELECT mpg, cyl FROM mtcars VISUALISE mpg AS x, cyl AS y DRAW point",
        )
        validate_card(source, card)  # no raise


class TestCardHtml:
    def test_value_box_renders_formatted_scalar(self, source):
        card = CardSpec(
            name="avg",
            type="value_box",
            title="Avg MPG",
            sql="SELECT AVG(mpg) FROM mtcars",
            format=",.1f",
        )
        html = card_html(source, card)
        assert "25.9" in html
        assert "Avg MPG" in html

    def test_table_renders_rows_and_query_footer(self, source):
        card = CardSpec(
            name="tbl",
            type="table",
            title="All rows",
            sql="SELECT * FROM mtcars",
            page_size=2,
        )
        html = card_html(source, card)
        assert "<details" in html
        assert "SELECT * FROM mtcars" in html

    def test_markdown_renders(self, source):
        card = CardSpec(name="m", type="markdown", title="Notes", text="**bold** note")
        html = card_html(source, card)
        assert "<strong>bold</strong>" in html

    def test_markdown_has_no_query_footer(self, source):
        card = CardSpec(name="m", type="markdown", title="Notes", text="x")
        assert "<details" not in card_html(source, card)
