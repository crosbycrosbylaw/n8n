from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


@dataclass(kw_only=True, frozen=True, slots=True)
class scenario:
    exception: type[Exception] | None = None
    switches: set[str] | None = None
