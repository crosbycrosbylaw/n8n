from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from rampy import console

from .flags import status_flag

if TYPE_CHECKING:
    from eserv.core import Pipeline
    from eserv.util import EmailState

    from .client import GraphClient
    from .flags import StatusFlag
    from .types import BatchResult, ProcessedResult


@dataclass
class EmailProcessor:
    """Orchestrates email monitoring and processing."""

    pipeline: Pipeline
    client: GraphClient = field(init=False)
    state: EmailState = field(init=False)

    def __post_init__(self) -> None:
        """Initialize state from pipeline after dataclass initialization."""
        from .client import GraphClient  # noqa: PLC0415

        self.client = GraphClient(
            self.pipeline.config.credentials['microsoftOutlookOAuth2Api'],
            self.pipeline.config.monitoring,
        )
        self.state = self.pipeline.state

    def process_batch(self, num_days: int) -> BatchResult:
        """Process all unprocessed emails from monitoring folder."""
        from .types import BatchResult  # noqa: PLC0415

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
                console.bind().exception()

            self.state.record(result)

        return BatchResult(
            total=len(batch),
            succeeded=sum(1 for r in results if r.status == 'success'),
            failed=sum(1 for r in results if r.status == 'error'),
            results=results,
        )

    @staticmethod
    def _result_to_flag(result: ProcessedResult) -> StatusFlag:
        """Convert result to MAPI flag."""
        if not result.error:
            return status_flag()

        return status_flag(result.error)
