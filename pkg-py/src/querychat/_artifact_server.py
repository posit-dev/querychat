from __future__ import annotations

import asyncio
import uuid
from typing import TYPE_CHECKING, Any

from shiny.types import NotifyException

from shiny import reactive, render, ui

from ._artifact_orchestrator import ArtifactOrchestrator, parse_generate_payload

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine

    import chatlas
    import shinychat

    from shiny import Inputs, Session

    from ._artifact_gallery import GalleryItem
    from ._artifact_orchestrator import GenerateRequest
    from ._artifact_prompt import Recommendation
    from ._datasource import DataSource
    from ._query_executor import QueryExecutor


ARTIFACTS_BOOKMARK_KEY = "querychat_artifacts"


def open_artifact_creator(
    orchestrator: ArtifactOrchestrator,
    recommend_task: reactive.ExtendedTask[[list[GalleryItem]], Recommendation],
) -> None:
    items = orchestrator.open_modal()
    # Extended tasks queue repeated invocations, so discard a recommendation
    # started for a previous modal before requesting one for this gallery.
    recommend_task.cancel()
    if items:
        recommend_task.invoke(items)


async def set_active_artifact(
    orchestrator: ArtifactOrchestrator,
    active_artifact_id: reactive.Value[str | None],
    artifact_id: str | None,
) -> None:
    active_artifact_id.set(artifact_id)
    await orchestrator.view.set_panel_open(is_open=artifact_id is not None)


def build_artifact_snapshot(
    orchestrator: ArtifactOrchestrator,
) -> list[dict[str, Any]]:
    return orchestrator.store.bookmark_values()


def apply_artifact_snapshot(
    orchestrator: ArtifactOrchestrator,
    values: object,
    active_artifact_id: reactive.Value[str | None],
) -> Coroutine[Any, Any, None] | None:
    if values is None:
        orchestrator.restore_snapshot([])
    elif isinstance(values, list):
        orchestrator.restore_snapshot(values)
    else:
        return None
    active_artifact_id.set(None)
    return orchestrator.view.set_panel_open(is_open=False)


def finish_artifact_restore_task(
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
            f"Failed to close the artifact panel after history restore: {error}",
            type="error",
            duration=None,
        )


async def save_artifact_revision(
    shinychat_chat: shinychat.Chat,
) -> None:
    await shinychat_chat.history.save()


async def step_artifact_version(
    orchestrator: ArtifactOrchestrator,
    artifact_id: str | None,
    delta: int,
    shinychat_chat: shinychat.Chat,
) -> None:
    changed = await orchestrator.step_version(artifact_id, delta)
    if changed:
        await save_artifact_revision(shinychat_chat)


async def generate_and_save_artifact(
    orchestrator: ArtifactOrchestrator,
    request: GenerateRequest,
    directions: str,
    artifact_id: str,
    shinychat_chat: shinychat.Chat,
) -> None:
    await orchestrator.generate(request, directions, artifact_id)
    await save_artifact_revision(shinychat_chat)


def artifact_server(
    input: Inputs,
    session: Session,
    chat: chatlas.Chat,
    *,
    data_sources: dict[str, DataSource],
    executor: QueryExecutor,
    shinychat_chat: shinychat.Chat,
) -> Callable[[], None]:
    orch = ArtifactOrchestrator(
        session,
        chat,
        data_sources,
        executor,
        shinychat_chat,
    )
    active_artifact_id: reactive.Value[str | None] = reactive.Value(None)
    restore_tasks: set[asyncio.Task[None]] = set()

    @reactive.extended_task
    async def recommend_task(items: list[GalleryItem]) -> Recommendation:
        return await orch.recommend(items)

    @shinychat_chat.slash_command(
        "artifact",
        "Create an artifact",
        echo=False,
    )
    async def open_artifact_modal():
        with reactive.isolate():
            stream_status = shinychat_chat.latest_message_stream.status()
        if stream_status == "running":
            await shinychat_chat.append_message(
                "Please wait for the current response to finish before creating an artifact."
            )
            return

        open_artifact_creator(orch, recommend_task)

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

        # Open the panel before generation yields its first streamed source chunk.
        artifact_id = uuid.uuid4().hex
        await set_active_artifact(orch, active_artifact_id, artifact_id)
        try:
            await generate_and_save_artifact(
                orch,
                req,
                directions,
                artifact_id,
                shinychat_chat,
            )
        except Exception as e:
            if not orch.store.has(artifact_id):
                await set_active_artifact(orch, active_artifact_id, None)
            raise NotifyException(str(e)) from e

    @reactive.effect
    @reactive.event(input.artifact_close)
    async def on_close():
        await set_active_artifact(orch, active_artifact_id, None)

    @reactive.effect
    @reactive.event(input.artifact_open)
    async def on_pill_click():
        artifact_id = input.artifact_open()
        if orch.store.has(artifact_id):
            await set_active_artifact(orch, active_artifact_id, artifact_id)
            await orch.show_version(artifact_id)

    @reactive.effect
    @reactive.event(input.artifact_revise_text)
    async def on_revise():
        try:
            await orch.revise(active_artifact_id.get(), input.artifact_revise_text())
        except Exception as e:
            raise NotifyException(str(e)) from e
        await save_artifact_revision(shinychat_chat)

    @reactive.effect
    @reactive.event(input.artifact_version_prev)
    async def on_version_prev():
        await step_artifact_version(
            orch,
            active_artifact_id.get(),
            -1,
            shinychat_chat,
        )

    @reactive.effect
    @reactive.event(input.artifact_version_next)
    async def on_version_next():
        await step_artifact_version(
            orch,
            active_artifact_id.get(),
            1,
            shinychat_chat,
        )

    @render.download(filename="artifact.zip")
    async def artifact_download():
        data = await orch.build_download(active_artifact_id.get())
        if data is not None:
            yield data

    @shinychat_chat.history.on_save
    def on_artifact_history_save(values: dict[str, Any]) -> None:
        snapshot = build_artifact_snapshot(orch)
        if snapshot:
            values[ARTIFACTS_BOOKMARK_KEY] = snapshot

    @shinychat_chat.history.on_restore
    def on_artifact_history_restore(values: dict[str, Any]) -> None:
        panel_close = apply_artifact_snapshot(
            orch,
            values.get(ARTIFACTS_BOOKMARK_KEY),
            active_artifact_id,
        )
        if panel_close is None:
            return
        task = asyncio.create_task(panel_close)
        restore_tasks.add(task)
        task.add_done_callback(
            lambda completed: finish_artifact_restore_task(
                completed,
                restore_tasks,
            )
        )

    return lambda: open_artifact_creator(orch, recommend_task)
