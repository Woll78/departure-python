import fnmatch
import pathlib

ROOT = pathlib.Path(__file__).parent.parent


def manifest_includes():
    lines = (ROOT / "MANIFEST.in").read_text(encoding="utf-8").splitlines()
    return [line.split()[1] for line in lines if line.startswith("include ")]


def test_every_package_data_file_is_in_manifest():
    # data files are loaded at import time, and the CLI imports every
    # provider, so a single missing file breaks the installed `departure`
    data_files = [
        path.relative_to(ROOT).as_posix()
        for path in (ROOT / "departure").rglob("*")
        if path.is_file()
        and path.suffix not in (".py", ".pyc")
        and "__pycache__" not in path.parts
    ]
    includes = manifest_includes()

    missing = [
        data_file
        for data_file in data_files
        if not any(fnmatch.fnmatch(data_file, pattern) for pattern in includes)
    ]

    assert data_files
    assert missing == []
