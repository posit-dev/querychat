from chatlas import ContentToolRequest, ContentToolResult, Turn
from chatlas._content import ContentImageInline
from querychat._artifact_gallery import (
    QueryGalleryItem,
    VizGalleryItem,
    extract_gallery_items,
)


def _make_viz_result(
    title: str = "Sales Chart",
    ggsql: str = "SELECT x, y FROM t VISUALISE x, y DRAW point",
    png_b64: str | None = "iVBORw0KGgo=",
    error: Exception | None = None,
) -> ContentToolResult:
    request = ContentToolRequest(
        id="call_1",
        name="querychat_visualize",
        arguments={"ggsql": ggsql, "title": title},
    )
    if error:
        return ContentToolResult(value="", error=error, request=request)
    value: list = [f"Visualization: {title}"]
    if png_b64 is not None:
        value.append(ContentImageInline(image_content_type="image/png", data=png_b64))
    return ContentToolResult(value=value, request=request)


def _make_query_result(
    sql: str = "SELECT COUNT(*) FROM t",
    intent: str = "Count all rows",
    error: Exception | None = None,
) -> ContentToolResult:
    request = ContentToolRequest(
        id="call_2",
        name="querychat_query",
        arguments={"query": sql, "_intent": intent},
    )
    if error:
        return ContentToolResult(value="", error=error, request=request)
    return ContentToolResult(value=[{"count": 42}], request=request)


def _make_update_result() -> ContentToolResult:
    request = ContentToolRequest(
        id="call_3",
        name="querychat_update_dashboard",
        arguments={"query": "SELECT * FROM t", "title": "Filtered"},
    )
    return ContentToolResult(value="Dashboard updated", request=request)


def _turns_from_results(*results: ContentToolResult) -> list[Turn]:
    # Simulate chatlas's behavior of hoisting ContentImageInline from
    # ContentToolResult.value into the surrounding turn contents.
    contents: list = []
    for result in results:
        contents.append(result)
        if isinstance(result.value, list):
            contents.extend(
                item for item in result.value if isinstance(item, ContentImageInline)
            )
    return [Turn(role="assistant", contents=contents)]


class TestExtractGalleryItems:
    def test_extracts_viz_item(self):
        turns = _turns_from_results(_make_viz_result())
        items = extract_gallery_items(turns)
        assert len(items) == 1
        item = items[0]
        assert isinstance(item, VizGalleryItem)
        assert item.title == "Sales Chart"
        assert item.ggsql == "SELECT x, y FROM t VISUALISE x, y DRAW point"
        assert item.thumbnail == "data:image/png;base64,iVBORw0KGgo="

    def test_viz_without_thumbnail(self):
        turns = _turns_from_results(_make_viz_result(png_b64=None))
        items = extract_gallery_items(turns)
        assert len(items) == 1
        assert isinstance(items[0], VizGalleryItem)
        assert items[0].thumbnail is None

    def test_extracts_query_item(self):
        turns = _turns_from_results(_make_query_result())
        items = extract_gallery_items(turns)
        assert len(items) == 1
        item = items[0]
        assert isinstance(item, QueryGalleryItem)
        assert item.title == "Count all rows"
        assert item.sql == "SELECT COUNT(*) FROM t"

    def test_query_empty_intent_falls_back_to_sql(self):
        turns = _turns_from_results(
            _make_query_result(sql="SELECT x, y FROM long_table_name", intent="")
        )
        items = extract_gallery_items(turns)
        assert len(items) == 1
        assert items[0].title.startswith("SELECT x, y")

    def test_skips_errored_query(self):
        turns = _turns_from_results(_make_query_result(error=Exception("bad sql")))
        items = extract_gallery_items(turns)
        assert len(items) == 0

    def test_skips_errored_viz(self):
        turns = _turns_from_results(
            _make_viz_result(error=Exception("ggsql render failed"))
        )
        items = extract_gallery_items(turns)
        assert len(items) == 0

    def test_extracts_update_dashboard(self):
        turns = _turns_from_results(_make_update_result())
        items = extract_gallery_items(turns)
        assert len(items) == 1
        item = items[0]
        assert isinstance(item, QueryGalleryItem)
        assert item.title == "Filtered"
        assert item.sql == "SELECT * FROM t"

    def test_mixed_results_ordered(self):
        turns = _turns_from_results(
            _make_viz_result(title="Chart A"),
            _make_query_result(intent="Query B"),
            _make_viz_result(title="Chart C"),
        )
        items = extract_gallery_items(turns)
        assert len(items) == 3
        assert items[0].title == "Chart A"
        assert items[1].title == "Query B"
        assert items[2].title == "Chart C"

    def test_empty_turns(self):
        items = extract_gallery_items([])
        assert items == []

    def test_skips_tool_result_without_request(self):
        result = ContentToolResult(value="orphan")
        turns = [Turn(role="assistant", contents=[result])]
        items = extract_gallery_items(turns)
        assert len(items) == 0

    def test_unique_ids(self):
        turns = _turns_from_results(
            _make_viz_result(title="A"),
            _make_viz_result(title="B"),
            _make_query_result(intent="C"),
        )
        items = extract_gallery_items(turns)
        ids = [item.id for item in items]
        assert len(ids) == len(set(ids))
