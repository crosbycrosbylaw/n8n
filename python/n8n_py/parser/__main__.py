from common import argument, parse_args

from .cls import Runner

if __name__ == "__main__":
    parse_args(
        argument("-c", "--content", type=str, dest="content", required=True),
        argument("-m", "--mode", type=str, dest="mode", required=True),
        argument("-e", "--email", type=str, dest="email", default="eservice@crosbyandcrosbylaw.com"),
        namespace=Runner(),
    ).invoke()
