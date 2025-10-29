from __future__ import annotations

import html
import typing
from dataclasses import dataclass, field
from urllib.parse import urlencode

import requests
from common import TMP, HTMLParser, Runner
from rampy import debug, json

if typing.TYPE_CHECKING:
    from pathlib import Path
    from typing import *


@dataclass()
class ResponseUtility:
    response: requests.Response = field(init=True, repr=False)

    def __post_init__(self) -> None:
        res = self.response
        res.raise_for_status()

        self.mime_type = res.headers.get("Content-Type")
        self.disposition = res.headers.get("Content-Disposition")

        if length := res.headers.get("Content-Length"):
            self.length = int(length)

    mime_type: str | None = field(init=False)
    disposition: str | None = field(init=False)
    length: int | None = field(default=None, init=False)

    @property
    def has_attachment(self) -> bool:
        required = not self.mime_type or (self.mime_type and self.mime_type not in {"text/html", "application/json"})
        return any(
            bool(x and required)
            for x in [
                self.disposition and "attachment; filename=" in self.disposition,
                self.length is not None and self.length > 0,
            ]
        )

    def _require(self, *, attachment: bool) -> None:
        if self.has_attachment is not attachment:
            raise AttributeError("has_attachment:", not attachment)

    def _get_attachment_name(self) -> str:
        self._require(attachment=True)

        if self.disposition:
            return self.disposition.split("filename=", 1)[-1].strip().split('"')[1]

        count = len([*TMP.iterdir()])
        extension = "txt" if not self.mime_type else self.mime_type.split("/", 1)[-1]
        if ";" in extension:
            extension = extension.split(";")[0]

        return f"attachment_{count}.{extension}"

    def save_attachment(self) -> tuple[str, str | None]:
        self._require(attachment=True)

        name = self._get_attachment_name()
        path = TMP / name

        if debug():
            print(str(path))

        out = [path.as_posix(), None]

        if not path.is_file():
            length = path.write_bytes(self.response.content)
            if self.length and length != self.length:
                out[1] = f"document '{name}' size ({length}) differs from expected ({self.length})"

        return tuple(out)

    def iter_subresponses(self, email: str, parser: HTMLParser) -> Generator[ResponseUtility]:
        self._require(attachment=False)

        text = self.response.content.decode(self.response.encoding or "utf-8")

        if not any(x in text for x in ["<html", "<head", "__VIEWSTATE"]):
            raise ValueError("unknown_response_type")

        tags = HTMLParser(text).tags("input", string=r"__(VIEW|EVENT)\w+", value=True)

        def value_for(id: str, *, prefix: str = "__", upper: bool = True) -> str:
            id_str = f"{prefix}{id}"
            upper and (id_str := id_str.upper())

            return str([x for x in tags if x["id"] == id_str][0]["value"])

        headers = json([("Content-Type", "application/x-www-form-urlencoded")])
        body = json(
            emailAddress=email,
            __VIEWSTATE=value_for("viewstate"),
            __VIEWSTATEGENERATOR=value_for("viewstategenerator"),
            __EVENTVALIDATION=value_for("eventvalidation"),
            SubmitEmailAddressButton="Validate",
            username=email,
            SubmitUsernameButton=email,
        )

        return (
            ResponseUtility(requests.post(href, data=urlencode(body), headers=headers.cast()))
            for href in (html.unescape(raw) for raw in parser.find_hrefs(r"ViewDocuments"))
        )


@dataclass()
class EmailParser(Runner):
    content: str | None = field(init=False, default=None)
    email: str = field(init=False, default="eservice@crosbyandcrosbylaw.com")

    def setup(self):
        item = self.input[0]
        if item != "clean":
            self.content = item

        return self

    def run(self):
        match self.content:
            case None:

                def rm(f: Path) -> None:
                    self.logs.append(f"removing {f.name}")
                    f.unlink()

                [rm(f) for f in TMP.iterdir()]

            case _:
                parser = HTMLParser(self.content)
                hrefs = parser.find_hrefs(r"Download Document")

                if len(hrefs) < 1:
                    raise ValueError("download link not found")

                paths: list[str] = []

                def process(link: str) -> None:
                    self.logs.append(f"processing extracted href: {link}")
                    res = ResponseUtility(requests.get(link))
                    responses = [res] if res.has_attachment else res.iter_subresponses(self.email, parser)
                    for r in responses:
                        if r.has_attachment:
                            path, warning = r.save_attachment()
                            if warning:
                                self.warnings.append(warning)
                            paths.append(path)
                            self.logs.append(f"saved document to {path}")
                        else:
                            self.warnings.append(f"missing document for link: {link}")

                [process(h) for h in hrefs]

                self.json["paths"] = paths

        return self
