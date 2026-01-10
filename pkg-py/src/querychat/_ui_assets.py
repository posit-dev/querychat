"""Shared UI assets (CSS/JS) for web framework integrations."""

from importlib.resources import files

_assets = files("querychat.assets")


def _read_asset(folder: str, name: str) -> str:
    return _assets.joinpath(folder).joinpath(name).read_text()


# Common CSS for clickable suggestion spans in chat messages
SUGGESTION_CSS = _read_asset("shared", "suggestion.css")

# Framework-specific CSS
DASH_CSS = _read_asset("dash", "dash.css")
GRADIO_CSS = _read_asset("gradio", "gradio.css")

# Framework-specific JS for handling suggestion clicks
DASH_SUGGESTION_JS = _read_asset("dash", "dash_suggestion.js")
GRADIO_SUGGESTION_JS = _read_asset("gradio", "gradio_suggestion.js")
STREAMLIT_SUGGESTION_JS = _read_asset("streamlit", "streamlit_suggestion.js")
