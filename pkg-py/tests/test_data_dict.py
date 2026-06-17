from pathlib import Path

import narwhals.stable.v1 as nw
import polars as pl
import pytest
from pydantic import ValidationError
from querychat._data_dict import ColumnRange, ColumnSpec, DataDict, TableSpec
from querychat._datasource import DataFrameSource
from querychat._query_executor import DataSourceExecutor


def test_from_yaml_full_spec(tmp_path: Path) -> None:
    yaml_content = """\
version: "0.1.0"
tables:
  orders:
    description: One row per order.
    columns:
      - name: order_id
        type: number(id)
        constraints: [primary_key]
        description: Unique order identifier.
        examples: [1, 2, 3]
      - name: amount
        type: number(quantity)
        range:
          min: 0
          max: 10000
      - name: status
        type: enum
        values: [pending, shipped, delivered]
relationships:
  - description: Order placed by customer.
    cardinality: many-to-one
    join: orders.customer_id = customers.id
glossary:
  churn: Customer with no orders in 90+ days.
"""
    f = tmp_path / "spec.yaml"
    f.write_text(yaml_content)
    dd = DataDict.from_yaml(f)

    assert dd.version == "0.1.0"
    assert "orders" in dd.tables
    t = dd.tables["orders"]
    assert t.description == "One row per order."
    assert len(t.columns) == 3

    col = t.columns[0]
    assert col.name == "order_id"
    assert col.description == "Unique order identifier."
    assert col.constraints == ["primary_key"]

    col = t.columns[1]
    assert col.range is not None
    assert col.range.min == 0
    assert col.range.max == 10000

    col = t.columns[2]
    assert col.values == ["pending", "shipped", "delivered"]

    assert len(dd.relationships) == 1
    assert dd.relationships[0].join == "orders.customer_id = customers.id"
    assert dd.relationships[0].cardinality == "many-to-one"
    assert dd.glossary["churn"] == "Customer with no orders in 90+ days."


def test_from_yaml_partial_spec(tmp_path: Path) -> None:
    f = tmp_path / "spec.yaml"
    f.write_text('version: "0.1.0"\ntables:\n  orders:\n    columns: []\n')
    dd = DataDict.from_yaml(f)
    assert dd.tables["orders"].description is None
    assert dd.relationships == []
    assert dd.glossary == {}


def test_from_yaml_missing_version_raises(tmp_path: Path) -> None:
    f = tmp_path / "spec.yaml"
    f.write_text("tables: {}\n")
    with pytest.raises(ValidationError):
        DataDict.from_yaml(f)


def test_from_yaml_str_path(tmp_path: Path) -> None:
    f = tmp_path / "spec.yaml"
    f.write_text('version: "0.1.0"\n')
    dd = DataDict.from_yaml(str(f))
    assert dd.version == "0.1.0"


def _make_executor(df: pl.DataFrame, table_name: str) -> DataSourceExecutor:
    source = DataFrameSource(nw.from_native(df), table_name)
    return DataSourceExecutor({table_name: source})


def test_get_table_schema_all_documented() -> None:
    dd = DataDict(
        version="0.1.0",
        tables={
            "orders": TableSpec(
                description="Order records.",
                columns=[
                    ColumnSpec(
                        name="amount",
                        description="Order total in USD.",
                        range=ColumnRange(min=0, max=500),
                    ),
                    ColumnSpec(
                        name="status",
                        values=["pending", "shipped"],
                    ),
                ],
            )
        },
    )
    df = pl.DataFrame({"amount": [10, 20], "status": ["pending", "shipped"]})
    executor = _make_executor(df, "orders")
    schema = dd.get_table_schema("orders", executor, categorical_threshold=10)
    assert "amount" in schema
    assert "Range: 0 to 500" in schema
    assert "status" in schema
    assert "pending" in schema
    assert "Description: Order total in USD." in schema


def test_get_table_schema_no_documentation() -> None:
    dd = DataDict(version="0.1.0", tables={"orders": TableSpec(columns=[])})
    df = pl.DataFrame({"amount": [10, 20, 30], "status": ["a", "b", "a"]})
    executor = _make_executor(df, "orders")
    schema = dd.get_table_schema("orders", executor, categorical_threshold=10)
    # SQL fallback should populate stats
    assert "amount" in schema
    assert "status" in schema


def test_get_table_schema_mixed_coverage() -> None:
    dd = DataDict(
        version="0.1.0",
        tables={
            "orders": TableSpec(
                columns=[
                    ColumnSpec(name="amount", range=ColumnRange(min=0, max=999)),
                ]
            )
        },
    )
    df = pl.DataFrame({"amount": [10, 20], "status": ["a", "b"]})
    executor = _make_executor(df, "orders")
    schema = dd.get_table_schema("orders", executor, categorical_threshold=10)
    assert "Range: 0 to 999" in schema  # from data_dict
    assert "status" in schema           # from SQL fallback
