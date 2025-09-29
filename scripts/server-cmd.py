from argparse import ArgumentParser

from rampy import root, sh


def main(*script_cmds: str) -> None:
    session_string = f"({str(root.join('scripts', 'server-session.ps1', resolve=True))})"
    scriptblock_string = f"{{{'\n\r'.join(script_cmds)}}}"
    sh.logs.enable()
    sh.pwsh(f"icm -session {session_string} -scriptblock {scriptblock_string}")
    sh.logs.disable()


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument(type=str, nargs="+", dest="commands")
    args = parser.parse_args()
    main(*args.commands)
