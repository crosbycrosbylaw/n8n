from __future__ import annotations

import re
import typing
from types import SimpleNamespace

if typing.TYPE_CHECKING:
    from typing import Final


class regex(SimpleNamespace):
    vs: Final = re.compile(
        r"(?P<left>[^\n<>;]{1,300})\s*(?P<sep>v\.?|vs\.?|\bvs\b|\bv\b)\s*(?P<right>[^\n<>;]{1,300})", flags=re.I
    )
    hint: Final = re.compile(
        r"(?:case style|in the matter of|envelope number|case number|case name)[:\s-]*([^\n]{1,1000})", flags=re.I
    )


class keywords(SimpleNamespace):
    corporate: Final = {
        "inc",
        "llc",
        "corp",
        "co",
        "ltd",
        "company",
        "bank",
        "county",
        "city",
        "state",
        "authority",
        "department",
        "university",
        "school",
        "hospital",
    }
