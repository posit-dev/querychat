# Multi-Table Support Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extend QueryChat to support multiple tables while preserving backwards compatibility for single-table use cases.

**Architecture:** The implementation uses a dictionary-based storage for multiple data sources, a TableAccessor class for per-table access, per-table reactive state management, and tool parameters to target specific tables. The LLM handles JOINs for queries while each table maintains independent filter state.

**Tech Stack:** Python, Shiny for Python, chatlas, narwhals, pytest

**Design Document:** `docs/plans/2025-01-14-multi-table-design.md`

---

## Phase 1: Multi-Source Storage Infrastructure

This phase changes the internal storage from a single `_data_source` to a dictionary of data sources keyed by table name.

### Task 1.1: Add `_data_sources` Dictionary Storage

**Files:**
- Modify: `pkg-py/src/querychat/_querychat.py:44-92`
- Test: `pkg-py/tests/test_multi_table.py` (create)

**Step 1: Create test file with initial failing test**

Create `pkg-py/tests/test_multi_table.py`:

```python
"""Tests for multi-table support."""

import os

import pandas as pd
import pytest
from querychat import QueryChat


@pytest.fixture(autouse=True)
def set_dummy_api_key():
    """Set a dummy OpenAI API key for testing."""
    old_api_key = os.environ.get("OPENAI_API_KEY")
    os.environ["OPENAI_API_KEY"] = "sk-dummy-api-key-for-testing"
    yield
    if old_api_key is not None:
        os.environ["OPENAI_API_KEY"] = old_api_key
    else:
        del os.environ["OPENAI_API_KEY"]


@pytest.fixture
def orders_df():
    """Sample orders DataFrame."""
    return pd.DataFrame({
        "id": [1, 2, 3],
        "customer_id": [101, 102, 101],
        "amount": [100.0, 200.0, 150.0],
    })


@pytest.fixture
def customers_df():
    """Sample customers DataFrame."""
    return pd.DataFrame({
        "id": [101, 102, 103],
        "name": ["Alice", "Bob", "Charlie"],
        "state": ["CA", "NY", "CA"],
    })


class TestMultiSourceStorage:
    """Tests for multi-source storage infrastructure."""

    def test_single_table_stored_in_data_sources(self, orders_df):
        """Test that single table is stored in _data_sources dict."""
        qc = QueryChat(orders_df, "orders", greeting="Hello!")

        # Should have _data_sources dict with one entry
        assert hasattr(qc, "_data_sources")
        assert isinstance(qc._data_sources, dict)
        assert "orders" in qc._data_sources
        assert len(qc._data_sources) == 1

    def test_data_source_property_returns_first_source(self, orders_df):
        """Test backwards compatibility: data_source property returns the first source."""
        qc = QueryChat(orders_df, "orders", greeting="Hello!")

        # data_source property should return the single source
        assert qc.data_source is qc._data_sources["orders"]
```

**Step 2: Run test to verify it fails**

Run: `cd pkg-py && uv run pytest tests/test_multi_table.py::TestMultiSourceStorage::test_single_table_stored_in_data_sources -v`
Expected: FAIL with "AttributeError: 'QueryChatExpress' object has no attribute '_data_sources'"

**Step 3: Implement dictionary storage**

In `pkg-py/src/querychat/_querychat.py`, change the constructor (around lines 44-92):

Replace:
```python
self._data_source = normalize_data_source(data_source, table_name)
```

With:
```python
self._data_sources: dict[str, DataSource] = {}
normalized = normalize_data_source(data_source, table_name)
self._data_sources[table_name] = normalized
```

Update the `data_source` property (around line 450-460) to return from dictionary:

```python
@property
def data_source(self) -> DataSource:
    """The data source (for single-table backwards compatibility)."""
    if len(self._data_sources) == 1:
        return next(iter(self._data_sources.values()))
    raise ValueError(
        f"Multiple tables present ({', '.join(self._data_sources.keys())}). "
        "Use qc.table('name').data_source instead."
    )
```

Also update cleanup() method to iterate over all sources.

**Step 4: Run test to verify it passes**

Run: `cd pkg-py && uv run pytest tests/test_multi_table.py::TestMultiSourceStorage -v`
Expected: PASS

**Step 5: Commit**

```bash
git add pkg-py/tests/test_multi_table.py pkg-py/src/querychat/_querychat.py
git commit -m "feat(pkg-py): add dictionary storage for multiple data sources

Store data sources in _data_sources dict keyed by table name.
Maintains backwards compatibility via data_source property.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

### Task 1.2: Add `table_names()` Method

**Files:**
- Modify: `pkg-py/src/querychat/_querychat.py`
- Test: `pkg-py/tests/test_multi_table.py`

**Step 1: Write the failing test**

Add to `TestMultiSourceStorage` class:

```python
def test_table_names_returns_list(self, orders_df):
    """Test that table_names() returns list of table names."""
    qc = QueryChat(orders_df, "orders", greeting="Hello!")

    names = qc.table_names()

    assert names == ["orders"]
```

**Step 2: Run test to verify it fails**

Run: `cd pkg-py && uv run pytest tests/test_multi_table.py::TestMultiSourceStorage::test_table_names_returns_list -v`
Expected: FAIL with "AttributeError: 'QueryChatExpress' object has no attribute 'table_names'"

**Step 3: Implement table_names() method**

Add method to `QueryChatBase` class:

```python
def table_names(self) -> list[str]:
    """
    Return the names of all registered tables.

    Returns
    -------
    list[str]
        List of table names in the order they were added.
    """
    return list(self._data_sources.keys())
```

**Step 4: Run test to verify it passes**

Run: `cd pkg-py && uv run pytest tests/test_multi_table.py::TestMultiSourceStorage::test_table_names_returns_list -v`
Expected: PASS

**Step 5: Commit**

```bash
git add pkg-py/src/querychat/_querychat.py pkg-py/tests/test_multi_table.py
git commit -m "feat(pkg-py): add table_names() method

Returns list of registered table names in add-order.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

### Task 1.3: Add `add_table()` Method

**Files:**
- Modify: `pkg-py/src/querychat/_querychat.py`
- Test: `pkg-py/tests/test_multi_table.py`

**Step 1: Write failing tests**

Add new test class:

```python
class TestAddTable:
    """Tests for add_table() method."""

    def test_add_table_basic(self, orders_df, customers_df):
        """Test adding a second table."""
        qc = QueryChat(orders_df, "orders", greeting="Hello!")
        qc.add_table(customers_df, "customers")

        assert qc.table_names() == ["orders", "customers"]
        assert len(qc._data_sources) == 2

    def test_add_table_with_relationships(self, orders_df, customers_df):
        """Test adding table with explicit relationships."""
        qc = QueryChat(orders_df, "orders", greeting="Hello!")
        qc.add_table(
            customers_df, "customers",
            relationships={"id": "orders.customer_id"}
        )

        assert "customers" in qc._data_sources

    def test_add_table_with_description(self, orders_df, customers_df):
        """Test adding table with description."""
        qc = QueryChat(orders_df, "orders", greeting="Hello!")
        qc.add_table(
            customers_df, "customers",
            description="Customer contact information"
        )

        assert "customers" in qc._data_sources

    def test_add_table_duplicate_name_raises(self, orders_df):
        """Test that adding duplicate table name raises error."""
        qc = QueryChat(orders_df, "orders", greeting="Hello!")

        with pytest.raises(ValueError, match="Table 'orders' already exists"):
            qc.add_table(orders_df, "orders")

    def test_add_table_invalid_name_raises(self, orders_df, customers_df):
        """Test that invalid table name raises error."""
        qc = QueryChat(orders_df, "orders", greeting="Hello!")

        with pytest.raises(ValueError, match="must begin with a letter"):
            qc.add_table(customers_df, "123invalid")

    def test_add_table_after_server_raises(self, orders_df, customers_df):
        """Test that adding table after server init raises error."""
        qc = QueryChat(orders_df, "orders", greeting="Hello!")
        qc._server_initialized = True  # Simulate server initialization

        with pytest.raises(RuntimeError, match="Cannot add tables after server"):
            qc.add_table(customers_df, "customers")
```

**Step 2: Run tests to verify they fail**

Run: `cd pkg-py && uv run pytest tests/test_multi_table.py::TestAddTable -v`
Expected: FAIL with "AttributeError: 'QueryChatExpress' object has no attribute 'add_table'"

**Step 3: Implement add_table() method**

Add to `QueryChatBase` class:

```python
def add_table(
    self,
    data_source: IntoFrame | sqlalchemy.Engine,
    table_name: str,
    *,
    relationships: dict[str, str] | None = None,
    description: str | None = None,
    infer_relationships: bool = True,
) -> None:
    """
    Add an additional table to the QueryChat instance.

    Parameters
    ----------
    data_source
        The data source (DataFrame, LazyFrame, or database connection).
    table_name
        Name for the table (must be unique within this QueryChat).
    relationships
        Optional dict mapping local columns to "other_table.column" for JOINs.
        Example: {"customer_id": "customers.id"}
    description
        Optional free-text description of the table for the LLM.
    infer_relationships
        Whether to auto-detect relationships from database metadata.
        Only applies to database connections. Default True.

    Raises
    ------
    ValueError
        If table_name already exists or is invalid.
    RuntimeError
        If called after server() has been invoked.
    """
    # Check if server already initialized
    if getattr(self, "_server_initialized", False):
        raise RuntimeError(
            "Cannot add tables after server initialization. "
            "Add all tables before calling .server() or .app()."
        )

    # Validate table name format
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9_]*$", table_name):
        raise ValueError(
            "Table name must begin with a letter and contain only "
            "letters, numbers, and underscores"
        )

    # Check for duplicates
    if table_name in self._data_sources:
        raise ValueError(f"Table '{table_name}' already exists")

    # Normalize and store the data source
    normalized = normalize_data_source(data_source, table_name)
    self._data_sources[table_name] = normalized

    # Store relationship and description metadata
    if not hasattr(self, "_table_relationships"):
        self._table_relationships: dict[str, dict[str, str]] = {}
    if not hasattr(self, "_table_descriptions"):
        self._table_descriptions: dict[str, str] = {}

    if relationships:
        self._table_relationships[table_name] = relationships
    if description:
        self._table_descriptions[table_name] = description

    # TODO: Implement infer_relationships for database connections
```

Also add `_server_initialized = False` to `__init__`.

**Step 4: Run tests to verify they pass**

Run: `cd pkg-py && uv run pytest tests/test_multi_table.py::TestAddTable -v`
Expected: PASS

**Step 5: Commit**

```bash
git add pkg-py/src/querychat/_querychat.py pkg-py/tests/test_multi_table.py
git commit -m "feat(pkg-py): add add_table() method for multi-table support

Allows adding additional tables after construction.
Stores relationships and descriptions for LLM context.
Validates table names and prevents duplicates.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

### Task 1.4: Add `remove_table()` Method

**Files:**
- Modify: `pkg-py/src/querychat/_querychat.py`
- Test: `pkg-py/tests/test_multi_table.py`

**Step 1: Write failing tests**

Add new test class:

```python
class TestRemoveTable:
    """Tests for remove_table() method."""

    def test_remove_table_basic(self, orders_df, customers_df):
        """Test removing a table."""
        qc = QueryChat(orders_df, "orders", greeting="Hello!")
        qc.add_table(customers_df, "customers")

        qc.remove_table("customers")

        assert qc.table_names() == ["orders"]

    def test_remove_table_nonexistent_raises(self, orders_df):
        """Test that removing nonexistent table raises error."""
        qc = QueryChat(orders_df, "orders", greeting="Hello!")

        with pytest.raises(ValueError, match="Table 'foo' not found"):
            qc.remove_table("foo")

    def test_remove_last_table_raises(self, orders_df):
        """Test that removing last table raises error."""
        qc = QueryChat(orders_df, "orders", greeting="Hello!")

        with pytest.raises(ValueError, match="Cannot remove last table"):
            qc.remove_table("orders")

    def test_remove_table_after_server_raises(self, orders_df, customers_df):
        """Test that removing table after server init raises error."""
        qc = QueryChat(orders_df, "orders", greeting="Hello!")
        qc.add_table(customers_df, "customers")
        qc._server_initialized = True

        with pytest.raises(RuntimeError, match="Cannot remove tables after server"):
            qc.remove_table("customers")
```

**Step 2: Run tests to verify they fail**

Run: `cd pkg-py && uv run pytest tests/test_multi_table.py::TestRemoveTable -v`
Expected: FAIL with "AttributeError: 'QueryChatExpress' object has no attribute 'remove_table'"

**Step 3: Implement remove_table() method**

Add to `QueryChatBase` class:

```python
def remove_table(self, table_name: str) -> None:
    """
    Remove a table from the QueryChat instance.

    Parameters
    ----------
    table_name
        Name of the table to remove.

    Raises
    ------
    ValueError
        If table doesn't exist or is the last remaining table.
    RuntimeError
        If called after server() has been invoked.
    """
    if getattr(self, "_server_initialized", False):
        raise RuntimeError(
            "Cannot remove tables after server initialization. "
            "Configure all tables before calling .server() or .app()."
        )

    if table_name not in self._data_sources:
        available = ", ".join(self._data_sources.keys())
        raise ValueError(f"Table '{table_name}' not found. Available: {available}")

    if len(self._data_sources) == 1:
        raise ValueError(
            "Cannot remove last table. At least one table is required."
        )

    # Clean up the data source
    self._data_sources[table_name].cleanup()
    del self._data_sources[table_name]

    # Remove associated metadata
    if hasattr(self, "_table_relationships"):
        self._table_relationships.pop(table_name, None)
    if hasattr(self, "_table_descriptions"):
        self._table_descriptions.pop(table_name, None)
```

**Step 4: Run tests to verify they pass**

Run: `cd pkg-py && uv run pytest tests/test_multi_table.py::TestRemoveTable -v`
Expected: PASS

**Step 5: Commit**

```bash
git add pkg-py/src/querychat/_querychat.py pkg-py/tests/test_multi_table.py
git commit -m "feat(pkg-py): add remove_table() method

Allows removing tables before server initialization.
Cleans up data source and associated metadata.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Phase 2: TableAccessor Class

This phase implements the `.table("name")` accessor pattern that returns an object with `.df()`, `.sql()`, `.title()` methods.

### Task 2.1: Create TableAccessor Class

**Files:**
- Create: `pkg-py/src/querychat/_table_accessor.py`
- Modify: `pkg-py/src/querychat/__init__.py`
- Test: `pkg-py/tests/test_multi_table.py`

**Step 1: Write failing tests**

Add new test class:

```python
class TestTableAccessor:
    """Tests for table() method and TableAccessor class."""

    def test_table_returns_accessor(self, orders_df):
        """Test that table() returns a TableAccessor."""
        qc = QueryChat(orders_df, "orders", greeting="Hello!")

        accessor = qc.table("orders")

        assert accessor is not None
        assert accessor.table_name == "orders"

    def test_table_accessor_has_data_source(self, orders_df):
        """Test that accessor provides access to data source."""
        qc = QueryChat(orders_df, "orders", greeting="Hello!")

        accessor = qc.table("orders")

        assert accessor.data_source is qc._data_sources["orders"]

    def test_table_nonexistent_raises(self, orders_df):
        """Test that accessing nonexistent table raises error."""
        qc = QueryChat(orders_df, "orders", greeting="Hello!")

        with pytest.raises(ValueError, match="Table 'foo' not found"):
            qc.table("foo")

    def test_table_accessor_multiple_tables(self, orders_df, customers_df):
        """Test accessor works with multiple tables."""
        qc = QueryChat(orders_df, "orders", greeting="Hello!")
        qc.add_table(customers_df, "customers")

        orders_accessor = qc.table("orders")
        customers_accessor = qc.table("customers")

        assert orders_accessor.table_name == "orders"
        assert customers_accessor.table_name == "customers"
        assert orders_accessor.data_source is not customers_accessor.data_source
```

**Step 2: Run tests to verify they fail**

Run: `cd pkg-py && uv run pytest tests/test_multi_table.py::TestTableAccessor -v`
Expected: FAIL with "AttributeError: 'QueryChatExpress' object has no attribute 'table'"

**Step 3: Create TableAccessor class**

Create `pkg-py/src/querychat/_table_accessor.py`:

```python
"""TableAccessor class for accessing per-table state and data."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ._datasource import AnyFrame, DataSource


class TableAccessor:
    """
    Accessor for a specific table's state and data.

    This class provides access to per-table reactive state (df, sql, title)
    and is returned by QueryChat.table("name").

    Parameters
    ----------
    querychat
        The parent QueryChat instance.
    table_name
        The name of the table this accessor represents.
    """

    def __init__(self, querychat: "QueryChatBase", table_name: str):
        self._querychat = querychat
        self._table_name = table_name

    @property
    def table_name(self) -> str:
        """The name of this table."""
        return self._table_name

    @property
    def data_source(self) -> "DataSource":
        """The data source for this table."""
        return self._querychat._data_sources[self._table_name]

    # Reactive accessors will be added in Phase 6
    # def df(self) -> AnyFrame: ...
    # def sql(self) -> str | None: ...
    # def title(self) -> str | None: ...


# Import at bottom to avoid circular imports
if TYPE_CHECKING:
    from ._querychat import QueryChatBase
```

**Step 4: Add table() method to QueryChatBase**

In `pkg-py/src/querychat/_querychat.py`, add import and method:

```python
from ._table_accessor import TableAccessor

# In QueryChatBase class:
def table(self, name: str) -> TableAccessor:
    """
    Get an accessor for a specific table.

    Parameters
    ----------
    name
        The name of the table to access.

    Returns
    -------
    TableAccessor
        An accessor object with df(), sql(), title() methods.

    Raises
    ------
    ValueError
        If the table doesn't exist.
    """
    if name not in self._data_sources:
        available = ", ".join(self._data_sources.keys())
        raise ValueError(f"Table '{name}' not found. Available: {available}")

    return TableAccessor(self, name)
```

**Step 5: Run tests to verify they pass**

Run: `cd pkg-py && uv run pytest tests/test_multi_table.py::TestTableAccessor -v`
Expected: PASS

**Step 6: Commit**

```bash
git add pkg-py/src/querychat/_table_accessor.py pkg-py/src/querychat/_querychat.py pkg-py/tests/test_multi_table.py
git commit -m "feat(pkg-py): add TableAccessor class and table() method

Provides per-table access pattern: qc.table('name').data_source
Reactive methods (df, sql, title) will be added in Phase 6.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Phase 3: Backwards-Compatible Accessor Errors

This phase modifies `.df()`, `.sql()`, `.title()` on QueryChatExpress to raise helpful errors when multiple tables are present.

### Task 3.1: Add Ambiguity Errors to Express Accessors

**Files:**
- Modify: `pkg-py/src/querychat/_querychat.py:828-903`
- Test: `pkg-py/tests/test_multi_table.py`

**Step 1: Write failing tests**

Add new test class:

```python
class TestAccessorAmbiguity:
    """Tests for accessor ambiguity errors with multiple tables."""

    def test_df_single_table_works(self, orders_df):
        """Test that df() works with single table."""
        qc = QueryChat(orders_df, "orders", greeting="Hello!")
        # Can't fully test reactive without server, but method should exist
        assert hasattr(qc, "df")

    def test_sql_single_table_works(self, orders_df):
        """Test that sql() works with single table."""
        qc = QueryChat(orders_df, "orders", greeting="Hello!")
        assert hasattr(qc, "sql")

    def test_title_single_table_works(self, orders_df):
        """Test that title() works with single table."""
        qc = QueryChat(orders_df, "orders", greeting="Hello!")
        assert hasattr(qc, "title")

    def test_data_source_multiple_tables_raises(self, orders_df, customers_df):
        """Test that data_source property raises with multiple tables."""
        qc = QueryChat(orders_df, "orders", greeting="Hello!")
        qc.add_table(customers_df, "customers")

        with pytest.raises(ValueError, match="Multiple tables present"):
            _ = qc.data_source
```

**Step 2: Run tests**

Run: `cd pkg-py && uv run pytest tests/test_multi_table.py::TestAccessorAmbiguity -v`
Expected: Tests should pass with current implementation (data_source was updated in Task 1.1)

**Step 3: Commit if tests pass**

Note: The actual `.df()`, `.sql()`, `.title()` ambiguity errors require the server to be initialized. These will be fully tested in Phase 6 when we implement per-table reactive state.

```bash
git add pkg-py/tests/test_multi_table.py
git commit -m "test(pkg-py): add accessor ambiguity tests

Verifies data_source raises when multiple tables present.
Full df/sql/title tests will be added with reactive state.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Phase 4: Tool Changes

This phase adds the `table` parameter to update_dashboard and reset_dashboard tools.

### Task 4.1: Update UpdateDashboardData TypedDict

**Files:**
- Modify: `pkg-py/src/querychat/tools.py:20-57`
- Test: `pkg-py/tests/test_tools.py`

**Step 1: Write failing test**

Add to existing test file or create section:

```python
def test_update_dashboard_data_has_table_field():
    """Test that UpdateDashboardData includes table field."""
    from querychat.tools import UpdateDashboardData

    # TypedDict should have table as a key
    assert "table" in UpdateDashboardData.__annotations__
```

**Step 2: Run test to verify it fails**

Run: `cd pkg-py && uv run pytest tests/test_tools.py::test_update_dashboard_data_has_table_field -v`
Expected: FAIL with "AssertionError"

**Step 3: Update TypedDict**

In `pkg-py/src/querychat/tools.py`, modify `UpdateDashboardData`:

```python
class UpdateDashboardData(TypedDict):
    """
    Data passed to update_dashboard callback.

    Attributes
    ----------
    table
        The name of the table being filtered.
    query
        The SQL query string to execute for filtering/sorting the dashboard.
    title
        A descriptive title for the query, typically displayed in the UI.
    """

    table: str
    query: str
    title: str
```

**Step 4: Run test to verify it passes**

Run: `cd pkg-py && uv run pytest tests/test_tools.py::test_update_dashboard_data_has_table_field -v`
Expected: PASS

**Step 5: Commit**

```bash
git add pkg-py/src/querychat/tools.py pkg-py/tests/test_tools.py
git commit -m "feat(pkg-py): add table field to UpdateDashboardData

Prepares for multi-table support in update_dashboard tool.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

### Task 4.2: Update update_dashboard Tool Signature

**Files:**
- Modify: `pkg-py/src/querychat/tools.py:66-146`
- Modify: `pkg-py/src/querychat/prompts/tool-update-dashboard.md`
- Test: `pkg-py/tests/test_tools.py`

**Step 1: Write failing test**

```python
def test_update_dashboard_accepts_table_parameter():
    """Test that update_dashboard tool accepts table parameter."""
    import pandas as pd
    from querychat._datasource import DataFrameSource
    from querychat.tools import tool_update_dashboard

    df = pd.DataFrame({"id": [1, 2], "name": ["a", "b"]})
    source = DataFrameSource(df, "test_table")
    sources = {"test_table": source}

    called_with = {}

    def callback(data):
        called_with.update(data)

    tool = tool_update_dashboard(sources, callback)

    # The tool function should accept table parameter
    result = tool._func(table="test_table", query="SELECT * FROM test_table", title="All data")

    assert called_with.get("table") == "test_table"
```

**Step 2: Run test to verify it fails**

Run: `cd pkg-py && uv run pytest tests/test_tools.py::test_update_dashboard_accepts_table_parameter -v`
Expected: FAIL with TypeError about unexpected keyword argument 'table'

**Step 3: Update tool implementation**

Modify `_update_dashboard_impl` and `tool_update_dashboard` in `tools.py`:

```python
def _update_dashboard_impl(
    data_sources: dict[str, DataSource],
    update_fn: Callable[[UpdateDashboardData], None],
) -> Callable[[str, str, str], ContentToolResult]:
    """Create the implementation function for updating the dashboard."""

    def update_dashboard(table: str, query: str, title: str) -> ContentToolResult:
        error = None
        markdown = f"```sql\n{query}\n```"
        value = "Dashboard updated. Use `query` tool to review results, if needed."

        # Validate table exists
        if table not in data_sources:
            available = ", ".join(data_sources.keys())
            error = f"Table '{table}' not found. Available: {available}"
            markdown += f"\n\n> Error: {error}"
            return ContentToolResult(value=markdown, error=Exception(error))

        data_source = data_sources[table]

        try:
            # Test the query but don't execute it yet
            data_source.test_query(query, require_all_columns=True)

            # Add Apply Filter button
            button_html = f"""<button
                class="btn btn-outline-primary btn-sm float-end mt-3 querychat-update-dashboard-btn"
                data-table="{table}"
                data-query="{query}"
                data-title="{title}">
                Apply Filter
            </button>"""

            # Call the callback with TypedDict data on success
            update_fn({"table": table, "query": query, "title": title})

        except Exception as e:
            error = str(e)
            markdown += f"\n\n> Error: {error}"
            return ContentToolResult(value=markdown, error=e)

        # Return ContentToolResult with display metadata
        return ContentToolResult(
            value=value,
            extra={
                "display": ToolResultDisplay(
                    markdown=markdown + f"\n\n{button_html}",
                    title=title,
                    show_request=False,
                    open=querychat_tool_starts_open("update"),
                    icon=bs_icon("funnel-fill"),
                ),
            },
        )

    return update_dashboard


def tool_update_dashboard(
    data_sources: dict[str, DataSource],
    update_fn: Callable[[UpdateDashboardData], None],
) -> Tool:
    """
    Create a tool that modifies the data presented in the dashboard.

    Parameters
    ----------
    data_sources
        Dictionary of data sources keyed by table name.
    update_fn
        Callback function to call with UpdateDashboardData when update succeeds.

    Returns
    -------
    Tool
        A tool that can be registered with chatlas.
    """
    impl = _update_dashboard_impl(data_sources, update_fn)

    # Get db_type from first source (all should be same dialect)
    first_source = next(iter(data_sources.values()))
    description = _read_prompt_template(
        "tool-update-dashboard.md",
        db_type=first_source.get_db_type(),
    )
    impl.__doc__ = description

    return Tool.from_func(
        impl,
        name="querychat_update_dashboard",
        annotations={"title": "Update Dashboard"},
    )
```

**Step 4: Update tool prompt template**

Modify `pkg-py/src/querychat/prompts/tool-update-dashboard.md` to include table parameter documentation:

Add near the top:
```
The `table` parameter specifies which table to filter. Use the table name exactly as shown in the schema.
```

**Step 5: Run test to verify it passes**

Run: `cd pkg-py && uv run pytest tests/test_tools.py::test_update_dashboard_accepts_table_parameter -v`
Expected: PASS

**Step 6: Commit**

```bash
git add pkg-py/src/querychat/tools.py pkg-py/src/querychat/prompts/tool-update-dashboard.md pkg-py/tests/test_tools.py
git commit -m "feat(pkg-py): add table parameter to update_dashboard tool

Tool now requires table parameter to specify which table to filter.
Validates table exists before executing query.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

### Task 4.3: Update reset_dashboard Tool

**Files:**
- Modify: `pkg-py/src/querychat/tools.py:149-209`
- Test: `pkg-py/tests/test_tools.py`

**Step 1: Write failing test**

```python
def test_reset_dashboard_accepts_table_parameter():
    """Test that reset_dashboard tool accepts table parameter."""
    from querychat.tools import tool_reset_dashboard

    reset_tables = []

    def callback(table: str):
        reset_tables.append(table)

    tool = tool_reset_dashboard(callback)

    # The tool function should accept table parameter
    result = tool._func(table="orders")

    assert reset_tables == ["orders"]
```

**Step 2: Run test to verify it fails**

Run: `cd pkg-py && uv run pytest tests/test_tools.py::test_reset_dashboard_accepts_table_parameter -v`
Expected: FAIL with TypeError

**Step 3: Update reset_dashboard implementation**

Modify in `tools.py`:

```python
def _reset_dashboard_impl(
    reset_fn: Callable[[str], None],
) -> Callable[[str], ContentToolResult]:
    """Create the implementation function for resetting the dashboard."""

    def reset_dashboard(table: str) -> ContentToolResult:
        reset_fn(table)
        return ContentToolResult(
            value="Dashboard reset to show all data.",
            extra={
                "display": ToolResultDisplay(
                    markdown="Reset to show all data",
                    title="Reset",
                    show_request=False,
                    open=querychat_tool_starts_open("reset"),
                    icon=bs_icon("arrow-counterclockwise"),
                ),
            },
        )

    return reset_dashboard


def tool_reset_dashboard(reset_fn: Callable[[str], None]) -> Tool:
    """
    Create a tool that resets the dashboard to show all data.

    Parameters
    ----------
    reset_fn
        Callback function to call with table name when reset is requested.

    Returns
    -------
    Tool
        A tool that can be registered with chatlas.
    """
    impl = _reset_dashboard_impl(reset_fn)

    description = _read_prompt_template("tool-reset-dashboard.md")
    impl.__doc__ = description

    return Tool.from_func(
        impl,
        name="querychat_reset_dashboard",
        annotations={"title": "Reset Dashboard"},
    )
```

**Step 4: Update tool prompt template**

Update `pkg-py/src/querychat/prompts/tool-reset-dashboard.md` to mention table parameter.

**Step 5: Run test to verify it passes**

Run: `cd pkg-py && uv run pytest tests/test_tools.py::test_reset_dashboard_accepts_table_parameter -v`
Expected: PASS

**Step 6: Commit**

```bash
git add pkg-py/src/querychat/tools.py pkg-py/src/querychat/prompts/tool-reset-dashboard.md pkg-py/tests/test_tools.py
git commit -m "feat(pkg-py): add table parameter to reset_dashboard tool

Tool now requires table parameter to specify which table to reset.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

### Task 4.4: Update query Tool for Multi-Table

**Files:**
- Modify: `pkg-py/src/querychat/tools.py` (query tool section)
- Test: `pkg-py/tests/test_tools.py`

**Step 1: Write failing test**

```python
def test_query_tool_accepts_multiple_sources():
    """Test that query tool works with multiple data sources."""
    import pandas as pd
    from querychat._datasource import DataFrameSource
    from querychat.tools import tool_query

    orders = pd.DataFrame({"id": [1, 2], "customer_id": [101, 102]})
    customers = pd.DataFrame({"id": [101, 102], "name": ["Alice", "Bob"]})

    sources = {
        "orders": DataFrameSource(orders, "orders"),
        "customers": DataFrameSource(customers, "customers"),
    }

    tool = tool_query(sources)

    # Query should work across tables
    # Note: This requires the sources to share a connection or be in same DuckDB instance
    assert tool is not None
```

**Step 2: Implement multi-source query tool**

The query tool needs access to all tables for JOINs. For DataFrameSource, this requires sharing a DuckDB connection. This is more complex and may need a separate implementation approach.

For now, update the signature to accept `dict[str, DataSource]`:

```python
def tool_query(
    data_sources: dict[str, DataSource],
) -> Tool:
    """Create a tool for querying data across tables."""
    # Use first source for now - multi-table JOINs will need shared connection
    first_source = next(iter(data_sources.values()))
    # ... rest of implementation
```

**Step 3: Run tests**

Run: `cd pkg-py && uv run pytest tests/test_tools.py -v`
Expected: PASS

**Step 4: Commit**

```bash
git add pkg-py/src/querychat/tools.py pkg-py/tests/test_tools.py
git commit -m "feat(pkg-py): update query tool for multi-table support

Query tool now accepts dict of data sources.
Full JOIN support will require shared database connection.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Phase 5: System Prompt Changes

This phase updates the system prompt to include all table schemas and relationship information.

### Task 5.1: Update QueryChatSystemPrompt for Multiple Sources

**Files:**
- Modify: `pkg-py/src/querychat/_system_prompt.py`
- Test: `pkg-py/tests/test_system_prompt.py`

**Step 1: Write failing tests**

```python
class TestMultiTableSystemPrompt:
    """Tests for multi-table system prompt generation."""

    def test_multiple_schemas_in_prompt(self):
        """Test that multiple table schemas appear in prompt."""
        import pandas as pd
        from querychat._datasource import DataFrameSource
        from querychat._system_prompt import QueryChatSystemPrompt

        orders = pd.DataFrame({"id": [1], "amount": [100.0]})
        customers = pd.DataFrame({"id": [1], "name": ["Alice"]})

        sources = {
            "orders": DataFrameSource(orders, "orders"),
            "customers": DataFrameSource(customers, "customers"),
        }

        prompt = QueryChatSystemPrompt(
            prompt_template="Schema: {{schema}}",
            data_sources=sources,
        )

        rendered = prompt.render(tools=("query",))

        assert "orders" in rendered
        assert "customers" in rendered

    def test_relationships_in_prompt(self):
        """Test that relationship information appears in prompt."""
        import pandas as pd
        from querychat._datasource import DataFrameSource
        from querychat._system_prompt import QueryChatSystemPrompt

        orders = pd.DataFrame({"id": [1], "customer_id": [101]})
        customers = pd.DataFrame({"id": [101], "name": ["Alice"]})

        sources = {
            "orders": DataFrameSource(orders, "orders"),
            "customers": DataFrameSource(customers, "customers"),
        }

        relationships = {
            "orders": {"customer_id": "customers.id"}
        }

        prompt = QueryChatSystemPrompt(
            prompt_template="{{schema}}\n{{#relationships}}Relationships:\n{{relationships}}{{/relationships}}",
            data_sources=sources,
            relationships=relationships,
        )

        rendered = prompt.render(tools=("query",))

        assert "customer_id" in rendered
        assert "customers.id" in rendered
```

**Step 2: Run tests to verify they fail**

Run: `cd pkg-py && uv run pytest tests/test_system_prompt.py::TestMultiTableSystemPrompt -v`
Expected: FAIL with TypeError about data_sources parameter

**Step 3: Update QueryChatSystemPrompt**

Modify `pkg-py/src/querychat/_system_prompt.py`:

```python
class QueryChatSystemPrompt:
    """Manages system prompt generation for QueryChat."""

    def __init__(
        self,
        prompt_template: str | Path,
        data_sources: DataSource | dict[str, DataSource],
        data_description: str | Path | None = None,
        extra_instructions: str | Path | None = None,
        categorical_threshold: int = 10,
        relationships: dict[str, dict[str, str]] | None = None,
        table_descriptions: dict[str, str] | None = None,
    ):
        # Handle both single source (backwards compat) and dict of sources
        if isinstance(data_sources, DataSource):
            self._data_sources = {data_sources.table_name: data_sources}
        else:
            self._data_sources = data_sources

        # Load template
        if isinstance(prompt_template, Path):
            self.template = prompt_template.read_text()
        else:
            self.template = prompt_template

        # Store metadata
        self.data_description = _load_text(data_description)
        self.extra_instructions = _load_text(extra_instructions)
        self.categorical_threshold = categorical_threshold
        self._relationships = relationships or {}
        self._table_descriptions = table_descriptions or {}

        # Generate combined schema
        self.schema = self._generate_combined_schema()

    def _generate_combined_schema(self) -> str:
        """Generate schema string for all tables."""
        schemas = []
        for name, source in self._data_sources.items():
            schema = source.get_schema(categorical_threshold=self.categorical_threshold)
            schemas.append(f"<table name=\"{name}\">\n{schema}\n</table>")

        return "\n\n".join(schemas)

    def _generate_relationships_text(self) -> str:
        """Generate relationship information text."""
        if not self._relationships:
            return ""

        lines = []
        for table, rels in self._relationships.items():
            for local_col, foreign_ref in rels.items():
                lines.append(f"- {table}.{local_col} references {foreign_ref}")

        return "\n".join(lines)

    def render(self, tools: tuple[str, ...] | None) -> str:
        """Render the system prompt with given tools."""
        # ... existing logic plus relationships
        context = {
            "db_type": next(iter(self._data_sources.values())).get_db_type(),
            "schema": self.schema,
            "data_description": self.data_description,
            "extra_instructions": self.extra_instructions,
            "has_tool_update": tools is not None and "update" in tools,
            "has_tool_query": tools is not None and "query" in tools,
            "include_query_guidelines": tools is not None and len(tools) > 0,
            "relationships": self._generate_relationships_text(),
        }

        return chevron.render(self.template, context)

    # Backwards compatibility
    @property
    def data_source(self) -> DataSource:
        """Return single data source for backwards compatibility."""
        if len(self._data_sources) == 1:
            return next(iter(self._data_sources.values()))
        raise ValueError("Multiple data sources present")
```

**Step 4: Run tests to verify they pass**

Run: `cd pkg-py && uv run pytest tests/test_system_prompt.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add pkg-py/src/querychat/_system_prompt.py pkg-py/tests/test_system_prompt.py
git commit -m "feat(pkg-py): update system prompt for multi-table support

QueryChatSystemPrompt now accepts dict of data sources.
Generates combined schema with table tags.
Includes relationship information in prompt.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

### Task 5.2: Update Main Prompt Template

**Files:**
- Modify: `pkg-py/src/querychat/prompts/prompt.md`

**Step 1: Update prompt template**

Add relationship section and update tool instructions:

```markdown
{{#relationships}}
<relationships>
{{relationships}}
</relationships>

When answering questions that span multiple tables, use JOINs based on these relationships.
{{/relationships}}

{{#has_tool_update}}
### Filtering and Sorting Data

When filtering, you must specify which table to filter using the `table` parameter.
Only one table can be filtered per tool call.
...
{{/has_tool_update}}
```

**Step 2: Commit**

```bash
git add pkg-py/src/querychat/prompts/prompt.md
git commit -m "feat(pkg-py): update prompt template for multi-table

Adds relationship section and multi-table filtering instructions.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Phase 6: Per-Table Reactive State

This phase implements per-table reactive state management in the Shiny module.

### Task 6.1: Update ServerValues for Multi-Table

**Files:**
- Modify: `pkg-py/src/querychat/_querychat_module.py:49-84`
- Test: `pkg-py/tests/test_multi_table.py`

**Step 1: Design new ServerValues**

The `ServerValues` dataclass needs to support per-table state:

```python
@dataclass
class TableState:
    """Per-table reactive state."""
    df: Callable[[], AnyFrame]
    sql: ReactiveStringOrNone
    title: ReactiveStringOrNone


@dataclass
class ServerValues:
    """Session-specific reactive values."""
    tables: dict[str, TableState]
    client: chatlas.Chat

    # Backwards compatibility for single table
    @property
    def df(self) -> Callable[[], AnyFrame]:
        if len(self.tables) == 1:
            return next(iter(self.tables.values())).df
        raise ValueError("Multiple tables present. Use .tables['name'].df")

    @property
    def sql(self) -> ReactiveStringOrNone:
        if len(self.tables) == 1:
            return next(iter(self.tables.values())).sql
        raise ValueError("Multiple tables present. Use .tables['name'].sql")

    @property
    def title(self) -> ReactiveStringOrNone:
        if len(self.tables) == 1:
            return next(iter(self.tables.values())).title
        raise ValueError("Multiple tables present. Use .tables['name'].title")
```

**Step 2: Write failing tests**

Add to test file:

```python
class TestPerTableState:
    """Tests for per-table reactive state."""

    def test_server_values_has_tables_dict(self, orders_df, customers_df):
        """Test that ServerValues has tables dict."""
        # This requires running the server, which is complex to test
        # For now, test the dataclass structure
        from querychat._querychat_module import ServerValues, TableState

        assert hasattr(ServerValues, "__annotations__")
        assert "tables" in ServerValues.__annotations__
```

**Step 3: Implement per-table state**

This requires significant changes to `mod_server`. The implementation should:

1. Create per-table reactive values
2. Create per-table filtered_df calcs
3. Update callbacks to handle table parameter
4. Return ServerValues with tables dict

**Step 4: Run tests and commit**

```bash
git add pkg-py/src/querychat/_querychat_module.py pkg-py/tests/test_multi_table.py
git commit -m "feat(pkg-py): implement per-table reactive state

ServerValues now contains tables dict with per-table state.
Maintains backwards compatibility for single-table access.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

### Task 6.2: Complete TableAccessor Reactive Methods

**Files:**
- Modify: `pkg-py/src/querychat/_table_accessor.py`
- Test: `pkg-py/tests/test_multi_table.py`

**Step 1: Implement reactive methods on TableAccessor**

```python
class TableAccessor:
    # ... existing code ...

    def df(self) -> AnyFrame:
        """Return the current filtered data for this table (reactive)."""
        if not hasattr(self._querychat, "_vals"):
            raise RuntimeError("Server not initialized. Call .server() first.")
        return self._querychat._vals.tables[self._table_name].df()

    def sql(self) -> str | None:
        """Return the current SQL filter for this table (reactive)."""
        if not hasattr(self._querychat, "_vals"):
            raise RuntimeError("Server not initialized. Call .server() first.")
        return self._querychat._vals.tables[self._table_name].sql.get()

    def title(self) -> str | None:
        """Return the current filter title for this table (reactive)."""
        if not hasattr(self._querychat, "_vals"):
            raise RuntimeError("Server not initialized. Call .server() first.")
        return self._querychat._vals.tables[self._table_name].title.get()
```

**Step 2: Commit**

```bash
git add pkg-py/src/querychat/_table_accessor.py
git commit -m "feat(pkg-py): add reactive methods to TableAccessor

TableAccessor.df(), .sql(), .title() now access per-table reactive state.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Phase 7: UI Changes

This phase implements the tabbed UI and building blocks.

### Task 7.1: Implement Tabbed UI in .app()

**Files:**
- Modify: `pkg-py/src/querychat/_querychat.py` (.app() method)
- Test: Manual testing required

**Step 1: Update .app() for tabs**

Modify the `.app()` method to render tabs when multiple tables are present:

```python
def app(self, *, bookmark_store: Literal["url", "server", "disable"] = "url") -> App:
    # ... existing setup ...

    def app_ui(request):
        table_names = self.table_names()

        if len(table_names) == 1:
            # Single table: existing layout
            main_content = ui.card(
                ui.card_header(
                    bs_icon("database"),
                    table_names[0],
                ),
                ui.output_data_frame("dt"),
            )
        else:
            # Multiple tables: tabbed layout
            tabs = []
            for name in table_names:
                tabs.append(
                    ui.nav_panel(
                        name,
                        ui.output_data_frame(f"dt_{name}"),
                        value=name,
                    )
                )
            main_content = ui.navset_card_tab(*tabs, id="table_tabs")

        # ... rest of layout
```

**Step 2: Update server for multiple data tables**

```python
def app_server(input, output, session):
    vals = self.server()

    for name in self.table_names():
        # Create render for each table
        @output(id=f"dt_{name}")
        @render.data_frame
        def _make_render(table_name=name):
            def render_table():
                return vals.tables[table_name].df()
            return render_table
```

**Step 3: Commit**

```bash
git add pkg-py/src/querychat/_querychat.py
git commit -m "feat(pkg-py): implement tabbed UI for multi-table

.app() renders tabs when multiple tables are present.
Single table mode unchanged for backwards compatibility.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

### Task 7.2: Implement Auto-Switch on Filter

**Files:**
- Modify: `pkg-py/src/querychat/_querychat.py`
- Modify: `pkg-py/src/querychat/_querychat_module.py`

**Step 1: Add active_table reactive value**

In the server module, track which table was most recently filtered:

```python
active_table = reactive.value[str](list(data_sources.keys())[0])

def update_dashboard(data: UpdateDashboardData):
    table = data["table"]
    tables[table].sql.set(data["query"])
    tables[table].title.set(data["title"])
    active_table.set(table)
```

**Step 2: Update UI to switch tabs**

In the app, use `ui.update_navs()` to switch tabs when filter changes:

```python
@reactive.effect
def switch_to_active_table():
    ui.update_navs("table_tabs", selected=vals.active_table())
```

**Step 3: Commit**

```bash
git add pkg-py/src/querychat/_querychat.py pkg-py/src/querychat/_querychat_module.py
git commit -m "feat(pkg-py): auto-switch tabs on filter

UI automatically switches to the most recently filtered table.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

### Task 7.3: Implement .table("name").ui() Building Block

**Files:**
- Modify: `pkg-py/src/querychat/_table_accessor.py`

**Step 1: Add ui() method to TableAccessor**

```python
def ui(self) -> Tag:
    """
    Render the UI for this table (data table + SQL display).

    Returns
    -------
    Tag
        A Shiny UI element containing the data table and SQL display.
    """
    from shiny import ui

    table_id = f"{self._querychat.id}_{self._table_name}"

    return ui.card(
        ui.card_header(self._table_name),
        ui.output_data_frame(f"{table_id}_dt"),
        ui.output_text(f"{table_id}_sql"),
    )
```

**Step 2: Commit**

```bash
git add pkg-py/src/querychat/_table_accessor.py
git commit -m "feat(pkg-py): add .ui() building block to TableAccessor

Enables custom layouts with qc.table('name').ui().

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Phase 8: Integration and Cleanup

### Task 8.1: Update QueryChatBase to Wire Everything Together

**Files:**
- Modify: `pkg-py/src/querychat/_querychat.py`

Ensure all the pieces connect:
1. Constructor creates `_data_sources` dict
2. System prompt receives all sources and relationships
3. Tools receive `data_sources` dict
4. Server creates per-table state

**Step 1: Update constructor**

**Step 2: Update .client() method**

**Step 3: Update .server() method**

**Step 4: Run full test suite**

Run: `cd pkg-py && uv run pytest -v`
Expected: PASS

**Step 5: Commit**

```bash
git add pkg-py/src/querychat/
git commit -m "feat(pkg-py): wire together multi-table support

Integrates all multi-table components:
- Dictionary storage for data sources
- Per-table reactive state
- Multi-table system prompt
- Parameterized tools

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

### Task 8.2: Update Module Callbacks and Bookmarking

**Files:**
- Modify: `pkg-py/src/querychat/_querychat_module.py`

Update bookmarking to save/restore per-table state:

```python
@session.bookmark.on_bookmark
def _on_bookmark(x: BookmarkState) -> None:
    vals = x.values
    for name, table_state in tables.items():
        vals[f"querychat_{name}_sql"] = table_state.sql.get()
        vals[f"querychat_{name}_title"] = table_state.title.get()
    vals["querychat_has_greeted"] = has_greeted.get()
    vals["querychat_active_table"] = active_table.get()

@session.bookmark.on_restore
def _on_restore(x: RestoreState) -> None:
    vals = x.values
    for name in tables:
        if f"querychat_{name}_sql" in vals:
            tables[name].sql.set(vals[f"querychat_{name}_sql"])
        if f"querychat_{name}_title" in vals:
            tables[name].title.set(vals[f"querychat_{name}_title"])
    # ... etc
```

**Step 1: Implement**

**Step 2: Commit**

```bash
git add pkg-py/src/querychat/_querychat_module.py
git commit -m "feat(pkg-py): update bookmarking for multi-table

Saves and restores per-table SQL, title, and active table state.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

### Task 8.3: Run Lint and Type Checks

**Step 1: Run linter**

Run: `cd pkg-py && uv run ruff check --fix . --config ../pyproject.toml`

**Step 2: Run type checker**

Run: `cd pkg-py && uv run pyright`

**Step 3: Fix any issues**

**Step 4: Run full test suite**

Run: `make py-check`

**Step 5: Commit**

```bash
git add -A
git commit -m "chore(pkg-py): fix lint and type issues

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

### Task 8.4: Update Exports and Documentation

**Files:**
- Modify: `pkg-py/src/querychat/__init__.py`
- Modify: `pkg-py/src/querychat/types.py` (if exists)

**Step 1: Export new classes**

```python
from ._table_accessor import TableAccessor

__all__ = [
    "QueryChat",
    "TableAccessor",
    # ... existing exports
]
```

**Step 2: Commit**

```bash
git add pkg-py/src/querychat/__init__.py
git commit -m "feat(pkg-py): export TableAccessor class

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Summary of Changes

| File | Changes |
|------|---------|
| `_querychat.py` | Dictionary storage, add_table(), remove_table(), table_names(), table() |
| `_table_accessor.py` | New file with TableAccessor class |
| `_querychat_module.py` | Per-table reactive state, updated ServerValues |
| `_system_prompt.py` | Multi-source support, relationships |
| `tools.py` | Table parameter on update/reset tools |
| `prompts/prompt.md` | Multi-table instructions, relationships section |
| `prompts/tool-*.md` | Table parameter documentation |
| `tests/test_multi_table.py` | Comprehensive multi-table tests |

---

Plan complete and saved to `docs/plans/2025-01-14-multi-table-impl.md`.

**Two execution options:**

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

**Which approach?**
