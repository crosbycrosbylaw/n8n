from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable
    from string.templatelib import Interpolation, Template
    from typing import Any


class ValidationError(ValueError):
    """Exception raised when template value validation fails."""

    def __init__(self, *, intr: Interpolation) -> None:
        """Initialize a ValidationError with an invalid interpolation.

        Args:
            intr: The Interpolation object that failed validation.

        """
        super().__init__(f'"{intr.expression}" has an invalid assignment of {intr.value!r}')


def validate_string(template: Template, schema: dict[str, Callable[[Any], bool]]) -> None:
    """Validate template values against a schema.

    Args:
        template: The template object containing interpolations and values to validate.
        schema: A dictionary mapping expression keys to validation callables.

    Raises:
        ValidationError: If any template value fails its corresponding schema validation.

    """
    for key, value in zip(template.interpolations, template.values, strict=True):
        if not schema[key.expression](value):
            raise ValidationError(intr=key)
