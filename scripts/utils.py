import sys
from argparse import ArgumentParser

parser = ArgumentParser()
parser.add_argument("--content", type=str, dest="content", required=True)


def error(exception: type[Exception], **kwds: object) -> None:
    msg = f"{exception.__name__}({', '.join([f'{k}={v}' for k, v in kwds.items()])})"
    print(msg, file=sys.stderr, flush=True)
