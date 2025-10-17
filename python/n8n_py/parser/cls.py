from __future__ import annotations

import html
import typing
from dataclasses import dataclass, field
from urllib.parse import urlencode

import requests
from common import TMP, HTMLParser, Runner
from rampy.json import JSON

if typing.TYPE_CHECKING:
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

        out = [path.as_posix(), None]

        if not path.is_file():
            length = path.write_bytes(self.response.content)
            if self.length and length != self.length:
                out[1] = f"document '{name}' size ({length}) differs from expected ({self.length})"

        return tuple(out)

    def iter_subresponses(self, runner: EmailParser) -> Generator[ResponseUtility]:
        self._require(attachment=False)

        text = self.response.content.decode(self.response.encoding or "utf-8")

        if not any(x in text for x in ["<html", "<head", "__VIEWSTATE"]):
            raise ValueError("unknown_response_type")

        tags = HTMLParser(text).tags("input", string=r"__(VIEW|EVENT)\w+", value=True)

        def value_for(id: str, *, prefix: str = "__", upper: bool = True) -> str:
            id_str = f"{prefix}{id}"
            upper and (id_str := id_str.upper())

            return str([x for x in tags if x["id"] == id_str][0]["value"])

        headers = JSON([("Content-Type", "application/x-www-form-urlencoded")])
        body = JSON(
            emailAddress=runner.email,
            __VIEWSTATE=value_for("viewstate"),
            __VIEWSTATEGENERATOR=value_for("viewstategenerator"),
            __EVENTVALIDATION=value_for("eventvalidation"),
            SubmitEmailAddressButton="Validate",
            username=runner.email,
            SubmitUsernameButton=runner.email,
        )

        return (
            ResponseUtility(requests.post(href, data=urlencode(body), headers=headers.cast()))
            for href in (html.unescape(raw) for raw in runner._parser.find_hrefs(r"ViewDocuments"))
        )


@dataclass()
class EmailParser(Runner):
    _parser: HTMLParser = field(init=False)
    email: str = field(init=False, default="eservice@crosbyandcrosbylaw.com")

    def setup(self) -> None:
        if self.input[1] != "clean":
            self._parser = HTMLParser(self.input[1])

    def run(self) -> None:
        match self.input[1]:
            case "clean":
                [f.unlink() for f in TMP.iterdir() if self.logs.append(f"removing {f.name}") is None]
            case _:
                hrefs = self._parser.find_hrefs(r"Download Document")
                if len(hrefs) < 1:
                    raise ValueError("download link not found")

                [self._process_href(h) for h in hrefs]

    def _process_href(self, href: str) -> None:
        self.logs.append(f"processing extracted href: {href}")

        res = ResponseUtility(requests.get(href))
        responses = [res] if res.has_attachment else res.iter_subresponses(self)
        paths: list[str] = []

        for r in responses:
            if r.has_attachment:
                path, warning = r.save_attachment()
                paths.append(path)

                self.logs.append(f"saved document to {path}")
                if warning:
                    self.warnings.append(warning)

        self.json["paths"] = paths
