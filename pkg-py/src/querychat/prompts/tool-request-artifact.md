Open the artifact creator so the user can turn this session's work into a standalone, reusable artifact (e.g. a Quarto document, Jupyter or marimo notebook, or Shiny app).

Call this tool when the user clearly wants to package, export, save, or share the queries and visualizations from this session as a standalone deliverable. Typical cues: "make me a report of this", "turn this into a notebook", "export this as a Quarto document", "I want to share this dashboard", "save this analysis so I can run it later".

Do NOT call this tool for ordinary data questions, filtering requests, or one-off charts within the chat. Only call it when the intent is to produce a standalone artifact.

This tool does not choose a format or generate anything itself. It opens a modal where the user selects which results to include and the output format, then generates the artifact themselves.

After calling this tool, respond with a single very brief sentence confirming the tool's result (for example: "Sure — opening the artifact creator now."). Do not describe the modal's contents or pre-empt the user's choices.

Returns
-------
:
    Confirmation that the artifact creator will open.
