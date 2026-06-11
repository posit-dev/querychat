"""Canvas tool definitions: the LLM's editing surface for the dashboard drawer."""

from __future__ import annotations

from typing import TYPE_CHECKING

from chatlas import ContentToolResult, Tool
from shinychat.types import ToolResultDisplay

from ._dashboard_cards import validate_card
from ._dashboard_state import CardSpec, Placement
from ._icons import bs_icon
from ._tool_names import (
    TOOL_CANVAS_ARRANGE,
    TOOL_CANVAS_REMOVE_CARD,
    TOOL_CANVAS_SET_CARDS,
)
from ._utils import read_prompt_template, truncate_error

if TYPE_CHECKING:
    from collections.abc import Callable

    from ._datasource import DataSource


def canvas_display(markdown: str, title: str) -> dict:
    return {
        "display": ToolResultDisplay(
            markdown=markdown,
            title=title,
            show_request=False,
            open=False,
            icon=bs_icon("grid-1x2-fill"),
        ),
    }


def tool_canvas_set_cards(
    data_source: DataSource,
    set_fn: Callable[[list[CardSpec]], None],
) -> Tool:
    def canvas_set_cards(cards: list[dict]) -> ContentToolResult:
        parsed: list[CardSpec] = []
        errors: list[str] = []
        for i, raw in enumerate(cards):
            try:
                card = CardSpec.model_validate(raw)
                validate_card(data_source, card)
                parsed.append(card)
            except Exception as e:  # noqa: PERF203 (per-card error collection is intentional)
                label = raw.get("name", f"card {i}") if isinstance(raw, dict) else f"card {i}"
                errors.append(f"{label}: {truncate_error(str(e))}")
        if errors:
            # All-or-nothing: predictable for the LLM, no half-applied canvas.
            msg = "No cards applied. Errors:\n- " + "\n- ".join(errors)
            return ContentToolResult(value=msg, error=Exception(msg))

        set_fn(parsed)
        names = ", ".join(c.name for c in parsed)
        value = f"Applied {len(parsed)} card(s) to the canvas: {names}."
        return ContentToolResult(
            value=value,
            extra=canvas_display(value, "Dashboard updated"),
        )

    canvas_set_cards.__doc__ = read_prompt_template(
        "tool-canvas-set-cards.md", db_type=data_source.get_db_type()
    )
    return Tool.from_func(
        canvas_set_cards,
        name=TOOL_CANVAS_SET_CARDS,
        annotations={"title": "Update Dashboard Canvas"},
    )


def tool_canvas_arrange(
    arrange_fn: Callable[[list[Placement]], None],
) -> Tool:
    def canvas_arrange(placements: list[dict]) -> ContentToolResult:
        try:
            parsed = [Placement.model_validate(p) for p in placements]
            arrange_fn(parsed)
        except KeyError as e:
            msg = f"Unknown card name: {e}. Nothing was moved."
            return ContentToolResult(value=msg, error=Exception(msg))
        except Exception as e:
            msg = truncate_error(str(e))
            return ContentToolResult(value=msg, error=Exception(msg))
        value = f"Rearranged {len(parsed)} card(s)."
        return ContentToolResult(
            value=value, extra=canvas_display(value, "Canvas rearranged")
        )

    canvas_arrange.__doc__ = read_prompt_template("tool-canvas-arrange.md")
    return Tool.from_func(
        canvas_arrange,
        name=TOOL_CANVAS_ARRANGE,
        annotations={"title": "Arrange Dashboard Canvas"},
    )


def tool_canvas_remove_card(
    remove_fn: Callable[[str], None],
) -> Tool:
    def canvas_remove_card(name: str) -> ContentToolResult:
        try:
            remove_fn(name)
        except KeyError:
            msg = f"No card named '{name}' on the canvas."
            return ContentToolResult(value=msg, error=Exception(msg))
        value = f"Removed '{name}' from the canvas (it remains in the palette)."
        return ContentToolResult(
            value=value, extra=canvas_display(value, "Card removed")
        )

    canvas_remove_card.__doc__ = read_prompt_template("tool-canvas-remove-card.md")
    return Tool.from_func(
        canvas_remove_card,
        name=TOOL_CANVAS_REMOVE_CARD,
        annotations={"title": "Remove Canvas Card"},
    )
