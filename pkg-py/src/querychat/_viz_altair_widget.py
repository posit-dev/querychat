"""Altair chart wrapper for responsive display in Shiny."""

from __future__ import annotations

import functools
from typing import TYPE_CHECKING, Any, cast
from uuid import uuid4

from shiny.session import get_current_session

from shiny import reactive

if TYPE_CHECKING:
    import altair as alt
    import ggsql

@functools.cache
def get_compound_chart_types() -> tuple[type, ...]:
    import altair as alt

    return (
        alt.FacetChart,
        alt.ConcatChart,
        alt.HConcatChart,
        alt.VConcatChart,
    )


class AltairWidget:
    """
    An Altair chart wrapped in ``alt.JupyterChart`` for display in Shiny.

    Always produces a ``JupyterChart`` so that ``shinywidgets`` receives
    a consistent widget type and doesn't call ``chart.properties(width=...)``
    (which fails on compound specs).

    Simple charts use native ``width/height: "container"`` sizing.
    Compound charts (facet, concat) get calculated cell dimensions
    that are reactively updated when the output container resizes.
    """

    widget: alt.JupyterChart
    widget_id: str

    def __init__(self, chart: alt.TopLevelMixin) -> None:
        import altair as alt

        is_compound = isinstance(chart, get_compound_chart_types())

        # Workaround: Vega-Lite's width/height: "container" doesn't work for
        # compound specs (facet, concat, etc.), so we inject pixel dimensions
        # and reconstruct the chart. Remove this branch when ggsql handles it
        # natively: https://github.com/posit-dev/ggsql/issues/238
        if is_compound:
            chart = inject_compound_sizes(
                chart, DEFAULT_COMPOUND_WIDTH, DEFAULT_COMPOUND_HEIGHT
            )
        else:
            chart = chart.properties(width="container", height="container")

        self.widget = alt.JupyterChart(chart)
        self.widget_id = f"querychat_viz_{uuid4().hex[:8]}"

        # Reactively update compound cell sizes when the container resizes.
        # Also part of the compound sizing workaround (issue #238).
        if is_compound:
            self._setup_reactive_sizing(self.widget, self.widget_id)

    @classmethod
    def from_ggsql(cls, spec: ggsql.Spec) -> AltairWidget:
        from ggsql import VegaLiteWriter

        writer = VegaLiteWriter()
        return cls(writer.render_chart(spec))

    @staticmethod
    def _setup_reactive_sizing(widget: alt.JupyterChart, widget_id: str) -> None:
        session = get_current_session()
        if session is None:
            return

        @reactive.effect
        def _sizing_effect():
            width = session.clientdata.output_width(widget_id)
            height = session.clientdata.output_height(widget_id)
            if width is None or height is None:
                return
            chart = widget.chart
            if chart is None:
                return
            chart = cast("alt.Chart", chart)
            chart2 = inject_compound_sizes(chart, int(width), int(height))
            # Must set widget.spec (a new dict) rather than widget.chart,
            # because traitlets won't fire change events when the same
            # chart object is assigned back after in-place mutation.
            widget.spec = chart2.to_dict()

        # Clean up the effect when the session ends to avoid memory leaks
        session.on_ended(_sizing_effect.destroy)


# ---------------------------------------------------------------------------
# Compound chart sizing helpers
#
# Vega-Lite's `width/height: "container"` doesn't work for compound specs
# (facet, concat, etc.), so we manually inject cell dimensions. Ideally ggsql
# will handle this natively: https://github.com/posit-dev/ggsql/issues/238
# ---------------------------------------------------------------------------

DEFAULT_COMPOUND_WIDTH = 900
DEFAULT_COMPOUND_HEIGHT = 450

LEGEND_CHANNELS = frozenset(
    {"color", "colour", "fill", "stroke", "shape", "size", "opacity"}
)
LEGEND_WIDTH = 120  # approximate space for a right-side legend


def inject_compound_sizes(
    chart: alt.TopLevelMixin,
    container_width: int,
    container_height: int,
) -> alt.TopLevelMixin:
    """
    Set cell ``width``/``height`` on a compound spec via in-place mutation.

    The chart is mutated in-place **and** returned. Callers that need to
    trigger traitlets change detection should serialize the returned chart
    (e.g., ``chart.to_dict()``) rather than reassigning ``widget.chart``,
    because traitlets won't fire events for the same object after mutation.

    For faceted charts, divides the container width by the number of columns.
    For hconcat/concat, divides by the number of sub-specs.
    For vconcat, each sub-spec gets the full width.

    Subtracts padding estimates so the rendered cells fill the container,
    including space for legends when present.
    """
    import altair as alt

    # Approximate padding; will be replaced when ggsql handles compound sizing
    # natively (https://github.com/posit-dev/ggsql/issues/238).
    padding_x = 80  # y-axis labels + title padding
    padding_y = 120  # facet headers, x-axis labels + title, bottom padding
    if has_legend(chart.to_dict()):
        padding_x += LEGEND_WIDTH
    usable_w = max(container_width - padding_x, 100)
    usable_h = max(container_height - padding_y, 100)

    if isinstance(chart, alt.FacetChart):
        ncol = chart.columns if isinstance(chart.columns, int) else 1
        cell_w = usable_w // max(ncol, 1)
        chart.spec.width = cell_w
        chart.spec.height = usable_h
    elif isinstance(chart, alt.HConcatChart):
        cell_w = usable_w // max(len(chart.hconcat), 1)
        for sub in chart.hconcat:
            sub.width = cell_w
            sub.height = usable_h
    elif isinstance(chart, alt.ConcatChart):
        ncol = chart.columns if isinstance(chart.columns, int) else len(chart.concat)
        cell_w = usable_w // max(ncol, 1)
        for sub in chart.concat:
            sub.width = cell_w
            sub.height = usable_h
    elif isinstance(chart, alt.VConcatChart):
        cell_h = usable_h // max(len(chart.vconcat), 1)
        for sub in chart.vconcat:
            sub.width = usable_w
            sub.height = cell_h

    return chart


def has_legend(vl: dict[str, object]) -> bool:
    """Check if any encoding in the VL spec uses a legend-producing channel with a field."""
    specs: list[dict[str, Any]] = []
    if "spec" in vl:
        specs.append(vl["spec"])  # type: ignore[arg-type]
    for key in ("hconcat", "vconcat", "concat"):
        if key in vl:
            specs.extend(vl[key])  # type: ignore[arg-type]

    for spec in specs:
        for layer in spec.get("layer", [spec]):  # type: ignore[union-attr]
            enc = layer.get("encoding", {})  # type: ignore[union-attr]
            for ch in LEGEND_CHANNELS:
                if ch in enc and "field" in enc[ch]:  # type: ignore[operator]
                    return True
    return False
