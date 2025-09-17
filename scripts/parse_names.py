import spacy
import bs4

from typing import Literal


def try_parse(
    content: str,
    *,
    mode: Literal["text", "file"],
) -> tuple[str, str] | tuple[str, str, str] | None:
    match mode:
        case "text":
            soup = bs4.BeautifulSoup(content, "html.parser")
            soup.find(
                # ...
            )
            ...
        case "file":
            spacy.load("en_core_web_sm")
            ...

    return None


def main(email_subj: str, email_body: str, pdf_path: str | None = None):
    names = ()
    for text in email_subj, email_body:
        names = try_parse(text, mode="text")
    if not names and pdf_path:
        names = try_parse(pdf_path, mode="file")
    match len(names or ()):
        case 2:
            ...
        case 3:
            ...
        case _:
            ...
