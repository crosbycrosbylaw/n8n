from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from eserv.monitor import status_flag

if TYPE_CHECKING:
    from eserv.monitor.flags import StatusFlag
    from eserv.monitor.types import ErrorDict
    from eserv.util.error_tracking import PipelineStage


@dataclass
class PipelineError(Exception):
    """Pipeline execution error with stage and message."""

    stage: PipelineStage
    message: str

    def info(self) -> ErrorDict:
        """Convert pipeline error to dictionary format.

        Returns:
            ErrorDict with category and message fields.

        """
        return {'category': self.stage.value, 'message': self.message}

    def flag(self) -> StatusFlag:
        return status_flag(error=self.info())
