from __future__ import annotations

from datetime import UTC, datetime

__all__ = [
    'DocumentDownloadError',
    'DocumentExtractionError',
    'DocumentUploadError',
    'EmailParseError',
    'FolderResolutionError',
    'PipelineError',
]

from dataclasses import InitVar, dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar, Final

from rampy import console

from eserv.monitor.flags import status_flag_factory
from eserv.types.enums import PipelineStage

if TYPE_CHECKING:
    from collections.abc import Iterable

    from eserv.types import ErrorDict, StatusFlag

_FIELDS: Final[Iterable[tuple[str, type[Any], Any]]] = [
    ('message', str, field(default='an unknown error occured')),
    ('positionals', list[object], field(default_factory=list)),
    ('timestamp', str, field(default_factory=lambda: datetime.now(UTC).isoformat())),
    ('context', dict[str, object], field(default_factory=dict, repr=False)),
]


@dataclass(slots=True, kw_only=True)
class PipelineError(Exception):
    """Pipeline execution error with stage and message."""

    stage: ClassVar[PipelineStage] = PipelineStage.UNKNOWN

    uid: str | None = field(default=None)
    message: str | None = field(default='an unknown error occured')
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    context: dict[str, object] = field(default_factory=dict, repr=False)

    args: InitVar[tuple[object, ...]] = field(default=())

    @property
    def category(self) -> str:
        return self.stage.value

    @property
    def positionals(self) -> list[object]:
        return [*super().args]

    @classmethod
    def default_message(cls) -> str:
        return cls.__dataclass_fields__['message'].default

    def __post_init__(self, args: tuple[object, ...]):
        self.message = self.message or self.default_message()
        super().__init__(self.message, *args)

    def __str__(self):
        return repr(self)

    def update(
        self,
        context: dict[str, object] | None = None,
        *,
        uid: str | None = None,
        timestamp: datetime | None = None,
        **kwds: object,
    ) -> None:
        """Update the fields of this PipelineError.

        Args:
            uid (str | None):
                If provided value is a string, it will overwrite the current `uid` field.
            positionals (Sequence[object]):
                If provided, these values will be used to extend the `positionals` field.
            timestamp (datetime | None):
                If provided value is a datetime, it will overwrite the current `timestamp` field.
            context (dict[str, object] | None):
                If provided, this value will be used to update the `context` field.
            **kwds (**dict[str, object]):
                An alternative way to pass values to update the `context` field with.

        """
        self.uid = uid

        self.context.update(**context or {}, **kwds)

        if timestamp is not None:
            self.timestamp = timestamp.isoformat()

    def print(self, event: str | None = None) -> None:
        """Print this error to the console."""
        event = event or type(self).__name__
        console.bind(**self.context, uid=self.uid, exc_info=self).exception(event=event)

    def entry(self) -> ErrorDict:
        """Convert pipeline error to dictionary format.

        Returns:
            out (ErrorDict):
                This error as a dictionary with positionals added to the context.

        """
        out: ErrorDict = {
            'uid': self.uid,
            'category': self.category,
            'message': self.message,
            'timestamp': self.timestamp,
        }

        if context := self.context.copy():
            context['args'] = self.positionals
            out['context'] = context

        return out

    def flag(self) -> StatusFlag:
        return status_flag_factory(error=self.entry())

    @staticmethod
    def _resolve_stage(stage: PipelineStage | None) -> type[PipelineError]:
        match (stage or PipelineStage.UNKNOWN).value:
            case 'unknown':
                return PipelineError
            case 'parsing':
                return EmailParseError
            case 'download':
                return DocumentDownloadError
            case 'extraction':
                return DocumentExtractionError
            case 'matching':
                return FolderResolutionError
            case 'upload':
                return DocumentUploadError

    @classmethod
    def from_stage(
        cls,
        stage: PipelineStage | None,
        *,
        uid: str | None = None,
        message: str | None = None,
        timestamp: str | None = None,
        context: dict[str, object] | None = None,
    ):
        scope = locals()
        error_cls = cls._resolve_stage(scope.pop('stage'))
        return error_cls(**{
            name: value for name in cls.__dataclass_fields__ if (value := scope.get(name))
        })


@dataclass
class DocumentDownloadError(PipelineError):
    stage: ClassVar = PipelineStage.DOCUMENT_DOWNLOAD

    message: str | None = field(
        default='an unknown error occured during document download sequence.',
    )
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    context: dict[str, object] = field(default_factory=dict, repr=False)


@dataclass
class DocumentUploadError(PipelineError):
    stage: ClassVar = PipelineStage.DROPBOX_UPLOAD

    message: str | None = field(
        default='an unknown error occured during Dropbox upload sequence.',
    )
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    context: dict[str, object] = field(default_factory=dict, repr=False)


@dataclass
class EmailParseError(PipelineError):
    stage: ClassVar = PipelineStage.EMAIL_PARSING

    message: str | None = field(
        default='an unknown error occured during email HTML parsing.',
    )
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    context: dict[str, object] = field(default_factory=dict, repr=False)


@dataclass
class DocumentExtractionError(PipelineError):
    stage: ClassVar = PipelineStage.PDF_EXTRACTION

    message: str | None = field(
        default='an unknown error occured during PDF text extraction',
    )
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    context: dict[str, object] = field(default_factory=dict, repr=False)


@dataclass
class FolderResolutionError(PipelineError):
    stage: ClassVar = PipelineStage.FOLDER_MATCHING

    message: str | None = field(
        default='an unknown error occured during Dropbox folder resolution.',
    )
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    context: dict[str, object] = field(default_factory=dict, repr=False)
