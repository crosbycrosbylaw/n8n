from __future__ import annotations

import typing
import sys
import json

if typing.TYPE_CHECKING:
    from typing import *


def stderr(
    ty: type[Exception] = Exception,
    *data: object,
    exit: bool = True,
    **kwds: object,
) -> None:
    pass_thru = ", ".join([f"{k}={v}" for k, v in kwds.items()])
    print(f"{ty.__name__}({pass_thru})", *data, file=sys.stderr, flush=True)

    exit and sys.exit(0)


def stdout(text: str | None = None, **kwds: object) -> None:
    print(json.dumps({"text": text or "", **kwds}, default=str), file=sys.stdout, flush=True)
