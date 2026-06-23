from pathlib import Path

import narwhals.stable.v1 as nw
import polars as pl
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


def test_from_yaml_str_path(tmp_path: Path) -> None:
    f = tmp_path / "spec.yaml"
    f.write_text('version: "0.1.0"\n')
    dd = DataDict.from_yaml(str(f))
    assert dd.tables == {}


def test_name_and_description_are_optional() -> None:
    dd = DataDict()
    assert dd.name is None
    assert dd.description is None


def test_from_yaml_derives_name_from_file_stem(tmp_path: Path) -> None:
    f = tmp_path / "my_schema.yaml"
    f.write_text('version: "0.1.0"\n')
    dd = DataDict.from_yaml(f)
    assert dd.name == "my_schema"


def test_from_yaml_explicit_name_overrides_stem(tmp_path: Path) -> None:
    f = tmp_path / "file_name.yaml"
    f.write_text("name: custom_name\n")
    dd = DataDict.from_yaml(f)
    assert dd.name == "custom_name"


def test_from_yaml_loads_description(tmp_path: Path) -> None:
    f = tmp_path / "spec.yaml"
    f.write_text('description: "Sales data"\n')
    dd = DataDict.from_yaml(f)
    assert dd.description == "Sales data"


def test_from_yaml_description_defaults_to_none(tmp_path: Path) -> None:
    f = tmp_path / "spec.yaml"
    f.write_text('version: "0.1.0"\n')
    dd = DataDict.from_yaml(f)
    assert dd.description is None


def _make_executor(df: pl.DataFrame, table_name: str) -> DataSourceExecutor:
    source = DataFrameSource(nw.from_native(df), table_name)
    return DataSourceExecutor({table_name: source})


def test_get_table_schema_all_documented() -> None:
    dd = DataDict(
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
    cols = dd.get_table_schema("orders", executor, categorical_threshold=10)
    col_map = {c.name: c for c in cols}
    assert "amount" in col_map
    assert col_map["amount"].min_val == 0
    assert col_map["amount"].max_val == 500
    assert col_map["amount"].description == "Order total in USD."
    assert "status" in col_map
    assert "pending" in col_map["status"].categories


def test_get_table_schema_no_documentation() -> None:
    dd = DataDict(tables={"orders": TableSpec(columns=[])})
    df = pl.DataFrame({"amount": [10, 20, 30], "status": ["a", "b", "a"]})
    executor = _make_executor(df, "orders")
    cols = dd.get_table_schema("orders", executor, categorical_threshold=10)
    col_names = [c.name for c in cols]
    # SQL fallback should populate stats
    assert "amount" in col_names
    assert "status" in col_names


def test_get_table_schema_mixed_coverage() -> None:
    dd = DataDict(
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
    cols = dd.get_table_schema("orders", executor, categorical_threshold=10)
    col_map = {c.name: c for c in cols}
    assert col_map["amount"].min_val == 0  # from data_dict
    assert col_map["amount"].max_val == 999
    assert "status" in col_map            # from SQL fallback


def test_to_prompt_dict_excludes_column_specs() -> None:
    dd = DataDict(
        name="sales",
        tables={
            "orders": TableSpec(
                description="Order records.",
                columns=[ColumnSpec(name="amount", range=ColumnRange(min=0, max=100))],
            )
        },
    )
    d = dd.to_prompt_dict()
    assert "columns" not in (d.get("tables", {}).get("orders") or {})


def test_to_prompt_dict_includes_table_description() -> None:
    dd = DataDict(tables={"orders": TableSpec(description="Order records.")})
    d = dd.to_prompt_dict()
    assert d["tables"]["orders"]["description"] == "Order records."


def test_to_prompt_dict_table_with_no_description_is_null() -> None:
    dd = DataDict(tables={"orders": TableSpec()})
    d = dd.to_prompt_dict()
    assert d["tables"]["orders"] is None


def test_to_prompt_dict_excludes_none_name() -> None:
    dd = DataDict()
    d = dd.to_prompt_dict()
    assert "name" not in d


def test_to_prompt_dict_excludes_none_description() -> None:
    dd = DataDict(name="sales")
    d = dd.to_prompt_dict()
    assert "description" not in d


def test_to_prompt_dict_includes_relationships() -> None:
    from querychat._data_dict import RelationshipSpec

    dd = DataDict(
        relationships=[RelationshipSpec(join="a.id = b.id", cardinality="one-to-many")]
    )
    d = dd.to_prompt_dict()
    assert d["relationships"][0]["join"] == "a.id = b.id"
    assert d["relationships"][0]["cardinality"] == "one-to-many"


def test_to_prompt_dict_includes_glossary() -> None:
    dd = DataDict(glossary={"ARR": "Annual Recurring Revenue"})
    d = dd.to_prompt_dict()
    assert d["glossary"]["ARR"] == "Annual Recurring Revenue"
