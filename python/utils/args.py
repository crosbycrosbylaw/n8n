from argparse import ArgumentParser


parser = ArgumentParser()
parser.add_argument("--content", type=str, dest="content", required=True)


def parse_content() -> str:
    return str(parser.parse_args().content)
