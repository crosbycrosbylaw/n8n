# %%
from __future__ import annotations

import dataclasses as dc
import time
import typing as ty
from pathlib import Path
from urllib.parse import urlencode

import requests
from pydantic import HttpUrl
from rampy import json

from common.metadata import _DocumentMetadata
from common.parsehtml import HTMLParser
from common.temp import TMP

if ty.TYPE_CHECKING:
    from typing import Any

    from common.metadata import MetadataDict


@dc.dataclass
class FieldMetadataMixin:
    def __getitem__[T: dict[Any, Any] = dict[str, Any]](self, name: str, default: T | None = None) -> T:
        if not dc.is_dataclass(self):
            raise TypeError(_ := "not_a_dataclass")
        try:
            return self.__dataclass_fields__[name].metadata
        except KeyError:
            return default or {}

    def __setitem__[T: dict[Any, Any] = dict[str, Any]](self, name: str, value: T) -> None:
        if not dc.is_dataclass(self):
            raise TypeError("not_a_dataclass")
        try:
            self.__dataclass_fields__[name].metadata = value
        except KeyError:
            self.__dataclass_fields__[name] = dc.field(init=False, repr=False, metadata=value)


class Metadata:
    __slots__ = ("_dict",)

    def __init__(self, dictionary: MetadataDict) -> None:
        self._dict = dictionary

    def serialize(self) -> str:
        return repr(json(self._dict))


@dc.dataclass
class Document(FieldMetadataMixin):
    href: str = dc.field(metadata={})
    name: str = dc.field(default="untitled", metadata={"parent": None, "length": None})

    @property
    def url(self) -> HttpUrl | None:
        return self["href"].setdefault("url", HttpUrl(self.href))

    @property
    def headers(self) -> dict[str, str]:
        return self["href"].setdefault("headers", {})

    @property
    def path(self) -> Path | None:
        return None if not isinstance(parent := self["name"]["parent"], Path) else parent / self.name

    def _fetch(self) -> requests.Response:
        response = requests.get(self.href)
        self["href"]["headers"].update(response.headers)
        return response

    def _process(self, text: str, **headers: str) -> bool:
        content_type = (headers or self.headers).get("Content-Type", "")
        if "application/pdf" in content_type:
            return True

        if any(s in content_type for s in ["text/html", "application/json"]):
            from common import HTMLParser

            parser = HTMLParser(text)
            tags = parser.tags("input", string=r"__(VIEW|EVENT)\w+", value=True)

            def value_for(id: str, *, prefix: str = "__", upper: bool = True) -> str:
                text = f"{prefix}{id}"
                text = text if not upper else text.upper()
                return str(next(x for x in tags if x["id"] == text)["value"])

            email = "eservice@crosbyandcrosbylaw.com"
            response = requests.post(
                self.href,
                data=urlencode(
                    {
                        "emailAddress": email,
                        "__VIEWSTATE": value_for("viewstate"),
                        "__VIEWSTATEGENERATOR": value_for("viewstategenerator"),
                        "__EVENTVALIDATION": value_for("eventvalidation"),
                        "SubmitEmailAddressButton": "Validate",
                        "username": email,
                        "SubmitUsernameButton": email,
                    },
                ),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            return self._process(response.text, **response.headers)

        return False

    def save(self) -> bool:
        if path := self.path:
            res = self._fetch()
            is_binary = self._process(res.text)
            if is_binary:
                self.size = path.write_bytes(res.content)
            else:  # TODO !!!
                ...
        return self.processed

    @property
    def processed(self) -> bool:
        return self["name"]["length"] is not None

    @processed.setter
    def size(self, length: int) -> None:
        self["name"]["length"] = length


def get_document_metadata(doc: Document) -> _DocumentMetadata:
    return {
        "processed": doc.processed,
        "document": {
            "name": doc.name,
            "directory": str(doc["name"]["parent"]),
            "length": str(doc["name"]["length"]),
        },
        "response": {
            "url": str(doc["href"]["url"]),
            "headers": doc["href"]["headers"],
        },
    }


@dc.dataclass
class LeadDocument(Document):
    desc: str | None = dc.field(default=None)
    docs: list[Document] = dc.field(default_factory=list, metadata={"count": 0})

    def asdict(self) -> dict[str, str | None]:
        return dc.asdict(self)

    def __post_init__(self) -> None:
        parent = self["name"]["parent"] = TMP / str(hash(self.name))
        parent.mkdir(parents=True, exist_ok=True)
        for doc in self.docs:
            doc["name"]["parent"] = parent
            if doc.path is None:
                raise ValueError(doc.path)
            doc.path.touch(exist_ok=True)


@dc.dataclass
class DocumentSet(LeadDocument):
    @property
    def directory(self) -> Path:
        return self["name"]["parent"]

    _metadata: str = dc.field(default="{}", metadata={"updated": None})

    @property
    def metadata(self) -> str:
        return self._metadata

    def update_metadata(self, refresh: bool = True, **kwds: object) -> None:
        if kwds and not refresh:
            self["_metadata"].update(kwds)
            return

        self["_metadata"].update(
            **kwds,
            updated=time.ctime(),
            desc=self.desc,
            docs=[get_document_metadata(doc) for doc in [self, *self.docs]],
        )
        self._metadata = repr(json(self["_metadata"]))

    def __post_init__(self) -> None:
        documents: list[Document] = [self, *self.docs]

        for doc in documents:
            success = doc.save()
            if success:  # TODO
                ...
            else:  # TODO
                ...

        self.update_metadata()
        return super().__post_init__()

    @property
    def path_display(self) -> str | None:
        return self["name"].get("path_display")

    @path_display.setter
    def path_display(self, value: str) -> None:
        self["name"]["path_display"] = value


@ty.overload
def collect_document_information(__parser: HTMLParser) -> LeadDocument: ...
@ty.overload
def collect_document_information(__content: str) -> LeadDocument: ...
def collect_document_information(argument) -> LeadDocument:
    parser = argument if isinstance(argument, HTMLParser) else HTMLParser(argument)

    iterator = iter(parser.find_hrefs("Download Document"))
    mapping = parser.find_table_strings({"Case Name": "desc", "Lead Document": "name"})

    def get_href():
        return next(iterator, None)

    if (href := get_href()) is None:
        raise ValueError("missing_hrefs")

    name = mapping.get("name", "untitled")

    ext = "" if not len(parts := name.split(".")) > 1 else f".{parts[-1]}"

    docs: list[Document] = []
    while url := get_href():
        docs.append(Document(name=f"untitled_{len(docs) + 1}{ext}", href=url))

    return LeadDocument(name=name, href=href, desc=mapping.get("desc"), docs=docs)
