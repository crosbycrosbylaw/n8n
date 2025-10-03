from argparse import ArgumentParser

from rampy import root, sh

sh.logs.pretty()


def main(*script_cmds: str) -> None:
    remote_session = str(root.join("scripts", "server-session.ps1", resolve=True))
    sh.pwsh("nav n8n", *script_cmds, remote_session=remote_session)


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument(type=str, nargs="*", dest="commands")
    args = parser.parse_args()
    main(*args.commands)
