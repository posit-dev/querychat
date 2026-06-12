from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from shiny.types import NotifyException

from shiny import reactive, render, ui

from ._artifact_orchestrator import ArtifactOrchestrator, parse_generate_payload

if TYPE_CHECKING:
    import chatlas
    import shinychat
    from shiny.bookmark import BookmarkState, RestoreState

    from shiny import Inputs, Session

    from ._artifact_gallery import GalleryItem
    from ._artifact_prompt import Recommendation
    from ._datasource import DataSource


ARTIFACTS_BOOKMARK_KEY = "querychat_artifacts"


def artifact_server(
    input: Inputs,
    session: Session,
    chat: chatlas.Chat,
    data_source: DataSource,
    chat_ui: shinychat.Chat,
    *,
    enable_bookmarking: bool = False,
) -> None:
    orch = ArtifactOrchestrator(session, chat, data_source, chat_ui)
    active_artifact_id: reactive.Value[str | None] = reactive.Value(None)

    @reactive.extended_task
    async def recommend_task(items: list[GalleryItem]) -> Recommendation:
        return await orch.recommend(items)

    @chat_ui.slash_command("artifact", "Create an artifact")
    async def open_artifact_modal():
        with reactive.isolate():
            stream_status = chat_ui.latest_message_stream.status()
        if stream_status == "running":
            await chat_ui.append_message(
                "Please wait for the current response to finish before creating an artifact."
            )
            return

        items = orch.open_modal()

        # Cancel any in-flight recommend from a prior modal session. invoke()
        # queues rather than replaces, so without this a recommend started for a
        # previous modal would complete and populate this freshly-opened one with
        # stale selections (whose item IDs may not even exist in this gallery).
        recommend_task.cancel()
        if items:
            recommend_task.invoke(items)

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
    @reactive.event(input.artifact_generate)
    async def on_generate():
        req = parse_generate_payload(input.artifact_generate(), orch.default_type_id)
        if req.type_id == "other" and not req.freeform:
            ui.notification_show(
                "Please enter a format name for 'Other'.",
                type="warning",
            )
            return
        try:
            directions = input.artifact_directions() or ""
        except Exception:
            directions = ""

        # Set the active id up front so `sync_panel_visibility` opens the panel
        # for the incoming stream; reset it on failure so the panel closes.
        artifact_id = uuid.uuid4().hex
        active_artifact_id.set(artifact_id)
        try:
            await orch.generate(req, directions, artifact_id)
        except Exception as e:
            active_artifact_id.set(None)
            raise NotifyException(str(e)) from e

    @reactive.effect
    @reactive.event(input.artifact_close)
    def on_close():
        active_artifact_id.set(None)

    @reactive.effect
    @reactive.event(input.artifact_open)
    async def on_pill_click():
        artifact_id = input.artifact_open()
        if orch.store.has(artifact_id):
            active_artifact_id.set(artifact_id)
            await orch.show_version(artifact_id)

    @reactive.effect
    async def sync_panel_visibility():
        await orch.view.set_panel_open(is_open=active_artifact_id.get() is not None)

    @reactive.effect
    @reactive.event(input.artifact_revise_text)
    async def on_revise():
        try:
            await orch.revise(active_artifact_id.get(), input.artifact_revise_text())
        except Exception as e:
            raise NotifyException(str(e)) from e
        # A revision streams into the editor without appending a chat message, so
        # shinychat's message-driven auto-bookmark never fires. Re-trigger it here
        # so the revised version is captured (and restored) in the bookmark.
        if enable_bookmarking:
            await session.bookmark()

    @reactive.effect
    @reactive.event(input.artifact_version_prev)
    async def on_version_prev():
        await orch.step_version(active_artifact_id.get(), -1)

    @reactive.effect
    @reactive.event(input.artifact_version_next)
    async def on_version_next():
        await orch.step_version(active_artifact_id.get(), 1)

    @render.download(filename="artifact.zip")
    async def artifact_download():
        data = await orch.build_download(active_artifact_id.get())
        if data is not None:
            yield data

    if enable_bookmarking:

        @session.bookmark.on_bookmark
        def _on_artifact_bookmark(state: BookmarkState) -> None:
            values = orch.store.bookmark_values()
            if values:
                state.values[ARTIFACTS_BOOKMARK_KEY] = values

        @session.bookmark.on_restore
        def _on_artifact_restore(state: RestoreState) -> None:
            saved = state.values.get(ARTIFACTS_BOOKMARK_KEY)
            if saved:
                orch.restore_from_bookmark(saved)
