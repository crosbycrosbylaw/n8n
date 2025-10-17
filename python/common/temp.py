from rampy import root

TMP = root() / "service" / "tmp"

if not TMP.is_dir():
    TMP.mkdir(parents=True, exist_ok=True)
