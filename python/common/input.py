from __future__ import annotations

import typing
from argparse import ArgumentParser, Namespace

if typing.TYPE_CHECKING:
    from argparse import Action, _ActionType
    from collections.abc import *
    from types import *
    from typing import *


class ArgumentParameters[_T](typing.TypedDict, total=False):
    action: str | type[Action]
    nargs: int | str | None
    const: Any
    default: Any
    type: _ActionType
    choices: Iterable[_T] | None
    required: bool
    help: str | None
    metavar: str | tuple[str, ...] | None
    dest: str | None
    version: str


type ArgSpecTuple[T] = Tuple[Sequence[str], ArgumentParameters[T]]
type ArgSpecDict[T] = MutableMapping[Sequence[str], ArgumentParameters[T]]


def parse_args[N: Namespace](
    *args_ls: ArgSpecTuple[Any],
    args_dict: ArgSpecDict[Any] = {},
    namespace: N = Namespace(),
    program_name: str | None = None,
) -> N:
    args_dict.update(dict(args_ls))
    parser = ArgumentParser(program_name)
    if not any("input" in ls for ls in args_dict.keys()):
        parser.add_argument("input", type=lambda x: rf"{x}")
    [parser.add_argument(*als, **args) for als, args in args_dict.items()]
    return parser.parse_args(namespace=namespace)


def argument[_T](
    *aliases: str,
    action: str | type[Action] = "",
    nargs: int | str | None = None,
    const: Any | None = None,
    default: Any | None = None,
    type: _ActionType | None = None,
    choices: Iterable[_T] | None = None,
    required: bool = False,
    help: str | None = None,
    metavar: str | tuple[str, ...] | None = None,
    dest: str | None = None,
    version: str = "",
    **kwds: ...,
) -> ArgSpecTuple[_T]:
    input_dict = {
        "action": action,
        "nargs": nargs,
        "const": const,
        "default": default,
        "type": type,
        "choices": choices,
        "required": required,
        "help": help,
        "metavar": metavar,
        "dest": dest,
        "version": version,
    }
    kwds.update({k: v for k, v in input_dict.items() if v})
    return aliases, typing.cast(ArgumentParameters[_T], kwds)
