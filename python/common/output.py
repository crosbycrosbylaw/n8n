from __future__ import annotations

import sys

from rampy import console
from rampy.json import JSON, serializable

JSON.configure(indent=0, errors="xmlcharrefreplace")

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


def output[T: serializable](json: JSON[T], *, logs: list[str], warnings: list[str]):
    console.error("\n".join(warnings))
    console.log("RETURN", "\n".join(logs), **json)
