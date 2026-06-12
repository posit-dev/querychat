"""
First-open dashboard generation.

Forks the live chat (deep copy, keeping the conversation turns so the LLM
knows what the user cares about) and runs one structured call. Exchanges
never appear in the visible transcript — same isolation pattern as
ArtifactChat (_artifact_chat.py).
"""

from __future__ import annotations

import copy
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from ._dashboard_cards import validate_card
from ._dashboard_state import CardLayout, CardSpec, DashboardSpec
from ._utils import read_prompt_template

if TYPE_CHECKING:
    import chatlas

    from ._dashboard_palette import PaletteItem
    from ._datasource import DataSource


class AutogenResult(BaseModel):
    title: str = "My dashboard"
    cards: list[CardSpec] = Field(default_factory=list)


def format_session_results(items: list[PaletteItem]) -> str:
    if not items:
        return "(none yet — generate an overview from the schema)"
    lines = [
        f"- [{item.kind}] {item.title}:\n```\n{item.source}\n```"
        for item in items
    ]
    return "\n".join(lines)


async def generate_first_pass(
    chat: chatlas.Chat,
    data_source: DataSource,
    palette: list[PaletteItem],
) -> DashboardSpec:
    prompt = read_prompt_template(
        "dashboard-autogen.md",
        db_type=data_source.get_db_type(),
        session_results=format_session_results(palette),
    )
    # deepcopy keeps the conversation turns AND the registered tools. Providers
    # generally honor the data_model schema over tool calls, but that's not
    # guaranteed — same trade-off as ArtifactChat's fork, accepted project-wide.
    forked = copy.deepcopy(chat)
    result: AutogenResult = await forked.chat_structured_async(
        prompt, data_model=AutogenResult
    )
    return apply_autogen_result(data_source, result)


def apply_autogen_result(
    data_source: DataSource, result: AutogenResult
) -> DashboardSpec:
    """Validate every generated card; drop failures rather than failing the gen."""
    spec = DashboardSpec(title=result.title)
    for card in result.cards:
        try:
            validate_card(data_source, card)
        except Exception:  # noqa: S112 — drop invalid cards silently; errors are expected LLM output
            continue
        if card.layout is None:
            card.layout = CardLayout(x=0, y=spec.next_free_y(), w=12, h=3)
        spec.upsert_card(card)
    return spec
