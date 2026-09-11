import nbformat
from nbformat.reader import NotJSONError

from ._handoff_types import LANGUAGES, HandoffType

HANDOFF_MIN_SOURCE_LENGTH = 200
HANDOFF_PROMPT_ECHO_PREFIX_LENGTH = 80


class HandoffValidationError(ValueError):
    """Generated handoff source violates its target contract."""


def validate_handoff_source(
    source: str,
    handoff_type: HandoffType,
    system_prompt: str,
) -> None:
    if not source.strip():
        raise HandoffValidationError("Generated handoff source is empty.")
    if handoff_type.structure == "notebook-json":
        validate_notebook_source(source, handoff_type)
    else:
        validate_handoff_substance(source, system_prompt)


def validate_handoff_substance(source: str, system_prompt: str) -> None:
    if len(source) < HANDOFF_MIN_SOURCE_LENGTH:
        raise HandoffValidationError(
            "Generated handoff source is too short to be a real handoff "
            f"({len(source)} characters)."
        )
    prompt_prefix = system_prompt.strip()[:HANDOFF_PROMPT_ECHO_PREFIX_LENGTH]
    if prompt_prefix and prompt_prefix in source:
        raise HandoffValidationError(
            "Generated handoff source echoes the system prompt instead of "
            "producing real content."
        )


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
