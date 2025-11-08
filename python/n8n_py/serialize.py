from __future__ import annotations

import json
import sys
import traceback
import typing
from functools import wraps

if typing.TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence

    from rampy import js


class OutputDict(typing.TypedDict):
    text: str | None
    items: Sequence[js.serializable]
    data: Mapping[str, js.serializable]


def serialize_output[**P, T](func: Callable[P, T]) -> Callable[P, None]:
    @wraps(func)
    def wrapper(*args: P.args, **kwds: P.kwargs) -> None:
        try:
            output_dict: OutputDict = {"text": None, "items": [], "data": {}}
            result = func(*args, **kwds)

            if isinstance(result, str):
                output_dict["text"] = result
            elif isinstance(result, dict):
                output_dict["data"] = result
            elif isinstance(result, list):
                output_dict["items"] = result
            else:
                output_dict["items"] = [f"{result!s}"]

            serialized = json.dumps(output_dict, separators=(",", ":"), skipkeys=True, sort_keys=True)

            print(serialized, file=sys.stdout, flush=True)

            exit_code = 0

        except Exception as exc:
            formatted = traceback.format_exception(exc)
            serialized = json.dumps({"exception": formatted})

            print(serialized, file=sys.stderr, flush=True)

            exit_code = 1

        sys.exit(exit_code)

    return wrapper
