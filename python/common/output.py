from __future__ import annotations

import sys

from rampy import console
from rampy.js import object, serializable

console.remove(0)
console.level("RETURN", 100)
console.add(
    sys.stdout,
    serialize=True,
    filter=lambda rec: rec["level"].name == "RETURN",
)
console.add(
    sys.stderr,
    serialize=True,
    filter=lambda rec: rec["level"].name == "ERROR",
    catch=True,
)
console.level("ERROR", icon=" ")


def output[T: serializable](json: object[T], *, logs: list[str], warnings: list[str]):
    console.error("\n".join(warnings))
    console.log("RETURN", "\n".join(logs), **json)
