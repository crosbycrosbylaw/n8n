from argparse import ArgumentParser

from rampy import root, sh


def main(*script_cmds: str) -> None:
    commands = ["cd ~/share/n8n", *script_cmds]
    sh.logs.enable()
    sh.pwsh(
        *commands,
        remote_session=str(root.join("scripts", "server-session.ps1", resolve=True)),
    )
    sh.logs.disable()


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument(type=str, nargs="*", dest="commands")
    args = parser.parse_args()
    main(*args.commands)
