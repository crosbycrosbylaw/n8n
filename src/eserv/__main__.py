# pyright: reportMissingTypeStubs = false, reportUnknownMemberType = false


import uuid
from datetime import UTC, datetime
from pathlib import Path

import fire

from eserv.core import Pipeline
from eserv.monitor import EmailRecord


class _CLI:
    @staticmethod
    def process(
        body: str,
        *,
        subject: str = '',
        sender: str = 'commandline',
        environ: str | None = None,
    ) -> None:

        env_path = None if not environ else Path(environ)
        record = EmailRecord(
            uid=f'{uuid.uuid4()}',
            received_at=datetime.now(UTC),
            sender=sender,
            subject=subject,
            html_body=body,
        )

        Pipeline(env_path).process(record)


if __name__ == '__main__':
    fire.Fire(_CLI, ['process'])
