import nbformat
from nbformat.reader import NotJSONError

from ._artifact_types import LANGUAGES, ArtifactType


class ArtifactValidationError(ValueError):
    """Generated artifact source violates its target contract."""


def validate_artifact_source(
    source: str,
    artifact_type: ArtifactType,
) -> None:
    if not source.strip():
        raise ArtifactValidationError("Generated artifact source is empty.")
    if artifact_type.structure == "text":
        return
    validate_notebook_source(source, artifact_type)


def validate_notebook_source(
    source: str,
    artifact_type: ArtifactType,
) -> None:
    try:
        notebook = nbformat.reads(source, as_version=4)
        nbformat.validate(notebook)
    except (NotJSONError, nbformat.ValidationError) as exc:
        raise ArtifactValidationError(
            "Generated source is not valid notebook JSON."
        ) from exc

    kernelspec = notebook.metadata.get("kernelspec")
    actual = kernelspec.get("language") if kernelspec is not None else None
    expected = artifact_type.language
    if expected is None:
        raise ArtifactValidationError(
            "Notebook validation requires a resolved R or Python language."
        )
    label = LANGUAGES[expected]
    if not isinstance(actual, str):
        raise ArtifactValidationError(
            f"Generated notebook must declare a {label} kernelspec."
        )
    if actual.casefold() != expected.casefold():
        raise ArtifactValidationError(
            f"Generated notebook must declare a {label} kernelspec, not {actual}."
        )
