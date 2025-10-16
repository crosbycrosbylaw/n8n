from __future__ import annotations

import sys

from rampy import console, typed
from rampy.json import JSON

if "CONSOLE_INIT" not in globals():
    console.remove(0)
    console.level("RETURN", 100)
    console.add(
        sink=sys.stdout,
        filter=lambda rec: rec["level"].name == "RETURN",
        format="{message}",
    )
    console.level("ERROR", icon=None)
    console.add(
        sys.stderr,
        filter=lambda rec: rec["level"].name == "ERROR",
        catch=True,
    )
    globals()["CONSOLE_INIT"] = True


def stderr(error: str | Exception | type[Exception], *info: object) -> None:
    if typed(type[Exception])(error):
        error = error.__name__
    elif typed(Exception)(error):
        error = str(error)

    console.error(error, *info)


def stdout(**kwds: ...) -> None:
    text = kwds.pop("text", "")
    console.patch(
        lambda rec: rec.update(message=repr(JSON(text=rec["message"], **kwds))),
    ).log("RETURN", text)
