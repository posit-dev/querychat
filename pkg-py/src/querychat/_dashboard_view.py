"""
Server→browser protocol for the dashboard drawer.

WIRE CONTRACT: action names and payload keys here must stay in sync with the
handlers in js/src/dashboard-core.ts (hand-maintained, like the artifact
panel's contract).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from shiny import Session

    from ._dashboard_state import CardLayout


MESSAGE_PREFIX = "querychat-dashboard-"


class DashboardView:
    def __init__(self, session: Session) -> None:
        self.session = session

    async def send(self, action: str, payload: dict) -> None:
        """Send a raw (action, payload) pair; the controller's outbox flush replays through this."""
        await self.session.send_custom_message(f"{MESSAGE_PREFIX}{action}", payload)

    async def set_open(self, *, is_open: bool) -> None:
        await self.send("drawer-toggle", {"open": is_open})

    async def card_upsert(self, name: str, html: str, layout: CardLayout) -> None:
        await self.send(
            "card-upsert",
            {"name": name, "html": html, "layout": layout.model_dump()},
        )

    async def card_remove(self, name: str) -> None:
        await self.send("card-remove", {"name": name})

    async def layout_apply(self, placements: list[dict]) -> None:
        await self.send("layout-apply", {"placements": placements})

    async def canvas_reset(self, *, title: str) -> None:
        """Clear all canvas items client-side (undo/redo and restore re-sync)."""
        await self.send("canvas-reset", {"title": title})

    async def set_badge(self, count: int) -> None:
        await self.send("badge", {"count": count})

    async def palette_update(self, html: str) -> None:
        await self.send("palette", {"html": html})

    async def set_autogen(self, *, active: bool) -> None:
        await self.send("autogen", {"active": active})

    async def set_history_buttons(self, *, can_undo: bool, can_redo: bool) -> None:
        await self.send("history", {"can_undo": can_undo, "can_redo": can_redo})
