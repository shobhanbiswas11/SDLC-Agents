import zipfile
from pathlib import Path


def build_zip(files: dict[str, str], output_path: str):
    with zipfile.ZipFile(output_path, "w") as z:
        for path, content in files.items():
            z.writestr(path, content)