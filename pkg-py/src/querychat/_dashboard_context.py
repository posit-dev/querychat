"""
LLM-facing context for the canvas (pieces pattern: inject fresh state into
every user turn while the drawer is open, never a stale system prompt).
The ASCII grid is a *derived rendering* for legibility — the JSON spec is
the source of truth the LLM mutates via the canvas tools.
"""

from __future__ import annotations

import json
import string
from typing import TYPE_CHECKING

from ._dashboard_state import GRID_COLUMNS

if TYPE_CHECKING:
    from ._dashboard_state import DashboardSpec


def render_grid_ascii(spec: DashboardSpec) -> str:
    placed = spec.on_canvas()
    if not placed:
        return "(canvas is empty)"

    rows = max(c.layout.y + c.layout.h for c in placed if c.layout is not None)
    grid = [["." for _ in range(GRID_COLUMNS)] for _ in range(rows)]
    legend: list[str] = []

    letters = string.ascii_uppercase
    for i, card in enumerate(placed):
        mark = letters[i % len(letters)]
        lay = card.layout
        if lay is None:  # on_canvas() guarantees this can't happen
            continue
        for y in range(lay.y, lay.y + lay.h):
            for x in range(lay.x, min(lay.x + lay.w, GRID_COLUMNS)):
                grid[y][x] = mark
        legend.append(f"{mark} = {card.name} ({card.type}, {lay.w}x{lay.h})")

    grid_text = "\n".join("".join(row) for row in grid)
    return f"{grid_text}\n" + "\n".join(legend)


def build_canvas_context(spec: DashboardSpec) -> str:
    cards_json = json.dumps(
        [c.model_dump(exclude={"controls"}) for c in spec.cards],
        indent=2,
        default=str,
    )
    hidden = [c.name for c in spec.cards if c.layout is None]
    hidden_note = (
        f"Off-canvas cards (re-place via querychat_canvas_arrange): {', '.join(hidden)}"
        if hidden
        else "No off-canvas cards."
    )
    return (
        "<dashboard-canvas-state>\n"
        "The user's dashboard drawer is open. Current canvas "
        f"(12-column grid, title: {spec.title!r}):\n\n"
        f"{render_grid_ascii(spec)}\n\n"
        f"{hidden_note}\n\n"
        f"Full card specs:\n```json\n{cards_json}\n```\n"
        "</dashboard-canvas-state>"
    )
