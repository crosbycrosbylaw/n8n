import re
import json
from bs4 import BeautifulSoup, Tag
from argparse import ArgumentParser


def tag_attr(item: object, attr: str):
    return None if not isinstance(item, Tag) else item.get(attr)


def main(html_content: str, base_url: str) -> str:
    soup = BeautifulSoup(html_content, "html.parser")

    # Extract ASP.NET form state values by their ID
    viewstate = soup.find("input", {"id": "__VIEWSTATE"})
    viewstategenerator = soup.find("input", {"id": "__VIEWSTATEGENERATOR"})
    eventvalidation = soup.find("input", {"id": "__EVENTVALIDATION"})

    links = []
    for link_tag in soup.find_all("a", href=re.compile(r"ViewDocuments")):
        if not isinstance(link_tag, Tag):
            continue

        raw_link = link_tag.get("href")

        if not isinstance(raw_link, str):
            continue

        cleaned_link = raw_link.replace(";", "").replace("amp", "")

        # Construct a full URL if it's a relative link
        if not cleaned_link.startswith("http"):
            # This logic might need to be adjusted based on the specific site's URL structure
            full_link = f"{base_url.split('/V')[0]}{cleaned_link}"
            links.append(full_link)
        else:
            links.append(cleaned_link)

    obj = {
        "data": {
            "emailAddress": "eservice@crosbyandcrosbylaw.com",
            "__viewstate": tag_attr(viewstate, "value"),
            "__viewstategenerator": tag_attr(viewstategenerator, "value"),
            "__eventvalidation": tag_attr(eventvalidation, "value"),
        },
        "links": links,
    }
    return json.dumps(obj, default=str)


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--content", type=str, required=True)
    parser.add_argument("--link", type=str, required=True)
    args = parser.parse_args()
    print(main(args.content, args.link))
