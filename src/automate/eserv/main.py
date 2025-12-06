"""Provides a high-level interface for automating file-stamped document uploads."""
# ruff: noqa: PLW0603


def process(
    body,
    dotenv: str | None = None,
    uid: str | None = None,
    received: str | None = None,
    subject: str = '',
    sender: str = 'unknown',
):
    """Execute pipeline for a single email record.

    Args:
        body (str):
            The body of an email record to process.

    Kwargs:
        dotenv (str | None):
            Path to a file containing the necessary environment variables.
        uid (str | None):
            Unique identifier for the email record.
        received (datetime | None):
            Timestamp when the email was received.
        subject (str):
            The subject line of the email.
        sender (str):
            The sender's email address or name.

    Returns:
        ProcessedResult with processing status and error information if applicable.

    """
    from typing import TYPE_CHECKING

    from automate.eserv.core import setup_eserv
    from automate.eserv.record import record_factory

    if TYPE_CHECKING:
        from typing import Any

    dotenv_path = None

    if dotenv is not None:
        from pathlib import Path

        dotenv_path = Path(dotenv)

    kwds: dict[str, Any] = {
        'uid': uid,
        'subject': subject,
        'sender': sender,
        'received_at': None,
    }

    if received is not None:
        from datetime import datetime

        kwds['received_at'] = datetime.fromisoformat(received)

    return setup_eserv(dotenv_path).execute(record_factory(body, **kwds))


def monitor(dotenv: str | None = None, lookback: int = 1):
    """Monitor email inbox and process new messages.

    Args:
        dotenv (str | None):
            Path to a file containing the necessary environment variables.
        lookback (int):
            Process emails from past N days.

    Returns:
        BatchResult with summary and per-email results.

    """
    global dotenv_path

    from automate.eserv.core import setup_eserv

    dotenv_path = None

    if dotenv is not None:
        from pathlib import Path

        dotenv_path = Path(dotenv)

    return setup_eserv(dotenv_path).monitor(num_days=lookback)
