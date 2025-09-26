from __future__ import annotations

import typing
import sys
from rampy import console

if typing.TYPE_CHECKING:
    from typing import *

try:
    console.level("RETURN")
except ValueError:
    console.remove(0)
    console.level("RETURN", 100)
    console.add(
        sink=sys.stdout,
        serialize=True,
        format=lambda rec: rec["message"],
        level="RETURN",
    )


def stderr(
    ty: type[Exception] = Exception,
    *data: object,
    exit: bool = True,
    **kwds: object,
) -> None:
    error_args = ", ".join(f"{k}={v}" for k, v in kwds.items())
    print(f"{ty.__name__}({error_args})", *data, file=sys.stderr, flush=True)
    if not exit:
        return
    sys.exit(0)


def stdout(text: str | None = None, **struct: object) -> None:
    console.log("RETURN", str(text), **struct)
