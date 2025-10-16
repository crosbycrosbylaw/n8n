from __future__ import annotations

__all__ = ["main"]


from .cls import Runner


def main(input: str):
    Runner(input=input.replace("^", '"'))
