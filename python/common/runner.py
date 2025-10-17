import sys
from dataclasses import dataclass, field

from rampy import console
from rampy.json import JSON

from .output import output


@dataclass()
class Runner:
    """A template class for creating python script utilities for use in n8n workflows. Standardizes input and serializes outputs."""

    input: list[str] = field(default_factory=list[str])

    json: JSON = field(init=False, default_factory=JSON)
    logs: list[str] = field(init=False, default_factory=list)
    warnings: list[str] = field(init=False, default_factory=list)

    def __call__(self) -> None:
        """Prints serialized output in a standardized format for ease of ingestion within the n8n instance."""
        return output(self.json, logs=self.logs, warnings=self.warnings)

    @console.catch
    def __post_init__(self) -> None:
        self.input = self.input or sys.argv
        self.setup()
        self.run()
        return self()

    def setup(self) -> None:
        """Implement this method if the class requires any internal setup before invoking the primary logic."""

    def run(self) -> None:
        """This method will be invoked after setup, but before output."""
