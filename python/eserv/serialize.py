# ruff: noqa: T201, BLE001

from __future__ import annotations

import json
import sys
import traceback
import typing
from functools import wraps
from typing import NoReturn

if typing.TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence

    from rampy import js


class OutputDict(typing.TypedDict):
    """A TypedDict representing the structure of output data.

    Attributes:
        text : str | None
            Optional text content to be included in the output.
        items : Sequence[js.serializable]
            A sequence of serializable items to be included in the output.
        data : Mapping[str, js.serializable]
            A mapping of string keys to serializable values for additional data.

    """

    text: str | None
    items: Sequence[js.serializable]
    data: Mapping[str, js.serializable]


def serialize_output[**P, T](func: Callable[P, T]) -> Callable[P, NoReturn]:
    """Serialize the output of the decorated function into JSON format.

    This wrapper catches the return value of the decorated function and converts it into
    a standardized JSON output format. The output is printed to stdout on success or
    stderr on failure, and the program exits with an appropriate exit code.

    Args:
        func (Callable[**P, T]):
            The function to recieve and handle the output for.

    Returns:
        NoReturn: This function always exits the program and does not return.
    Output Format:
        Success (stdout):
            - If result is str: {"text": result, "items": [], "data": {}}
            - If result is dict: {"text": null, "items": [], "data": result}
            - If result is list: {"text": null, "items": result, "data": {}}
            - Otherwise: {"text": null, "items": [str(result)], "data": {}}
        Failure (stderr):
            - {"exception": [traceback_lines]}
    Exit Codes:
        0: Function executed successfully
        1: An exception occurred during execution
    Note:
        This function will always terminate the program by calling sys.exit().

    """

    @wraps(func)
    def wrapper(*args: P.args, **kwds: P.kwargs) -> NoReturn:
        try:
            output_dict: OutputDict = {'text': None, 'items': [], 'data': {}}
            result = func(*args, **kwds)

            if isinstance(result, str):
                output_dict['text'] = result
            elif isinstance(result, dict):
                output_dict['data'] = result
            elif isinstance(result, list):
                output_dict['items'] = result
            else:
                output_dict['items'] = [f'{result!s}']

            serialized = json.dumps(
                output_dict, separators=(',', ':'), skipkeys=True, sort_keys=True
            )

            print(serialized, file=sys.stdout, flush=True)

            exit_code = 0

        except Exception as exc:
            formatted = traceback.format_exception(exc)
            serialized = json.dumps({'exception': formatted})

            print(serialized, file=sys.stderr, flush=True)

            exit_code = 1

        sys.exit(exit_code)

    return wrapper
