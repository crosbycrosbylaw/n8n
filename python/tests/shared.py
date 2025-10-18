import os
from pathlib import Path


def temp(*strpath: str | Path):
    class temp(Path):
        base = Path("d:/temp/pytest")

        def __init__(self, *strpath: str | Path) -> None:
            if not self.base.exists():
                self.base.mkdir(777, parents=True)
            super().__init__(self.base, *strpath)

    return temp(*strpath)


def env(**vars: str) -> os._Environ[str]:
    vars.update(TEST="true")
    os.environ.update(vars)
    return os.environ
