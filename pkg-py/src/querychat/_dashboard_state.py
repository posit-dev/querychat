"""
State models for the dashboard drawer.

`DashboardSpec` is the single source of truth for the drawer: rendering,
bookmarking, LLM context, and (later) artifact export all consume it. Cards
are declarative only — see the design doc. `DashboardHistory` (Task 2) gives
undo/redo over spec snapshots.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

CardType = Literal["chart", "table", "value_box", "markdown"]

GRID_COLUMNS = 12

# Which source field each card type requires. A card carries exactly one
# meaningful source; the others stay "".
SOURCE_FIELD_BY_TYPE: dict[str, str] = {
    "chart": "ggsql",
    "table": "sql",
    "value_box": "sql",
    "markdown": "text",
}


class CardLayout(BaseModel):
    """Position of a card on the 12-column unit grid (gridstack coordinates)."""

    x: int = Field(ge=0, le=GRID_COLUMNS - 1)
    y: int = Field(ge=0)
    w: int = Field(ge=1, le=GRID_COLUMNS)
    h: int = Field(ge=1)

    @model_validator(mode="after")
    def fits_within_grid(self) -> CardLayout:
        if self.x + self.w > GRID_COLUMNS:
            raise ValueError(
                f"Card extends beyond grid: x={self.x} + w={self.w} > {GRID_COLUMNS}"
            )
        return self


class Placement(BaseModel):
    """A named layout update, as sent by the LLM arrange tool or browser drags."""

    name: str
    x: int = Field(ge=0, le=GRID_COLUMNS - 1)
    y: int = Field(ge=0)
    w: int = Field(ge=1, le=GRID_COLUMNS)
    h: int = Field(ge=1)

    @model_validator(mode="after")
    def fits_within_grid(self) -> Placement:
        if self.x + self.w > GRID_COLUMNS:
            raise ValueError(
                f"Card extends beyond grid: x={self.x} + w={self.w} > {GRID_COLUMNS}"
            )
        return self

    def layout(self) -> CardLayout:
        return CardLayout(x=self.x, y=self.y, w=self.w, h=self.h)


class CardSpec(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    name: str = Field(pattern=r"^[a-z][a-z0-9_]*$", max_length=40)
    type: CardType
    title: str = ""
    layout: CardLayout | None = None
    # Type-specific source (exactly one is required, per SOURCE_FIELD_BY_TYPE):
    ggsql: str = ""
    sql: str = ""
    text: str = ""
    # value_box options:
    format: str = ""  # Python format spec, optional leading currency symbol
    icon: str | None = None
    theme: str | None = None
    delta_sql: str | None = None
    # table options:
    page_size: int = Field(default=10, ge=1, le=100)
    # RESERVED for parameterized cards (post-MVP); always [] in Stage 1:
    controls: list[dict] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_source_for_type(self) -> CardSpec:
        field = SOURCE_FIELD_BY_TYPE[self.type]
        if not getattr(self, field):
            raise ValueError(f"A '{self.type}' card requires a non-empty '{field}'.")
        return self

    @property
    def source(self) -> str:
        return getattr(self, SOURCE_FIELD_BY_TYPE[self.type])


class DashboardSpec(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    title: str = "My dashboard"
    cards: list[CardSpec] = Field(default_factory=list)

    def get_card(self, name: str) -> CardSpec | None:
        for card in self.cards:
            if card.name == name:
                return card
        return None

    def upsert_card(self, card: CardSpec) -> None:
        for i, existing in enumerate(self.cards):
            if existing.name == card.name:
                self.cards[i] = card
                return
        self.cards.append(card)

    def remove_card(self, name: str) -> bool:
        """Hide-don't-delete: clear layout so the card returns to the palette."""
        card = self.get_card(name)
        if card is None:
            return False
        card.layout = None
        return True

    def on_canvas(self) -> list[CardSpec]:
        return [c for c in self.cards if c.layout is not None]

    def next_free_y(self) -> int:
        """First row below all placed cards (gridstack will compact upward)."""
        placed = self.on_canvas()
        if not placed:
            return 0
        return max(c.layout.y + c.layout.h for c in placed if c.layout is not None)

    def apply_placements(self, placements: list[Placement]) -> None:
        cards: list[tuple[CardSpec, Placement]] = []
        for p in placements:
            card = self.get_card(p.name)
            if card is None:
                raise KeyError(p.name)
            cards.append((card, p))
        for card, p in cards:
            card.layout = p.layout()
