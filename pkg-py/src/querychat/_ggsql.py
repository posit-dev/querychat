"""Helpers for ggsql integration."""

from __future__ import annotations

import re


def extract_title(viz_spec: str) -> str | None:
    """
    Extract the title from a VISUALISE spec's LABEL clause.

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


def vegalite_to_html(vegalite_spec: dict) -> str:
    """
    Convert a Vega-Lite specification to standalone HTML.

    This renders the spec directly using vega-embed.

    Parameters
    ----------
    vegalite_spec
        A Vega-Lite specification as a dictionary.

    Returns
    -------
    str
        A complete HTML document that renders the chart.

    """
    import json

    spec_json = json.dumps(vegalite_spec)

    # ggsql produces v6 specs
    vl_version = "6"

    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <script src="https://cdn.jsdelivr.net/npm/vega@5"></script>
  <script src="https://cdn.jsdelivr.net/npm/vega-lite@{vl_version}"></script>
  <script src="https://cdn.jsdelivr.net/npm/vega-embed@6"></script>
  <style>
    body {{ margin: 0; padding: 8px; }}
    #vis {{ width: 100%; }}
  </style>
</head>
<body>
  <div id="vis"></div>
  <script>
    vegaEmbed('#vis', {spec_json}, {{actions: false}})
      .catch(console.error);
  </script>
</body>
</html>"""
