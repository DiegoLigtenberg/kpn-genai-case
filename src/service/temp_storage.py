import uuid
from pathlib import Path


def invoice_temp_dir() -> Path:
    return Path.cwd() / ".tmp-invoice-images"


def content_hash_dir() -> Path:
    """Holds hashes of metadata that has already been processed."""
    return Path.cwd() / ".tmp-content-hash"


def ensure_invoice_temp_dir() -> Path:
    d = invoice_temp_dir()
    d.mkdir(parents=True, exist_ok=True)
    return d


def clear_invoice_temp_dir() -> None:
    d = invoice_temp_dir()
    if not d.is_dir():
        return
    for f in d.iterdir():
        if f.is_file():
            try:
                f.unlink()
            except OSError:
                pass


def ensure_content_hash_dir() -> Path:
    d = content_hash_dir()
    d.mkdir(parents=True, exist_ok=True)
    return d


def clear_content_hash_dir() -> None:
    d = content_hash_dir()
    if not d.is_dir():
        return
    for f in d.iterdir():
        if f.is_file():
            try:
                f.unlink()
            except OSError:
                pass


def append_fingerprint(fp: str) -> None:
    """Append the hash as a line to seen.txt."""
    path = ensure_content_hash_dir() / "seen.txt"
    with path.open("a", encoding="utf-8") as f:
        f.write(fp + "\n")


def write_temp_png(data: bytes) -> str:
    """Write PNG bytes to a temp file."""
    d = ensure_invoice_temp_dir()
    path = d / f"{uuid.uuid4().hex}.png"
    path.write_bytes(data)
    return str(path.resolve())
