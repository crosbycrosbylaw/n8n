__all__ = ["main"]

from .cls import Runner


def main(content: str, mode: str, email: str = "eservice@crosbyandcrosbylaw.com"):
    return Runner(content=content, mode=mode, email=email).invoke()
