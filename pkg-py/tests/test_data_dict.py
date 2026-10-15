import warnings
from pathlib import Path

import narwhals.stable.v1 as nw
import polars as pl
import pytest
from pydantic import ValidationError
from querychat._data_dict import ColumnSpec, DataDict, TableSpec
from querychat._datasource import DataFrameSource
from querychat._query_executor import DataSourceExecutor


def test_from_yaml_full_spec(tmp_path: Path) -> None:
    yaml_content = """\
$version: "0.1.0"
tables:
  - name: orders
    description: One row per order.
    columns:
      - name: order_id
        type: number(id)
        constraints: [primary_key]
        description: Unique order identifier.
        examples: [1, 2, 3]
      - name: amount
        type: number(quantity)
        range: [0, 10000]
      - name: status
        type: enum
        values: [pending, shipped, delivered]
      - name: channel
        type: enum
        values: {W: Web, R: Retail}
      - name: discount
        type: number(quantity)
        constraints:
          - assert: discount >= 0
            language: sql
            description: Non-negative discount
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

    assert [t.name for t in dd.tables] == ["orders"]
    t = dd.tables[0]
    assert t.description == "One row per order."
    assert len(t.columns) == 5

    col = t.columns[0]
    assert col.name == "order_id"
    assert col.description == "Unique order identifier."
    assert col.constraints == ["primary_key"]

    assert t.columns[1].range == [0, 10000]
    assert t.columns[2].values == ["pending", "shipped", "delivered"]
    assert t.columns[3].values == {"W": "Web", "R": "Retail"}

    constraint = t.columns[4].constraints[0]
    assert not isinstance(constraint, str)
    assert constraint.assert_ == "discount >= 0"
    assert constraint.language == "sql"
    assert constraint.description == "Non-negative discount"

    assert len(dd.relationships) == 1
    assert dd.relationships[0].join == "orders.customer_id = customers.id"
    assert dd.relationships[0].cardinality == "many-to-one"
    assert dd.glossary["churn"] == "Customer with no orders in 90+ days."


def test_from_yaml_legacy_dict_tables_error(tmp_path: Path) -> None:
    f = tmp_path / "spec.yaml"
    f.write_text("tables:\n  orders:\n    columns: []\n")
    with pytest.raises(ValidationError, match="outdated format"):
        DataDict.from_yaml(f)


def test_newer_spec_version_warns_but_is_read(tmp_path: Path) -> None:
    f = tmp_path / "spec.yaml"
    f.write_text('$version: "0.2.0"\ntables: []\n')
    with pytest.warns(UserWarning, match="best-effort basis"):
        dd = DataDict.from_yaml(f)
    assert dd.tables == []


def test_spec_version_predating_first_spec_warns() -> None:
    with pytest.warns(UserWarning, match="predates the first"):
        DataDict.model_validate({"$version": "0.0.9"})


def test_invalid_spec_version_warns(tmp_path: Path) -> None:
    f = tmp_path / "spec.yaml"
    f.write_text('$version: "not-a-version"\n')
    with pytest.warns(UserWarning, match=r"invalid `\$version`"):
        DataDict.from_yaml(f)


def test_null_spec_version_means_absent(tmp_path: Path) -> None:
    f = tmp_path / "spec.yaml"
    f.write_text("$version:\ntables: []\n")
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert DataDict.from_yaml(f).tables == []


def test_known_spec_version_ok(tmp_path: Path) -> None:
    f = tmp_path / "spec.yaml"
    f.write_text('$version: "0.1.0"\ntables: []\n')
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert DataDict.from_yaml(f).tables == []

    # Short forms are zero-padded ("0.1" == "0.1.0")
    f.write_text('$version: "0.1"\ntables: []\n')
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert DataDict.from_yaml(f).tables == []


def test_table_requires_name(tmp_path: Path) -> None:
    f = tmp_path / "spec.yaml"
    f.write_text("tables:\n  - description: No name here\n    columns: []\n")
    with pytest.raises(ValidationError):
        DataDict.from_yaml(f)


def test_range_must_have_two_elements() -> None:
    with pytest.raises(ValidationError, match="two-element"):
        ColumnSpec(name="x", range=[0, 1, 2])


def test_from_yaml_partial_spec(tmp_path: Path) -> None:
    f = tmp_path / "spec.yaml"
    f.write_text("tables:\n  - name: orders\n    columns: []\n")
    dd = DataDict.from_yaml(f)
    assert dd.tables[0].description is None
    assert dd.relationships == []
    assert dd.glossary == {}


def test_from_yaml_str_path(tmp_path: Path) -> None:
    f = tmp_path / "spec.yaml"
    f.write_text('$version: "0.1.0"\n')
    dd = DataDict.from_yaml(str(f))
    assert dd.tables == []


def test_name_and_description_are_optional() -> None:
    dd = DataDict()
    assert dd.name is None
    assert dd.description is None


def test_from_yaml_derives_name_from_file_stem(tmp_path: Path) -> None:
    f = tmp_path / "my_schema.yaml"
    f.write_text('$version: "0.1.0"\n')
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
    f.write_text('$version: "0.1.0"\n')
    dd = DataDict.from_yaml(f)
    assert dd.description is None


def _make_executor(df: pl.DataFrame, table_name: str) -> DataSourceExecutor:
    source = DataFrameSource(nw.from_native(df), table_name)
    return DataSourceExecutor({table_name: source})


def test_get_table_schema_all_documented() -> None:
    dd = DataDict(
        tables=[
            TableSpec(
                name="orders",
                description="Order records.",
                columns=[
                    ColumnSpec(
                        name="amount",
                        description="Order total in USD.",
                        range=[0, 500],
                    ),
                    ColumnSpec(
                        name="status",
                        values=["pending", "shipped"],
                    ),
                ],
            )
        ],
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
    dd = DataDict(tables=[TableSpec(name="orders", columns=[])])
    df = pl.DataFrame({"amount": [10, 20, 30], "status": ["a", "b", "a"]})
    executor = _make_executor(df, "orders")
    cols = dd.get_table_schema("orders", executor, categorical_threshold=10)
    col_names = [c.name for c in cols]
    # SQL fallback should populate stats
    assert "amount" in col_names
    assert "status" in col_names


def test_get_table_schema_mixed_coverage() -> None:
    dd = DataDict(
        tables=[
            TableSpec(
                name="orders",
                columns=[
                    ColumnSpec(name="amount", range=[0, 999]),
                ],
            )
        ],
    )
    df = pl.DataFrame({"amount": [10, 20], "status": ["a", "b"]})
    executor = _make_executor(df, "orders")
    cols = dd.get_table_schema("orders", executor, categorical_threshold=10)
    col_map = {c.name: c for c in cols}
    assert col_map["amount"].min_val == 0  # from data_dict
    assert col_map["amount"].max_val == 999
    assert "status" in col_map  # from SQL fallback


def test_get_table_schema_open_ended_range() -> None:
    dd = DataDict(
        tables=[
            TableSpec(
                name="orders",
                columns=[ColumnSpec(name="amount", range=[0, None])],
            )
        ],
    )
    df = pl.DataFrame({"amount": [10, 20]})
    executor = _make_executor(df, "orders")
    cols = dd.get_table_schema("orders", executor, categorical_threshold=10)
    assert cols[0].min_val == 0
    assert cols[0].max_val is None


def test_get_table_schema_values_map_uses_keys() -> None:
    dd = DataDict(
        tables=[
            TableSpec(
                name="orders",
                columns=[ColumnSpec(name="status", values={"W": "Web", "R": "Retail"})],
            )
        ],
    )
    df = pl.DataFrame({"status": ["W", "R"]})
    executor = _make_executor(df, "orders")
    cols = dd.get_table_schema("orders", executor, categorical_threshold=10)
    assert cols[0].categories == ["W", "R"]


def test_get_table_schema_assertion_constraints() -> None:
    dd = DataDict(
        tables=[
            TableSpec(
                name="orders",
                columns=[
                    ColumnSpec(
                        name="amount",
                        constraints=[
                            {"assert": "amount >= 0", "description": "Non-negative"},
                            "required",
                        ],
                    )
                ],
            )
        ],
    )
    df = pl.DataFrame({"amount": [1, 2]})
    executor = _make_executor(df, "orders")
    cols = dd.get_table_schema("orders", executor, categorical_threshold=10)
    assert cols[0].constraints == ["amount >= 0 (Non-negative)", "required"]


def test_to_prompt_dict_excludes_column_specs() -> None:
    dd = DataDict(
        name="sales",
        tables=[
            TableSpec(
                name="orders",
                description="Order records.",
                columns=[ColumnSpec(name="amount", range=[0, 100])],
            )
        ],
    )
    d = dd.to_prompt_dict()
    assert "columns" not in (d.get("tables", {}).get("orders") or {})


def test_to_prompt_dict_includes_table_description() -> None:
    dd = DataDict(tables=[TableSpec(name="orders", description="Order records.")])
    d = dd.to_prompt_dict()
    assert d["tables"]["orders"]["description"] == "Order records."


def test_to_prompt_dict_table_with_no_description_is_null() -> None:
    dd = DataDict(tables=[TableSpec(name="orders")])
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


def test_new_field_parsing(tmp_path: Path) -> None:
    yaml_content = """\
tables:
  - name: orders
    label: Orders
    constraints:
      - assert: end_date >= start_date
        description: Valid date range
      - primary_key
    columns:
      - name: status
        type: enum
        label: Order status
        values: {W: Web, R: Retail}
      - name: ssn
        type: string
        display: restricted
      - name: created_at
        type: datetime
        time_zone: America/Chicago
relationships:
  - join: mother.otter_no = pup.pup_number
    cardinality: one-to-many
    aliases: {mother: otters, pup: otters}
    conflicts: [description]
"""
    f = tmp_path / "spec.yaml"
    f.write_text(yaml_content)
    dd = DataDict.from_yaml(f)

    t = dd.tables[0]
    assert t.label == "Orders"
    assert len(t.constraints) == 2
    table_constraint = t.constraints[0]
    assert not isinstance(table_constraint, str)
    assert table_constraint.assert_ == "end_date >= start_date"
    assert table_constraint.description == "Valid date range"
    assert t.constraints[1] == "primary_key"

    status, ssn, created_at = t.columns
    assert status.label == "Order status"
    assert ssn.display == "restricted"
    assert created_at.time_zone == "America/Chicago"

    rel = dd.relationships[0]
    assert rel.aliases == {"mother": "otters", "pup": "otters"}
    assert rel.conflicts == ["description"]


def test_get_table_schema_new_column_fields() -> None:
    dd = DataDict(
        tables=[
            TableSpec(
                name="orders",
                columns=[
                    ColumnSpec(
                        name="status",
                        label="Order status",
                        values={"W": "Web", "R": "Retail"},
                        examples=["W", "R"],
                    ),
                    ColumnSpec(
                        name="ssn",
                        display="restricted",
                        examples=["000-00-0000"],
                    ),
                    ColumnSpec(name="created_at", time_zone="America/Chicago"),
                ],
            )
        ],
    )
    df = pl.DataFrame(
        {
            "status": ["W", "R"],
            "ssn": ["x", "y"],
            "created_at": [1, 2],
        }
    )
    executor = _make_executor(df, "orders")
    cols = dd.get_table_schema("orders", executor, categorical_threshold=10)
    col_map = {c.name: c for c in cols}

    status = col_map["status"]
    assert status.label == "Order status"
    assert status.categories == ["W", "R"]
    assert status.value_labels == {"W": "Web", "R": "Retail"}
    assert status.examples == ["W", "R"]

    ssn = col_map["ssn"]
    assert ssn.display == "restricted"
    assert ssn.examples == []  # withheld on restricted columns

    assert col_map["created_at"].time_zone == "America/Chicago"


def test_to_prompt_dict_new_pass_throughs() -> None:
    from querychat._data_dict import RelationshipSpec

    dd = DataDict(
        tables=[TableSpec(name="orders", description="Orders", label="Orders title")],
        relationships=[
            RelationshipSpec(
                join="mother.otter_no = pup.pup_number",
                cardinality="one-to-many",
                aliases={"mother": "otters", "pup": "otters"},
                conflicts=["description"],
            )
        ],
    )
    d = dd.to_prompt_dict()
    assert d["tables"]["orders"]["label"] == "Orders title"
    assert d["relationships"][0]["aliases"] == {"mother": "otters", "pup": "otters"}
    assert d["relationships"][0]["conflicts"] == ["description"]


def test_constraint_assertion_constructible_by_name_and_round_trips() -> None:
    from querychat._data_dict import ConstraintAssertion

    ca = ConstraintAssertion(assert_="amount >= 0", description="Non-negative")
    assert ca.assert_ == "amount >= 0"
    dd = DataDict(
        tables=[
            TableSpec(
                name="orders",
                columns=[ColumnSpec(name="amount", constraints=[ca])],
            )
        ],
    )
    dd2 = DataDict.model_validate(dd.model_dump())
    constraint = dd2.tables[0].columns[0].constraints[0]
    assert not isinstance(constraint, str)
    assert constraint.assert_ == "amount >= 0"
    assert constraint.description == "Non-negative"


def test_values_map_accepts_numeric_keys(tmp_path: Path) -> None:
    f = tmp_path / "spec.yaml"
    f.write_text(
        "tables:\n  - name: orders\n    columns:\n"
        "      - name: arm\n        values: {0: Control, 1: Treatment}\n"
    )
    dd = DataDict.from_yaml(f)
    assert dd.tables[0].columns[0].values == {"0": "Control", "1": "Treatment"}


def test_range_infinity_sentinels_mean_open(tmp_path: Path) -> None:
    f = tmp_path / "spec.yaml"
    f.write_text(
        "tables:\n  - name: orders\n    columns:\n"
        "      - name: amount\n        range: [0, .inf]\n"
        "      - name: score\n        range: [-.inf, 100]\n"
    )
    dd = DataDict.from_yaml(f)
    assert dd.tables[0].columns[0].range == [0, None]
    assert dd.tables[0].columns[1].range == [None, 100]
