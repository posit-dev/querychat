"""
Dash example app for querychat.

Run with: python 06-dash-app.py
Requires: pip install dash dash-bootstrap-components (or uv sync --group dash)
"""

import os
from pathlib import Path

from querychat.dash import QueryChat
from querychat.data import titanic

greeting = Path(__file__).parent / "greeting.md"

qc = QueryChat(titanic(), "titanic", greeting=greeting)
app = qc.app()

if __name__ == "__main__":
    port = int(os.environ.get("DASH_PORT", "8050"))
    debug = os.environ.get("DASH_DEBUG", "true").lower() == "true"
    app.run(debug=debug, port=port)
