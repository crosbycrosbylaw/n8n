import sys

import * as parser

if __name__ == "__main__":
    if sys.argv[1] == "clean":
        parser.clean()
    else:
        parser.main()
