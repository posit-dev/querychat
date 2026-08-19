import asyncio
import gc
from unittest.mock import AsyncMock, MagicMock, call

import querychat._artifact_server as artifact_server
from querychat._artifact_types import resolve_artifact_type
from querychat._artifact_view import ArtifactView
from querychat._shiny_module import artifact_action_for_status


def test_running_or_initial_status_waits():
    assert artifact_action_for_status("running") == "wait"
    assert artifact_action_for_status("initial") == "wait"


def test_success_opens():
    assert artifact_action_for_status("success") == "open"


def test_error_or_cancelled_drops():
    assert artifact_action_for_status("error") == "drop"
    assert artifact_action_for_status("cancelled") == "drop"


def test_artifact_snapshot_round_trip():
    active_artifact_id = MagicMock()
    orch = MagicMock()
    orch.store.bookmark_values.return_value = [{"artifact_id": "a"}]
    orch.view.set_panel_open = AsyncMock()

    values = artifact_server.build_artifact_snapshot(orch)
    panel_close = artifact_server.apply_artifact_snapshot(
        orch,
        values,
        active_artifact_id,
    )
    assert panel_close is not None
    asyncio.run(panel_close)

    assert values == [{"artifact_id": "a"}]
    orch.restore_snapshot.assert_called_once_with(values)


def test_apply_missing_artifact_snapshot_clears_store():
    active_artifact_id = MagicMock()
    orch = MagicMock()
    orch.view.set_panel_open = AsyncMock()

    panel_close = artifact_server.apply_artifact_snapshot(
        orch,
        None,
        active_artifact_id,
    )
    assert panel_close is not None
    asyncio.run(panel_close)

    orch.restore_snapshot.assert_called_once_with([])


def test_apply_artifact_snapshot_ignores_other_values():
    active_artifact_id = MagicMock()
    orch = MagicMock()

    panel_close = artifact_server.apply_artifact_snapshot(
        orch,
        {"artifact_id": "a"},
        active_artifact_id,
    )

    assert panel_close is None
    orch.restore_snapshot.assert_not_called()


def test_apply_artifact_snapshot_closes_open_panel():
    active_artifact_id = MagicMock()
    orch = MagicMock()
    orch.view.set_panel_open = AsyncMock()
    values = [{"artifact_id": "restored-artifact"}]

    asyncio.run(
        artifact_server.set_active_artifact(
            orch,
            active_artifact_id,
            "previous-artifact",
        )
    )
    panel_close = artifact_server.apply_artifact_snapshot(
        orch,
        values,
        active_artifact_id,
    )
    assert panel_close is not None
    asyncio.run(panel_close)

    orch.restore_snapshot.assert_called_once_with(values)
    assert active_artifact_id.set.call_args_list == [
        call("previous-artifact"),
        call(None),
    ]
    assert orch.view.set_panel_open.await_args_list == [
        call(is_open=True),
        call(is_open=False),
    ]


def capture_history_restore(monkeypatch, orchestrator):
    callbacks = []
    active_artifact_id = MagicMock()
    recommend_task = MagicMock()
    recommend_task.status = MagicMock()
    session = MagicMock()
    session.bookmark.on_bookmark.side_effect = lambda fn: fn
    session.bookmark.on_restore.side_effect = lambda fn: fn
    shinychat_chat = MagicMock()
    shinychat_chat.slash_command.side_effect = lambda *args, **kwargs: lambda fn: fn
    shinychat_chat.history.on_save.side_effect = lambda fn: fn

    def register_restore(fn):
        callbacks.append(fn)
        return fn

    shinychat_chat.history.on_restore.side_effect = register_restore
    monkeypatch.setattr(
        artifact_server,
        "ArtifactOrchestrator",
        MagicMock(return_value=orchestrator),
    )
    monkeypatch.setattr(
        artifact_server.reactive,
        "Value",
        MagicMock(return_value=active_artifact_id),
    )
    monkeypatch.setattr(
        artifact_server.reactive,
        "extended_task",
        lambda fn: recommend_task,
    )
    monkeypatch.setattr(artifact_server.reactive, "effect", lambda fn: fn)
    monkeypatch.setattr(
        artifact_server.reactive,
        "event",
        lambda *args, **kwargs: lambda fn: fn,
    )
    monkeypatch.setattr(
        artifact_server.render,
        "download",
        lambda *args, **kwargs: lambda fn: fn,
    )

    artifact_server.artifact_server(
        MagicMock(),
        session,
        MagicMock(),
        data_sources={},
        executor=MagicMock(),
        shinychat_chat=shinychat_chat,
        history=False,
    )
    return callbacks[0], active_artifact_id


def get_restore_tasks(callback):
    index = callback.__code__.co_freevars.index("restore_tasks")
    return callback.__closure__[index].cell_contents


def test_history_restore_applies_metadata_synchronously_and_retains_close_task(
    monkeypatch,
):
    async def run_test():
        close_started = asyncio.Event()
        release_close = asyncio.Event()

        async def close_panel(*, is_open):
            assert is_open is False
            close_started.set()
            await release_close.wait()

        orch = MagicMock()
        orch.view.set_panel_open = close_panel
        callback, active_artifact_id = capture_history_restore(monkeypatch, orch)
        restore_tasks = get_restore_tasks(callback)
        values = [{"artifact_id": "restored"}]

        callback({artifact_server.ARTIFACTS_BOOKMARK_KEY: values})

        orch.restore_snapshot.assert_called_once_with(values)
        active_artifact_id.set.assert_called_once_with(None)
        assert len(restore_tasks) == 1
        await close_started.wait()
        assert len(restore_tasks) == 1

        release_close.set()
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        assert not restore_tasks

    asyncio.run(run_test())


def test_history_restore_reports_and_consumes_panel_close_failure(monkeypatch):
    async def run_test():
        async def close_panel(*, is_open):
            raise RuntimeError("panel close failed")

        orch = MagicMock()
        orch.view.set_panel_open = close_panel
        callback, _ = capture_history_restore(monkeypatch, orch)
        notifications = MagicMock()
        monkeypatch.setattr(
            artifact_server.ui,
            "notification_show",
            notifications,
        )
        loop_errors = []
        loop = asyncio.get_running_loop()
        loop.set_exception_handler(lambda _loop, context: loop_errors.append(context))

        callback({artifact_server.ARTIFACTS_BOOKMARK_KEY: []})
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        gc.collect()

        notifications.assert_called_once()
        assert "panel close failed" in notifications.call_args.args[0]
        assert loop_errors == []

    asyncio.run(run_test())


def test_open_artifact_creator_replaces_pending_recommendation():
    items = [MagicMock()]
    orch = MagicMock()
    orch.open_modal.return_value = items
    recommend_task = MagicMock()

    artifact_server.open_artifact_creator(orch, recommend_task)

    recommend_task.cancel.assert_called_once()
    recommend_task.invoke.assert_called_once_with(items)


def test_open_artifact_creator_skips_recommendation_for_empty_gallery():
    orch = MagicMock()
    orch.open_modal.return_value = []
    recommend_task = MagicMock()

    artifact_server.open_artifact_creator(orch, recommend_task)

    recommend_task.cancel.assert_called_once()
    recommend_task.invoke.assert_not_called()


def test_set_active_artifact_opens_panel():
    active_artifact_id = MagicMock()
    orch = MagicMock()
    orch.view.set_panel_open = AsyncMock()

    asyncio.run(
        artifact_server.set_active_artifact(
            orch,
            active_artifact_id,
            "artifact-id",
        )
    )

    active_artifact_id.set.assert_called_once_with("artifact-id")
    orch.view.set_panel_open.assert_awaited_once_with(is_open=True)


def test_set_active_artifact_closes_panel():
    active_artifact_id = MagicMock()
    orch = MagicMock()
    orch.view.set_panel_open = AsyncMock()

    asyncio.run(artifact_server.set_active_artifact(orch, active_artifact_id, None))

    active_artifact_id.set.assert_called_once_with(None)
    orch.view.set_panel_open.assert_awaited_once_with(is_open=False)


def test_revision_save_uses_history_controller():
    controller = MagicMock()
    controller.save_current = AsyncMock()
    chat = MagicMock()
    chat.history._controller = controller
    session = MagicMock()
    session.bookmark = AsyncMock()

    asyncio.run(
        artifact_server.save_artifact_revision(
            chat,
            session,
            bookmark_mode=False,
        )
    )

    controller.save_current.assert_awaited_once()
    session.bookmark.assert_not_awaited()


def test_bookmark_revision_uses_history_hook_after_saving():
    record = object()
    events: list[str] = []

    async def save_current() -> None:
        events.append("save")

    async def on_response_saved(saved_record: object) -> None:
        assert saved_record is record
        events.append("bookmark")

    controller = MagicMock()
    controller.record = record
    controller.save_current = save_current
    controller.on_response_saved = on_response_saved
    chat = MagicMock()
    chat.history._controller = controller
    session = MagicMock()
    session.bookmark = AsyncMock()

    asyncio.run(
        artifact_server.save_artifact_revision(
            chat,
            session,
            bookmark_mode=True,
        )
    )

    assert events == ["save", "bookmark"]
    session.bookmark.assert_not_awaited()


def test_revision_save_bookmarks_without_history_controller():
    chat = MagicMock()
    chat.history._controller = None
    session = MagicMock()
    session.bookmark = AsyncMock()

    asyncio.run(
        artifact_server.save_artifact_revision(
            chat,
            session,
            bookmark_mode=True,
        )
    )

    session.bookmark.assert_awaited_once()


def test_bookmark_revision_falls_back_without_active_record():
    controller = MagicMock()
    controller.record = None
    controller.save_current = AsyncMock()
    controller.on_response_saved = AsyncMock()
    chat = MagicMock()
    chat.history._controller = controller
    session = MagicMock()
    session.bookmark = AsyncMock()

    asyncio.run(
        artifact_server.save_artifact_revision(
            chat,
            session,
            bookmark_mode=True,
        )
    )

    controller.save_current.assert_awaited_once()
    controller.on_response_saved.assert_not_awaited()
    session.bookmark.assert_awaited_once()


def test_bookmark_revision_falls_back_without_history_hook():
    controller = MagicMock()
    controller.record = object()
    controller.save_current = AsyncMock()
    controller.on_response_saved = None
    chat = MagicMock()
    chat.history._controller = controller
    session = MagicMock()
    session.bookmark = AsyncMock()

    asyncio.run(
        artifact_server.save_artifact_revision(
            chat,
            session,
            bookmark_mode=True,
        )
    )

    controller.save_current.assert_awaited_once()
    session.bookmark.assert_awaited_once()


def test_generated_pill_is_committed_before_history_save(monkeypatch):
    events: list[str] = []
    saved_messages: list[object] = []

    class TranscriptChatUI:
        def __init__(self):
            self.messages: list[object] = []

        async def append_message(self, message):
            self.messages.append(message)

    chat_ui = TranscriptChatUI()
    view_session = MagicMock()
    view_session.ns.side_effect = lambda value: f"ns-{value}"
    view = ArtifactView(view_session, chat_ui)
    orch = MagicMock()

    async def generate(request, directions, artifact_id):
        await view.append_pill(
            artifact_id,
            resolve_artifact_type("quarto-dashboard", "python"),
            "A dashboard",
        )
        events.append("pill")

    async def save_revision(chat, session, *, bookmark_mode):
        saved_messages.extend(chat_ui.messages)
        events.append("history")

    orch.generate = generate
    monkeypatch.setattr(
        artifact_server,
        "save_artifact_revision",
        save_revision,
    )

    asyncio.run(
        artifact_server.generate_and_save_artifact(
            orch,
            MagicMock(),
            "Use a line chart",
            "artifact-id",
            shinychat_chat=MagicMock(),
            session=MagicMock(),
            bookmark_mode=True,
        )
    )

    assert events == ["pill", "history"]
    assert len(saved_messages) == 1
    assert "artifact-id" in str(saved_messages[0])
