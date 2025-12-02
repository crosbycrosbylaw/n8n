"""Utility modules for document processing pipeline."""

from __future__ import annotations

__all__ = [
    'CaseMatch',
    'Config',
    'CredentialManager',
    'EmailState',
    'ErrorTracker',
    'FolderMatcher',
    'IndexCache',
    'NotificationConfig',
    'Notifier',
    'OAuthCredential',
    'PartyExtractor',
    'PipelineStage',
    'extract_case_names_from_pdf',
    'extract_text_from_pdf',
    'extract_text_from_store',
    'get_document_store',
]

from .config import Config
from .doc_store import get_document_store
from .email_state import EmailState
from .error_tracking import ErrorTracker, PipelineStage
from .index_cache import IndexCache
from .notifications import NotificationConfig, Notifier
from .oauth_manager import CredentialManager, OAuthCredential
from .pdf_utils import extract_text_from_pdf, extract_text_from_store
from .target_finder import CaseMatch, FolderMatcher, PartyExtractor, extract_case_names_from_pdf
