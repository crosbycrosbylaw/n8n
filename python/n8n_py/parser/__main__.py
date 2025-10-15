from common import argument, parse_args

from .cls import Runner

if __name__ == "__main__":
    parse_args(
        argument("-m", "--mode", type=str, dest="mode", required=True),
        namespace=Runner(),
        program_name="n8n_py.parser",
    ).invoke()
