import nbformat
from nbformat.reader import NotJSONError

from ._handoff_types import LANGUAGES, HandoffType


class HandoffValidationError(ValueError):
    """Generated handoff source violates its target contract."""


def validate_handoff_source(
    source: str,
    handoff_type: HandoffType,
) -> None:
    if not source.strip():
        raise HandoffValidationError("Generated handoff source is empty.")
    if handoff_type.structure == "text":
        return
    validate_notebook_source(source, handoff_type)


def validate_notebook_source(
    source: str,
    handoff_type: HandoffType,
) -> None:
    try:
        notebook = nbformat.reads(source, as_version=4)
        nbformat.validate(notebook)
    except (NotJSONError, nbformat.ValidationError) as exc:
        raise HandoffValidationError(
            "Generated source is not valid notebook JSON."
        ) from exc

    kernelspec = notebook.metadata.get("kernelspec")
    actual = kernelspec.get("language") if kernelspec is not None else None
    expected = handoff_type.language
    if expected is None:
        raise HandoffValidationError(
            "Notebook validation requires a resolved R or Python language."
        )
    label = LANGUAGES[expected]
    if not isinstance(actual, str):
        raise HandoffValidationError(
            f"Generated notebook must declare a {label} kernelspec."
        )
    if actual.casefold() != expected.casefold():
        raise HandoffValidationError(
            f"Generated notebook must declare a {label} kernelspec, not {actual}."
        )
