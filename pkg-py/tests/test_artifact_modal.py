import re

from querychat._artifact_modal import build_language_selector, build_type_selector


def ns(x: str) -> str:
    return f"ns-{x}"


class TestLanguageSelector:
    def test_renders_no_preference_and_both_languages(self):
        html = str(build_language_selector())
        assert 'data-language=""' in html
        assert 'data-language="r"' in html
        assert 'data-language="python"' in html
        assert "No preference" in html

    def test_no_hidden_input(self):
        html = str(build_language_selector())
        assert "artifact_language_selected" not in html

    def test_no_preference_pill_is_active(self):
        html = str(build_language_selector())
        # Exactly one pill is active, and it is the No preference one.
        assert html.count("querychat-artifact-language-pill active") == 1
        active_idx = html.index("querychat-artifact-language-pill active")
        assert active_idx < html.index('data-language="r"')


class TestTypeSelectorLanguages:
    def test_marimo_pill_is_python_only(self):
        html = str(build_type_selector())
        assert re.search(
            r'data-artifact-type="marimo-notebook"[^>]*data-languages="python"',
            html,
        )

    def test_multilingual_pill_supports_both(self):
        html = str(build_type_selector())
        assert 'data-languages="python,r"' in html
