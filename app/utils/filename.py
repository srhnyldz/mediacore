import re
import unicodedata
from pathlib import Path


def sanitize_filename(filename: str) -> str:
    path_obj = Path(filename)
    normalized = unicodedata.normalize("NFKD", path_obj.stem)
    ascii_stem = normalized.encode("ascii", "ignore").decode("ascii")
    clean_stem = re.sub(r"[^A-Za-z0-9._-]+", "-", ascii_stem).strip("._-")
    clean_stem = clean_stem or "download"

    suffix = "".join(path_obj.suffixes)
    clean_suffix = re.sub(r"[^A-Za-z0-9.]+", "", suffix)

    return f"{clean_stem}{clean_suffix}"


def build_unique_path(target_path: Path) -> Path:
    if not target_path.exists():
        return target_path

    counter = 1
    while True:
        candidate = target_path.with_name(
            f"{target_path.stem}-{counter}{target_path.suffix}"
        )
        if not candidate.exists():
            return candidate
        counter += 1

