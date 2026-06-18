"""
chatlas transport for the artifact feature.

`ArtifactChat` wraps the live chat client and owns every chatlas interaction:
forking an isolated conversation, running one-shot structured calls, and
streaming a structured `ArtifactResult` into a display sink. It is
domain-agnostic — it builds no artifact prompts; callers pass prompts and data
models in. It holds no reactive state.
"""

from __future__ import annotations

import copy
from typing import TYPE_CHECKING, TypeVar

from pydantic import BaseModel
from pydantic_core import from_json

from ._artifact_prompt import ArtifactResult

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Sequence

    import chatlas

    from ._artifact_view import ArtifactView

M = TypeVar("M", bound=BaseModel)


class ArtifactChat:
    def __init__(self, chat: chatlas.Chat) -> None:
        self._chat = chat

    def history_turns(self) -> list[chatlas.Turn]:
        return self._chat.get_turns()

    async def ask(
        self, prompt: str, model: type[M], *, turns: Sequence[chatlas.Turn] = ()
    ) -> M:
        forked = self._fork(turns=list(turns))
        return await forked.chat_structured_async(prompt, data_model=model)

    async def stream(
        self,
        prompt: str,
        *,
        turns: list[chatlas.Turn],
        system_prompt: str | None,
        sink: ArtifactView,
    ) -> tuple[ArtifactResult, list[chatlas.Turn]]:
        """Fork a chat, stream a structured artifact into the sink, return it."""
        forked = self._fork(turns=turns, system_prompt=system_prompt)
        tokens = await forked.stream_async(
            prompt, data_model=ArtifactResult, echo="none"
        )
        result = await self._drive(tokens, sink)
        return result, forked.get_turns()

    def _fork(
        self, *, turns: list[chatlas.Turn], system_prompt: str | None = None
    ) -> chatlas.Chat:
        """
        Deep-copy the live chat into an isolated conversation.

        Forking keeps generation/recommendation exchanges out of the user's main
        chat history.
        """
        forked = copy.deepcopy(self._chat)
        forked.set_turns(turns)
        if system_prompt is not None:
            forked.system_prompt = system_prompt
        return forked

    async def _drive(
        self, tokens: AsyncIterator[str], sink: ArtifactView
    ) -> ArtifactResult:
        # Spinner on before the first chunk, off in the finally so it clears even
        # if the stream or final validation fails.
        await sink.set_streaming(active=True)
        try:
            buf = ""
            last = ""
            async for chunk in tokens:
                buf += chunk
                try:
                    raw = from_json(buf, allow_partial="trailing-strings")
                except ValueError:
                    # buf hasn't reached the opening '{' yet (e.g. leading
                    # whitespace); from_json rejects it even with allow_partial.
                    continue
                value = raw.get("source", "") if isinstance(raw, dict) else ""
                source = value if isinstance(value, str) else ""
                if source != last:
                    last = source
                    await sink.update_source(source)
            result = ArtifactResult.model_validate_json(buf)
            await sink.update_source(result.source)
            return result
        finally:
            await sink.set_streaming(active=False)
