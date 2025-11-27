from argparse import ArgumentParser
from pathlib import Path

from . import main

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('path', required=True, type=Path)

    args = parser.parse_args()

    main(args.path)
