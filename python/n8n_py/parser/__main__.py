import sys

from . import clean, main

if __name__ == "__main__":
    if "clear_temporary_files" in sys.argv:
        clean()
    else:
        main()
