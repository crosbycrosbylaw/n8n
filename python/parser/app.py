from parser.cls import HtmlParser
import typer

app = typer.Typer()


@app.command(name="parse_link")
def parse_download_url(parser: HtmlParser) -> None:
    from utils.output import stdout

    stdout(matching=parser.parse_links(r"Download Document"))


@app.command(name="parse_response")
def parse_download_http_response(parser: HtmlParser) -> None:
    from utils.output import stdout

    tags = parser.tags("input", id=r"__(VIEW|EVENT)\w+", value=True)

    def value_for(id: str) -> str:
        return str([x for x in tags if x["id"] == "__VIEWSTATE"][0]["value"])

    links = [
        raw.replace(";", "").replace("amp", "") for raw in parser.parse_links(r"ViewDocuments")
    ]

    return stdout(
        links=links,
        data={
            "emailAddress": "eservice@crosbyandcrosbylaw.com",
            "__viewstate": value_for("__VIEWSTATE"),
            "__viewstategenerator": value_for("__VIEWSTATEGENERATOR"),
            "__eventvalidation": value_for("__EVENTVALIDATION"),
        },
    )


if __name__ == "__main__":
    app()
