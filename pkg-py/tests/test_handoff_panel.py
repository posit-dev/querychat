from querychat._handoff_panel import handoff_panel_ui, render_pill_html
from querychat._handoff_types import HandoffType, resolve_handoff_type


class TestRenderPillHtml:
    def test_labels_as_handoff_with_format_subtitle(self):
        html = render_pill_html(
            "abc123",
            resolve_handoff_type("quarto-dashboard", "python"),
            "ns-handoff_open",
        )
        assert "Handoff" in html
        # the format label is the subtitle, not the headline
        assert "Quarto" in html
        assert 'data-handoff-id="abc123"' in html
        assert 'data-input-id="ns-handoff_open"' in html

    def test_has_open_affordance(self):
        html = render_pill_html(
            "x",
            resolve_handoff_type("quarto-dashboard", "python"),
            "ns-handoff_open",
        )
        assert "querychat-handoff-pill-open" in html

    def test_escapes_freeform_label(self):
        art = HandoffType(
            id="other",
            label="<b>R</b> & Co",
            language="r",
            file_extension=".R",
            editor_language="r",
        )
        html = render_pill_html("x", art, "ns-handoff_open")
        assert "<b>R</b>" not in html
        assert "&lt;b&gt;R&lt;/b&gt; &amp; Co" in html


class TestHandoffPanelUi:
    def test_has_namespaced_root(self):
        markup = str(handoff_panel_ui())
        assert 'id="handoff_root"' in markup
        assert 'class="querychat-handoff-root"' in markup

    def test_uses_html_dependency_for_assets(self):
        dependencies = handoff_panel_ui().render()["dependencies"]
        handoff_dependencies = [
            dependency
            for dependency in dependencies
            if dependency.name == "querychat-handoff"
        ]
        assert len(handoff_dependencies) == 1
        dependency = handoff_dependencies[0]
        assert dependency.script == [{"src": "js/handoff.js"}]
        assert [item["href"] for item in dependency.stylesheet] == ["css/handoff.css"]

    def test_has_handoff_controls(self):
        markup = str(handoff_panel_ui())
        assert "handoff_download" in markup
        assert "handoff_close" in markup
        assert "querychat-handoff-revise-toggle" in markup
        assert "querychat-handoff-panel-header" in markup
