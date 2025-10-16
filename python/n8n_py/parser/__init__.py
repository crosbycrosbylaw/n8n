from __future__ import annotations

__all__ = ["main"]

import sys

from .cls import Runner


def main(input: str):
    Runner(input=input)
