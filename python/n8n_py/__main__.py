from argparse import ArgumentParser
from pathlib import Path

from . import main

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("path", required=True, type=Path)

    try:
        args = parser.parse_args()
        main(args.path)
    except TypeError:
        import sys

        if len(sys.argv) > 1:
            main(Path(sys.argv[1]))
        else:
            raise
