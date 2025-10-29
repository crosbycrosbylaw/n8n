__all__ = ["Response"]


class Response:
    def __init__(self, content: bytes, headers: dict[str, str] | None = None, encoding: str = "utf-8"):
        self.content = content
        self.headers = headers or {}
        self.encoding = encoding

    def raise_for_status(self):
        return None
