"""Monitor module for eserv package."""

__all__ = [
    'BatchResult',
    'EmailProcessor',
    'EmailRecord',
    'GraphClient',
    'ProcessStatus',
    'ProcessedResult',
    'ProcessedResultDict',
    'StatusFlag',
    'processed_result',
    'status_flag',
]

from .client import GraphClient
from .flags import StatusFlag, status_flag
from .processor import EmailProcessor
from .result import ProcessedResult, processed_result
from .types import BatchResult, EmailRecord, ProcessedResultDict, ProcessStatus
