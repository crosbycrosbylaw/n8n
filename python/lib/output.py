from __future__ import annotations

import typing
import sys
import json
import rampy

if typing.TYPE_CHECKING:
    from typing import *


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


def stdout(text: str = "", **struct: object) -> None:
    json_dict = {"text": text, **(struct or {})}
    print(json.dumps(json_dict, default=str), file=sys.stdout, flush=True)


rampy.console.configure(
    handlers=[]
)