import sys
from argparse import ArgumentParser
from bs4 import BeautifulSoup, Tag


def error(exception: type[Exception], **kwds: object) -> None:
    msg = f"{exception.__name__}({', '.join([f'{k}={v}' for k, v in kwds.items()])})"
    print(msg, file=sys.stderr, flush=True)


def main(content: str) -> str | None:
    elem = BeautifulSoup(content, "html.parser").find("a", string="Download Document")
    if not isinstance(elem, Tag):
        return error(TypeError, expected=Tag, recieved=type(elem))
    link = elem.get("href")
    if not isinstance(link, str):
        return error(TypeError, expected=str, recieved=type(link))
    return link


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--content", type=str, required=True)
    args = parser.parse_args()
    print(main(args.content))
