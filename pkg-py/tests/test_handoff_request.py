import asyncio
from unittest.mock import AsyncMock, MagicMock, call

import pytest
import querychat._handoff_server as handoff_server
from querychat._handoff_types import resolve_handoff_type
from querychat._handoff_view import HandoffView


def test_handoff_snapshot_round_trip():
    active_handoff_id = MagicMock()
    orch = MagicMock()
    orch.store.bookmark_values.return_value = [{"handoff_id": "a"}]
    orch.view.set_panel_open = AsyncMock()

    values = handoff_server.build_handoff_snapshot(orch)
    panel_close = handoff_server.apply_handoff_snapshot(
        orch,
        values,
        active_handoff_id,
    )
    assert panel_close is not None
    asyncio.run(panel_close)

    assert values == [{"handoff_id": "a"}]
    orch.restore_snapshot.assert_called_once_with(values)


def test_apply_missing_handoff_snapshot_clears_store():
    active_handoff_id = MagicMock()
    orch = MagicMock()
    orch.view.set_panel_open = AsyncMock()

    panel_close = handoff_server.apply_handoff_snapshot(
        orch,
        None,
        active_handoff_id,
    )
    assert panel_close is not None
    asyncio.run(panel_close)

    orch.restore_snapshot.assert_called_once_with([])


def test_apply_handoff_snapshot_ignores_other_values():
    active_handoff_id = MagicMock()
    orch = MagicMock()

    panel_close = handoff_server.apply_handoff_snapshot(
        orch,
        {"handoff_id": "a"},
        active_handoff_id,
    )

    assert panel_close is None
    orch.restore_snapshot.assert_not_called()


def test_apply_handoff_snapshot_closes_open_panel():
    active_handoff_id = MagicMock()
    orch = MagicMock()
    orch.view.set_panel_open = AsyncMock()
    values = [{"handoff_id": "restored-handoff"}]

    asyncio.run(
        handoff_server.set_active_handoff(
            orch,
            active_handoff_id,
            "previous-handoff",
        )
    )
    panel_close = handoff_server.apply_handoff_snapshot(
        orch,
        values,
        active_handoff_id,
    )
    assert panel_close is not None
    asyncio.run(panel_close)

    orch.restore_snapshot.assert_called_once_with(values)
    assert active_handoff_id.set.call_args_list == [
        call("previous-handoff"),
        call(None),
    ]
    assert orch.view.set_panel_open.await_args_list == [
        call(is_open=True),
        call(is_open=False),
    ]


def test_completed_panel_close_task_is_removed():
    async def run_test():
        task = asyncio.create_task(asyncio.sleep(0))
        restore_tasks = {task}
        await task

        handoff_server.finish_handoff_restore_task(task, restore_tasks)

        assert not restore_tasks

    asyncio.run(run_test())


def test_failed_panel_close_task_notifies_and_is_removed(monkeypatch):
    async def run_test():
        async def fail_close():
            raise RuntimeError("panel close failed")

        notifications = MagicMock()
        monkeypatch.setattr(
            handoff_server.ui,
            "notification_show",
            notifications,
        )
        task = asyncio.create_task(fail_close())
        restore_tasks = {task}
        with pytest.raises(RuntimeError, match="panel close failed"):
            await task

        handoff_server.finish_handoff_restore_task(task, restore_tasks)

        notifications.assert_called_once()
        assert "panel close failed" in notifications.call_args.args[0]
        assert not restore_tasks

    asyncio.run(run_test())


def test_open_handoff_creator_replaces_pending_recommendation():
    items = [MagicMock()]
    orch = MagicMock()
    orch.open_modal.return_value = items
    recommend_task = MagicMock()

    handoff_server.open_handoff_creator(orch, recommend_task)

    recommend_task.cancel.assert_called_once()
    recommend_task.invoke.assert_called_once_with(items)


def test_open_handoff_creator_skips_recommendation_for_empty_gallery():
    orch = MagicMock()
    orch.open_modal.return_value = []
    recommend_task = MagicMock()

    handoff_server.open_handoff_creator(orch, recommend_task)

    recommend_task.cancel.assert_called_once()
    recommend_task.invoke.assert_not_called()


def test_set_active_handoff_opens_panel():
    active_handoff_id = MagicMock()
    orch = MagicMock()
    orch.view.set_panel_open = AsyncMock()

    asyncio.run(
        handoff_server.set_active_handoff(
            orch,
            active_handoff_id,
            "handoff-id",
        )
    )

    active_handoff_id.set.assert_called_once_with("handoff-id")
    orch.view.set_panel_open.assert_awaited_once_with(is_open=True)


def test_set_active_handoff_closes_panel():
    active_handoff_id = MagicMock()
    orch = MagicMock()
    orch.view.set_panel_open = AsyncMock()

    asyncio.run(handoff_server.set_active_handoff(orch, active_handoff_id, None))

    active_handoff_id.set.assert_called_once_with(None)
    orch.view.set_panel_open.assert_awaited_once_with(is_open=False)


def test_handoff_revision_uses_public_history_save():
    chat = MagicMock()
    chat.history.save = AsyncMock(return_value=True)

    asyncio.run(handoff_server.save_handoff_revision(chat))

    chat.history.save.assert_awaited_once_with()


def test_handoff_revision_propagates_history_save_error():
    chat = MagicMock()
    chat.history.save = AsyncMock(side_effect=OSError("disk full"))

    with pytest.raises(OSError, match="disk full"):
        asyncio.run(handoff_server.save_handoff_revision(chat))


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
    view = HandoffView(view_session, chat_ui)
    orch = MagicMock()

    async def generate(request, directions, handoff_id):
        await view.append_pill(
            handoff_id,
            resolve_handoff_type("quarto-dashboard", "python"),
            "A dashboard",
        )
        events.append("pill")

    async def save_revision(chat):
        saved_messages.extend(chat_ui.messages)
        events.append("history")

    orch.generate = generate
    monkeypatch.setattr(
        handoff_server,
        "save_handoff_revision",
        save_revision,
    )

    asyncio.run(
        handoff_server.generate_and_save_handoff(
            orch,
            MagicMock(),
            "Use a line chart",
            "handoff-id",
            shinychat_chat=MagicMock(),
        )
    )

    assert events == ["pill", "history"]
    assert len(saved_messages) == 1
    assert "handoff-id" in str(saved_messages[0])
