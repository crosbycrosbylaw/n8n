from __future__ import annotations

__all__ = ["main"]

import typing

from common import parse_args

from .cls import Runner

if typing.TYPE_CHECKING:
    from typing import Sequence


def main(args: Sequence[str] | None = None):
    parse_args(namespace=Runner(), program_name="n8n_py.parser", known_args=args).invoke()
