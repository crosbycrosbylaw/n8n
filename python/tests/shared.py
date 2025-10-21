from __future__ import annotations

import functools
import os
import typing as ty
from pathlib import Path

from rampy import js, typed

if ty.TYPE_CHECKING:
    from os import PathLike, _Environ
    from typing import Any, Callable, Generator, Literal, Sequence

    from pytest import Mark

import pytest

type VarsDict = dict[str, object]
type VarsFunction[T: VarsDict | None] = Callable[[VarsDict], T]
type TestExtensionFunc = Callable[[dict[str, object]], None]


class TempPath(Path):
    def __init__(self, *args: str | PathLike[str]) -> None:
        super().__init__("d:/temp/pytest", *args)

    def mkdir(self, mode: int = 777, parents: bool = True, exist_ok: bool = True) -> None:
        return super().mkdir(mode, parents, exist_ok)

    def touch(self, mode: int = 777, exist_ok: bool = True) -> None:
        return super().touch(mode, exist_ok)


def path(*strpath: str | os.PathLike[str]) -> TempPath:
    return TempPath(*strpath)


class TestHook:
    def __init__(self, order: Literal["before", "after"], names: list[str], values: list[str]) -> None:
        self.items = zip(names, values, strict=True)
        self.order = order

    @staticmethod
    def is_before(hook: TestHook) -> bool:
        return hook.order == "before"

    @staticmethod
    def is_after(hook: TestHook) -> bool:
        return hook.order == "after"

    def __call__(self, vars: VarsDict) -> VarsDict:
        for name, value in self.items:
            vars[name] = eval(value)

        return vars


class ExceptionHandler:
    def __init__(
        self,
        func: ty.Callable[[Exception | ExceptionGroup, VarsDict], Any],
        types: ty.Sequence[type[Exception]] = (AssertionError,),
    ):
        self.types = types
        self.func = func

    def __call__(self, exc: Exception | ExceptionGroup, ctx: VarsDict) -> None:
        if any(typed(t)(exc) for t in self.types):
            self.func(exc, ctx)


@ty.overload
def hook(
    func: ty.Callable[[Exception | ExceptionGroup, VarsDict], Any],
    types: ty.Sequence[type[Exception]] = (AssertionError,),
) -> ExceptionHandler:
    pass


@ty.overload
def hook(order: ty.Literal["before", "after"], names: list[str], values: list[str]) -> TestHook:
    pass


def hook[T](*args, **kwds):
    first: T = next(iter(args))

    if callable(first):
        return ExceptionHandler(*args, **kwds)
    if first in {"before", "after"}:
        return TestHook(*args, **kwds)

    raise TypeError("unsupported argument types")


class TestSpec:
    arguments: tuple[list[str], list[str]]
    predicates: list[str] | None
    hooks: Sequence[TestHook | ExceptionHandler] | None
    marks: tuple[Mark, ...]

    def __init__(
        self,
        arguments: tuple[list[str], list[str]],
        predicates: list[str] | None = None,
        *,
        hooks: Sequence[TestHook | ExceptionHandler] | None = None,
        marks: tuple[Mark, ...] = (),
    ) -> None:
        self.arguments = arguments
        self.predicates = predicates
        self.hooks = hooks
        self.marks = marks

    @property
    def ordered_hooks(self) -> ty.Generator[TestHook]:
        return (h for h in (self.hooks or []) if typed(TestHook)(h))

    @property
    def exception_hooks(self) -> ty.Generator[ExceptionHandler]:
        return (h for h in (self.hooks or []) if not typed(TestHook)(h))

    def before(self) -> None:
        if not self.hooks:
            return

        js.array(self.ordered_hooks).filter(TestHook.is_before).foreach(lambda hook: self.ctx.update(hook(self.ctx)))

    def after(self) -> None:
        if not self.hooks:
            return

        def discard_vars(hook):
            hook(self.ctx)

        js.array(self.ordered_hooks).filter(TestHook.is_after).foreach(discard_vars)

    def onexcept(self, exc: ...) -> None:
        js.array(self.exception_hooks).foreach(lambda x: x(exc, self.ctx))

    def extension(self):
        for predicate in self.predicates or []:
            assert eval(predicate, globals=self.ctx)

    def param(self, desc: str):
        return pytest.param(*self.arguments, self.main, marks=self.marks, id=desc)

    def main(self, ctx: VarsDict) -> None:
        self.ctx = {**locals(), **globals(), **ctx}
        self.before()
        try:
            self.extension()
        except Exception as exc:
            self.onexcept(exc)
            raise
        self.after()


def spec(
    arguments: tuple[list[str], list[str]],
    predicates: list[str] | None = None,
    *,
    hooks: Sequence[TestHook | ExceptionHandler] | None = None,
    marks: tuple[Mark, ...] = (),
) -> TestSpec:
    return TestSpec(arguments=arguments, predicates=predicates, hooks=hooks, marks=marks)


@pytest.fixture
def env() -> Generator[_Environ[str]]:
    initial_env = os.environ.copy()

    yield os.environ

    os.environ = initial_env


def suite[**P, T](param_names: list[str], predefined: dict[str, TestSpec] | None = None, **inline: TestSpec):
    test_dict = inline

    if predefined:
        test_dict.update(predefined)

    def decorator(func: Callable[P, T]):
        param_sets = js.array(test_dict.items()).map(lambda kv: kv[1].param(kv[0]))

        @functools.wraps(func)
        @pytest.mark.parametrize(param_names, param_sets)
        def wrapper(*args: P.args, **kwds: P.kwargs) -> T:
            return func(*args, **kwds)

        return wrapper

    return decorator
