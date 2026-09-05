from __future__ import annotations

import asyncio
import uuid
from typing import TYPE_CHECKING, Any

from shiny.types import NotifyException

from shiny import reactive, render, ui

from ._handoff_orchestrator import HandoffOrchestrator, parse_generate_payload

if TYPE_CHECKING:
    from collections.abc import Coroutine

    import chatlas
    import shinychat
    from shiny.bookmark import BookmarkState, RestoreState

    from shiny import Inputs, Session

    from ._datasource import DataSource
    from ._handoff_gallery import GalleryItem
    from ._handoff_orchestrator import GenerateRequest
    from ._handoff_prompt import Recommendation
    from ._query_executor import QueryExecutor


HANDOFFS_BOOKMARK_KEY = "querychat_handoffs"


def open_handoff_creator(
    orchestrator: HandoffOrchestrator,
    recommend_task: reactive.ExtendedTask[[list[GalleryItem]], Recommendation],
) -> None:
    items = orchestrator.open_modal()
    # Extended tasks queue repeated invocations, so discard a recommendation
    # started for a previous modal before requesting one for this gallery.
    recommend_task.cancel()
    if items:
        recommend_task.invoke(items)


async def set_active_handoff(
    orchestrator: HandoffOrchestrator,
    active_handoff_id: reactive.Value[str | None],
    handoff_id: str | None,
) -> None:
    active_handoff_id.set(handoff_id)
    await orchestrator.view.set_panel_open(is_open=handoff_id is not None)


def build_handoff_snapshot(
    orchestrator: HandoffOrchestrator,
) -> list[dict[str, Any]]:
    return orchestrator.store.bookmark_values()


def apply_handoff_snapshot(
    orchestrator: HandoffOrchestrator,
    values: object,
    active_handoff_id: reactive.Value[str | None],
) -> Coroutine[Any, Any, None] | None:
    if values is None:
        orchestrator.restore_snapshot([])
    elif isinstance(values, list):
        orchestrator.restore_snapshot(values)
    else:
        return None
    active_handoff_id.set(None)
    return orchestrator.view.set_panel_open(is_open=False)


def finish_handoff_restore_task(
    task: asyncio.Task[None],
    restore_tasks: set[asyncio.Task[None]],
) -> None:
    restore_tasks.discard(task)
    if task.cancelled():
        return
    try:
        task.result()
    except Exception as error:
        ui.notification_show(
            f"Failed to close the handoff panel after state restore: {error}",
            type="error",
            duration=None,
        )


async def save_handoff_revision(
    shinychat_chat: shinychat.Chat,
) -> None:
    await shinychat_chat.history.save()


async def generate_and_save_handoff(
    orchestrator: HandoffOrchestrator,
    request: GenerateRequest,
    directions: str,
    handoff_id: str,
    *,
    shinychat_chat: shinychat.Chat,
) -> None:
    await orchestrator.generate(request, directions, handoff_id)
    await save_handoff_revision(shinychat_chat)


def handoff_server(
    input: Inputs,
    session: Session,
    chat: chatlas.Chat,
    *,
    data_sources: dict[str, DataSource],
    executor: QueryExecutor,
    shinychat_chat: shinychat.Chat,
) -> None:
    orch = HandoffOrchestrator(
        session,
        chat,
        data_sources,
        executor,
        shinychat_chat,
    )
    active_handoff_id: reactive.Value[str | None] = reactive.Value(None)
    restore_tasks: set[asyncio.Task[None]] = set()

    @reactive.extended_task
    async def recommend_task(items: list[GalleryItem]) -> Recommendation:
        return await orch.recommend(items)

    @shinychat_chat.slash_command(
        "handoff",
        "Prepare a shareable handoff document or webapp using the current chat context.",
        echo=False,
    )
    async def open_handoff_modal():
        with reactive.isolate():
            stream_status = shinychat_chat.latest_message_stream.status()
        if stream_status == "running":
            await shinychat_chat.append_message(
                "Please wait for the current response to finish before preparing a handoff."
            )
            return

        open_handoff_creator(orch, recommend_task)

    @reactive.effect
    @reactive.event(recommend_task.status)
    async def on_recommend_complete():
        status = recommend_task.status()
        if status == "success":
            await orch.view.show_recommendation(recommend_task.result())
        elif status == "error":
            try:
                recommend_task.result()
            except Exception as e:
                error_msg = str(e)
            else:
                error_msg = "Unknown error"
            ui.notification_show(
                f"Auto-recommend failed: {error_msg}",
                type="error",
                duration=None,
            )
            await orch.view.show_recommendation_error(error_msg)

    @reactive.effect
    @reactive.event(input.handoff_generate)
    async def on_generate():
        req = parse_generate_payload(input.handoff_generate(), orch.default_type_id)
        if req.type_id == "other" and not req.freeform:
            ui.notification_show(
                "Please enter a format name for 'Other'.",
                type="warning",
            )
            return
        try:
            directions = input.handoff_directions() or ""
        except Exception:
            directions = ""

        # Open the panel before generation yields its first streamed source chunk.
        handoff_id = uuid.uuid4().hex
        await set_active_handoff(orch, active_handoff_id, handoff_id)
        try:
            await generate_and_save_handoff(
                orch,
                req,
                directions,
                handoff_id,
                shinychat_chat=shinychat_chat,
            )
        except Exception as e:
            if not orch.store.has(handoff_id):
                await set_active_handoff(orch, active_handoff_id, None)
            raise NotifyException(str(e)) from e

    @reactive.effect
    @reactive.event(input.handoff_close)
    async def on_close():
        await set_active_handoff(orch, active_handoff_id, None)

    @reactive.effect
    @reactive.event(input.handoff_open)
    async def on_pill_click():
        handoff_id = input.handoff_open()
        if orch.store.has(handoff_id):
            await set_active_handoff(orch, active_handoff_id, handoff_id)
            await orch.show_handoff(handoff_id)

    @reactive.effect
    @reactive.event(input.handoff_revise_text)
    async def on_revise():
        try:
            await orch.revise(active_handoff_id.get(), input.handoff_revise_text())
        except Exception as e:
            raise NotifyException(str(e)) from e
        await save_handoff_revision(shinychat_chat)

    @render.download(filename="handoff.zip")
    async def handoff_download():
        data = await orch.build_download(active_handoff_id.get())
        if data is not None:
            yield data

    def save_handoffs(values: dict[str, Any]) -> None:
        snapshot = build_handoff_snapshot(orch)
        if snapshot:
            values[HANDOFFS_BOOKMARK_KEY] = snapshot

    def restore_handoffs(values: dict[str, Any]) -> None:
        panel_close = apply_handoff_snapshot(
            orch,
            values.get(HANDOFFS_BOOKMARK_KEY),
            active_handoff_id,
        )
        if panel_close is None:
            return
        task = asyncio.create_task(panel_close)
        restore_tasks.add(task)
        task.add_done_callback(
            lambda completed: finish_handoff_restore_task(
                completed,
                restore_tasks,
            )
        )

    @session.bookmark.on_bookmark
    def on_handoff_bookmark(state: BookmarkState) -> None:
        save_handoffs(state.values)

    @session.bookmark.on_restore
    def on_handoff_bookmark_restore(state: RestoreState) -> None:
        restore_handoffs(state.values)

    @shinychat_chat.history.on_save
    def on_handoff_history_save(values: dict[str, Any]) -> None:
        save_handoffs(values)

    @shinychat_chat.history.on_restore
    def on_handoff_history_restore(values: dict[str, Any]) -> None:
        restore_handoffs(values)
