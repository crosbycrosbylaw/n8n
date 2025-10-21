import sys
from dataclasses import InitVar, dataclass, field
from typing import Self

from rampy import console, js

from .output import output


@dataclass(match_args=False)
class Runner[T: js.serializable[...]]:
    """A template class for creating python script utilities for use in n8n workflows. Standardizes input and serializes outputs."""

    input: list[str] = field(default_factory=lambda: sys.argv[1:])

    json: js.object[T] = field(init=False, default_factory=js.object[T])
    logs: list[str] = field(init=False, default_factory=list[str])
    warnings: list[str] = field(init=False, default_factory=list[str])

    testing: InitVar[bool] = False

    def submit(self) -> None:
        """Prints serialized output in a standardized format for ease of ingestion within the n8n instance."""
        return output(self.json, logs=self.logs, warnings=self.warnings)

    @console.catch
    def __post_init__(self, testing: bool) -> None:
        if not testing:
            self.setup().run().submit()
        self.test = testing

    def setup(self) -> Self:
        """Implement this method if the class requires any internal setup before invoking the primary logic."""

        return self

    def run(self) -> Self:
        """This method will be invoked after setup, but before output."""

        return self
