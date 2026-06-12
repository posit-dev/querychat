from querychat._artifact_panel import artifact_panel_ui, render_pill_html
from querychat._artifact_types import ARTIFACT_TYPES, ArtifactType


class TestRenderPillHtml:
    def test_labels_as_artifact_with_format_subtitle(self):
        html = render_pill_html(
            "abc123", ARTIFACT_TYPES["quarto-dashboard"], "ns-artifact_open"
        )
        assert "Artifact" in html
        # the format label is the subtitle, not the headline
        assert "Quarto" in html
        assert 'data-artifact-id="abc123"' in html
        assert 'data-input-id="ns-artifact_open"' in html

    def test_has_open_affordance(self):
        html = render_pill_html(
            "x", ARTIFACT_TYPES["quarto-dashboard"], "ns-artifact_open"
        )
        assert "querychat-artifact-pill-open" in html

    def test_escapes_freeform_label(self):
        art = ArtifactType(
            id="other",
            label="<b>R</b> & Co",
            file_extension=".R",
            description="",
            editor_language="r",
        )
        html = render_pill_html("x", art, "ns-artifact_open")
        assert "<b>R</b>" not in html
        assert "&lt;b&gt;R&lt;/b&gt; &amp; Co" in html


class TestArtifactPanelUi:
    def test_has_version_controls(self):
        markup = str(artifact_panel_ui())
        assert "artifact_version_prev" in markup
        assert "artifact_version_next" in markup
        assert "querychat-artifact-version-label" in markup

    def test_has_download_and_close(self):
        markup = str(artifact_panel_ui())
        assert "artifact_download" in markup
        assert "artifact_close" in markup

    def test_revise_toggle_present(self):
        markup = str(artifact_panel_ui())
        assert "querychat-artifact-revise-toggle" in markup

    def test_refine_removed(self):
        markup = str(artifact_panel_ui())
        assert "artifact_refine" not in markup
        assert "querychat-artifact-findings" not in markup

    def test_single_row_header_no_toolbar(self):
        markup = str(artifact_panel_ui())
        assert "querychat-artifact-toolbar" not in markup
        assert "querychat-artifact-panel-header" in markup
