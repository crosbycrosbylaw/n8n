from parser.cls import HTMLParser
from lib.output import stdout
from argparse import ArgumentParser, Namespace


class Runner(Namespace):
    mode: str
    content: str
    email: str

    _parser: HTMLParser

    def _parse_download_link(self) -> None:
        [first, *rest] = self._parser.find_hrefs(r"Download Document")
        stdout(first, other=rest)

    def _parse_http_response(self) -> None:
        tags = self._parser.tags("input", id=r"__(VIEW|EVENT)\w+", value=True)

        def value_for(id: str, *, prefix: str = "__", upper: bool = True) -> str:
            id_str = f"{prefix}{id}"
            upper and (id_str := id_str.upper())

            return str([x for x in tags if x["id"] == id_str][0]["value"])

        links = [
            raw.replace(";", "").replace("amp", "") for raw in self._parser.find_hrefs(r"ViewDocuments")
        ]

        return stdout(
            links=links,
            data={
                "emailAddress": self.email,
                "__viewstate": value_for("viewstate"),
                "__viewstategenerator": value_for("viewstategenerator"),
                "__eventvalidation": value_for("eventvalidation"),
            },
        )

    def invoke(self) -> None:
        self._parser = HTMLParser(self.content)
        match self.mode:
            case "link":
                self._parse_download_link()
            case "response":
                self._parse_http_response()
            case _:
                raise ValueError("invalid_mode:", self.mode)


def runner():
    parser = ArgumentParser()

    def mode_type(raw: object) -> str:
        string = str(raw)
        if string not in {"link", "response"}:
            raise TypeError("mode:", type(raw))
        return string

    parser.add_argument("--mode", "-m", type=mode_type, dest="mode", required=True)
    parser.add_argument("--content", "-c", type=HTMLParser, dest="content", required=True)
    parser.add_argument("--email", "-e", type=str, dest="email", default="eservice@crosbyandcrosbylaw.com")

    return parser.parse_args(namespace=Runner())


if __name__ == "__main__":
    runner().invoke()
