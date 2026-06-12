"""
Dashboard drawer server logic.

`DashboardController` is plain Python (testable without Shiny): it owns the
spec, history, validation/rendering, and an outbox of pending browser
messages. `dashboard_server()` wires it into Shiny: slash command, client
inputs, the outbox flush, autogen, and bookmarking.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from shiny import reactive, ui

from ._artifact_gallery import extract_gallery_items
from ._dashboard_autogen import generate_first_pass
from ._dashboard_cards import card_html, validate_card
from ._dashboard_context import build_canvas_context
from ._dashboard_palette import (
    PaletteItem,
    card_for_palette_item,
    palette_from_gallery,
)
from ._dashboard_state import (
    CardLayout,
    CardSpec,
    DashboardHistory,
    DashboardSpec,
    Placement,
)
from ._dashboard_ui import palette_html
from ._dashboard_view import DashboardView

if TYPE_CHECKING:
    from collections.abc import Callable

    import chatlas
    import shinychat
    from shiny.bookmark import BookmarkState, RestoreState

    from shiny import Inputs, Session

    from ._datasource import DataSource

DASHBOARD_BOOKMARK_KEY = "querychat_dashboard"

# (action, payload) pairs queued for the browser; flushed by dashboard_server.
Outbound = tuple[str, dict[str, Any]]


class DashboardController:
    def __init__(self, data_source: DataSource) -> None:
        self.data_source = data_source
        self.spec = DashboardSpec()
        self.history = DashboardHistory(self.spec)
        self.outbox: list[Outbound] = []
        self.opened_once = False

    # ---- staging (callable from tool callbacks, mid-stream, sync) ----

    def stage_set_cards(self, cards: list[CardSpec]) -> None:
        for card in cards:
            if card.layout is None:
                existing = self.spec.get_card(card.name)
                card.layout = (
                    existing.layout
                    if existing is not None and existing.layout is not None
                    else CardLayout(x=0, y=self.spec.next_free_y(), w=6, h=3)
                )
            self.spec.upsert_card(card)
            html = card_html(self.data_source, card)
            self.outbox.append(
                (
                    "card-upsert",
                    {
                        "name": card.name,
                        "html": html,
                        "layout": card.layout.model_dump(),
                    },
                )
            )
        self.history.record(self.spec)
        self.queue_chrome()

    def stage_arrange(self, placements: list[Placement]) -> None:
        # apply_placements is atomic: raises KeyError before mutating anything.
        self.spec.apply_placements(placements)
        for p in placements:
            card = self.spec.get_card(p.name)
            # apply_placements verified every name exists and assigned layout,
            # so card is never None and layout is never None here.
            if card is None or card.layout is None:
                continue
            self.outbox.append(
                (
                    "card-upsert",
                    {
                        "name": card.name,
                        "html": card_html(self.data_source, card),
                        "layout": card.layout.model_dump(),
                    },
                )
            )
        self.history.record(self.spec)
        self.queue_chrome()

    def stage_remove(self, name: str) -> None:
        if self.spec.get_card(name) is None:
            raise KeyError(name)
        self.spec.remove_card(name)
        self.outbox.append(("card-remove", {"name": name}))
        self.history.record(self.spec)
        self.queue_chrome()

    # ---- direct manipulation (reactive context) ----

    def apply_browser_layout(self, placements: list[dict]) -> None:
        parsed = [Placement.model_validate(p) for p in placements]
        known = [p for p in parsed if self.spec.get_card(p.name) is not None]
        self.spec.apply_placements(known)
        self.history.record(self.spec)
        # No card-upsert needed: the browser already shows the new layout.
        self.queue_chrome()

    def add_palette_item(self, item: PaletteItem) -> None:
        taken = {c.name for c in self.spec.cards}
        card = card_for_palette_item(item, taken_names=taken)
        validate_card(self.data_source, card)
        self.stage_set_cards([card])

    def undo(self) -> bool:
        restored = self.history.undo()
        if restored is None:
            return False
        self.spec = restored
        self.queue_full_resync()
        return True

    def redo(self) -> bool:
        restored = self.history.redo()
        if restored is None:
            return False
        self.spec = restored
        self.queue_full_resync()
        return True

    def replace_spec(self, spec: DashboardSpec) -> None:
        self.spec = spec
        self.history.record(self.spec)
        self.queue_full_resync()

    # ---- outbox ----

    def queue_full_resync(self) -> None:
        self.outbox.append(("canvas-reset", {"title": self.spec.title}))
        for card in self.spec.on_canvas():
            if card.layout is None:
                continue
            self.outbox.append(
                (
                    "card-upsert",
                    {
                        "name": card.name,
                        "html": card_html(self.data_source, card),
                        "layout": card.layout.model_dump(),
                    },
                )
            )
        self.queue_chrome()

    def queue_chrome(self) -> None:
        self.outbox.append(
            (
                "history",
                {
                    "can_undo": self.history.can_undo(),
                    "can_redo": self.history.can_redo(),
                },
            )
        )
        self.outbox.append(("badge", {"count": len(self.spec.on_canvas())}))

    def drain_outbox(self) -> list[Outbound]:
        drained, self.outbox = self.outbox, []
        return drained

    # ---- persistence ----

    def bookmark_value(self) -> dict:
        return self.spec.model_dump(mode="json")

    def restore_from_bookmark(self, value: dict) -> None:
        self.spec = DashboardSpec.model_validate(value)
        self.history = DashboardHistory(self.spec)

    # ---- LLM context ----

    def canvas_context(self) -> str:
        return build_canvas_context(self.spec)


def dashboard_server(
    input: Inputs,
    session: Session,
    controller: DashboardController,
    chat: chatlas.Chat,
    chat_ui: shinychat.Chat,
    *,
    enable_bookmarking: bool = False,
) -> Callable[[], None]:
    view = DashboardView(session)
    drawer_open = reactive.value(False)  # noqa: FBT003
    flush_requested = reactive.value(0)

    # reactive.Value.set works from non-reactive contexts (update_dashboard's
    # sql.set in _shiny_module.py proves the pattern); a counter guarantees
    # the value actually changes so the effect re-runs.
    flush_count = {"n": 0}

    def bump_flush() -> None:
        flush_count["n"] += 1
        flush_requested.set(flush_count["n"])

    @reactive.effect
    @reactive.event(flush_requested)
    async def flush_outbox():
        for action, payload in controller.drain_outbox():
            await view.send(action, payload)

    async def open_drawer() -> None:
        drawer_open.set(True)
        await view.set_open(is_open=True)
        await refresh_palette()
        if not controller.opened_once:
            controller.opened_once = True
            if not controller.spec.cards:
                autogen_task.invoke()
        controller.queue_full_resync()
        bump_flush()

    @reactive.extended_task
    async def autogen_task() -> DashboardSpec:
        items = palette_from_gallery(
            extract_gallery_items(chat.get_turns()), controller.spec
        )
        return await generate_first_pass(chat, controller.data_source, items)

    @reactive.effect
    @reactive.event(autogen_task.status)
    async def on_autogen_complete():
        status = autogen_task.status()
        if status == "running":
            await view.set_autogen(active=True)
            return
        await view.set_autogen(active=False)
        if status == "success":
            controller.replace_spec(autogen_task.result())
            bump_flush()
        elif status == "error":
            ui.notification_show(
                "Could not auto-generate a dashboard; start from the palette.",
                type="warning",
            )

    @chat_ui.slash_command("dashboard", "Open your dashboard")
    async def on_slash_dashboard():
        await open_drawer()

    @reactive.effect
    @reactive.event(input.dashboard_open)
    async def on_badge_click():
        await open_drawer()

    @reactive.effect
    @reactive.event(input.dashboard_close)
    async def on_close():
        drawer_open.set(False)
        await view.set_open(is_open=False)

    @reactive.effect
    @reactive.event(input.dashboard_layout_change)
    def on_layout_change():
        payload = input.dashboard_layout_change()
        if isinstance(payload, list):
            controller.apply_browser_layout(payload)
            bump_flush()

    @reactive.effect
    @reactive.event(input.dashboard_remove_card)
    def on_remove_card():
        name = input.dashboard_remove_card()
        if isinstance(name, str) and controller.spec.get_card(name) is not None:
            controller.stage_remove(name)
            bump_flush()

    @reactive.effect
    @reactive.event(input.dashboard_palette_add)
    async def on_palette_add():
        payload = input.dashboard_palette_add()
        if not isinstance(payload, dict):
            return
        items = palette_from_gallery(
            extract_gallery_items(chat.get_turns()), controller.spec
        )
        match = next((i for i in items if i.id == payload.get("id")), None)
        if match is None:
            return
        try:
            controller.add_palette_item(match)
        except ValueError as e:
            ui.notification_show(f"Could not add card: {e}", type="error")
            return
        await refresh_palette()
        bump_flush()

    @reactive.effect
    @reactive.event(input.dashboard_pin)
    async def on_pin():
        payload = input.dashboard_pin()
        if not isinstance(payload, dict):
            return
        kind = payload.get("kind")
        source = payload.get("source", "")
        title = payload.get("title", "Pinned result")
        if kind not in ("chart", "table") or not source:
            return
        taken = {c.name for c in controller.spec.cards}
        item = PaletteItem(
            id="pin",
            kind=kind,
            title=title,
            source=source,
            thumbnail=None,
            preview_html=None,
            on_canvas=False,
        )
        try:
            card = card_for_palette_item(item, taken_names=taken)
            validate_card(controller.data_source, card)
            controller.stage_set_cards([card])
        except ValueError as e:
            ui.notification_show(f"Could not pin: {e}", type="error")
            return
        bump_flush()
        ui.notification_show(f'Pinned "{title}" to your dashboard.', type="message")

    @reactive.effect
    @reactive.event(input.dashboard_undo)
    def on_undo():
        if controller.undo():
            bump_flush()

    @reactive.effect
    @reactive.event(input.dashboard_redo)
    def on_redo():
        if controller.redo():
            bump_flush()

    async def refresh_palette() -> None:
        items = palette_from_gallery(
            extract_gallery_items(chat.get_turns()), controller.spec
        )
        await view.palette_update(palette_html(items))

    if enable_bookmarking:

        @session.bookmark.on_bookmark
        def on_dashboard_bookmark(state: BookmarkState) -> None:
            if controller.spec.cards:
                state.values[DASHBOARD_BOOKMARK_KEY] = controller.bookmark_value()

        @session.bookmark.on_restore
        def on_dashboard_restore(state: RestoreState) -> None:
            saved = state.values.get(DASHBOARD_BOOKMARK_KEY)
            if saved:
                controller.restore_from_bookmark(saved)
                # Don't autogen over restored work
                controller.opened_once = True

    return bump_flush
