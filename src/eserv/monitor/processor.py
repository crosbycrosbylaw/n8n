from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from rampy import create_field_factory

from setup_console import console

from .flags import status_flag_factory

if TYPE_CHECKING:
    from eserv.core import Pipeline
    from eserv.types import BatchResult, EmailState, GraphClient, ProcessedResult, StatusFlag


@dataclass
class EmailProcessor:
    """Orchestrates email monitoring and processing."""

    pipeline: Pipeline
    client: GraphClient = field(init=False)
    state: EmailState = field(init=False)

    def __post_init__(self) -> None:
        """Initialize state from pipeline after dataclass initialization."""
        from .client import GraphClient

        self.client = GraphClient(
            self.pipeline.config.credentials['microsoft-outlook'],
            self.pipeline.config.monitoring,
        )
        self.state = self.pipeline.state

    def process_batch(self, num_days: int) -> BatchResult:
        """Process all unprocessed emails from monitoring folder."""
        from eserv.types import BatchResult

        batch = self.client.fetch_unprocessed_emails(num_days, self.state.processed)
        results: list[ProcessedResult] = []

        for record in batch:
            result = self.pipeline.execute(record)
            results.append(result)

            # Apply flag (auto-retry on transient failure)
            try:
                flag = self._result_to_flag(result)
                self.client.apply_flag(record.uid, flag)
            except Exception:
                console.exception('Batch processing')

            self.state.record(result)

        return BatchResult(results=results)

    @staticmethod
    def _result_to_flag(result: ProcessedResult) -> StatusFlag:
        """Convert result to MAPI flag."""
        if not result.error:
            return status_flag_factory(success=True)

        return status_flag_factory(result.error)


processor_factory = create_field_factory(EmailProcessor)
