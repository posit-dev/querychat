"""
Canonical names of the tools the LLM can call.

These are the single source of truth for the names tools register under
(`tools.py`, `_viz_tools.py`) and the names consumers match against when reading
recorded chat turns (`_artifact_gallery.py`). Keeping them here makes that
cross-module contract explicit: a rename is one edit, and `goToReferences` on a
constant shows every site that depends on it.
"""

from __future__ import annotations

TOOL_QUERY = "querychat_query"
TOOL_VISUALIZE = "querychat_visualize"
TOOL_UPDATE_DASHBOARD = "querychat_update_dashboard"
TOOL_RESET_DASHBOARD = "querychat_reset_dashboard"
TOOL_REQUEST_ARTIFACT = "querychat_request_artifact"
