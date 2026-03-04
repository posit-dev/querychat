"""
Helpers for ggsql integration.

These are workarounds for functionality not yet exposed by the ggsql package.
When ggsql adds native title/metadata extraction, these should be replaced.
"""

from __future__ import annotations

import re


def extract_title(viz_spec: str) -> str | None:
    """
    Extract the title from a VISUALISE spec's LABEL clause.

    .. note::
        This is a workaround. Ideally ggsql would expose title extraction
        from its ``Validated`` or ``Spec`` objects. This regex will break if
        ggsql's LABEL syntax changes (e.g., escaped quotes, multi-line values).
        TODO: File ggsql issue for native title extraction API.

    Parameters
    ----------
    viz_spec
        The VISUALISE portion of a ggsql query.

    Returns
    -------
    str | None
        The title if found, otherwise None.

    """
    # Match LABEL title => 'value' or LABEL title => "value"
    pattern = r"LABEL\s+title\s*=>\s*['\"]([^'\"]+)['\"]"
    match = re.search(pattern, viz_spec, re.IGNORECASE)
    if match:
        return match.group(1)
    return None
