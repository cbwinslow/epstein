"""Utility helpers for the ingestion pipeline tests and scripts.

Provides small, deterministic helpers used by `scripts/ingestion_pipeline` and its tests:
- generate_file_hash
- get_file_metadata
- detect_file_type
- safe_filename

These are intentionally simple, pure-Python helpers to make tests deterministic and fast.
"""

import hashlib
import mimetypes
import re
from pathlib import Path


def generate_file_hash(file_path: str) -> str:
    """Return the SHA-256 hex digest of the file contents."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()


def get_file_metadata(file_path: str) -> dict[str, object]:
    """Return basic file metadata: name, size (bytes), extension, mime_type."""
    p = Path(file_path)
    name = p.name
    size = p.stat().st_size
    extension = p.suffix.lstrip(".")
    mime_type, _ = mimetypes.guess_type(file_path)
    if mime_type is None:
        mime_type = "application/octet-stream"

    return {"name": name, "size": size, "extension": extension, "mime_type": mime_type}


def detect_file_type(file_path: str) -> str:
    """Detect a simple file type category based on extension."""
    ext = Path(file_path).suffix.lower()
    if ext == ".pdf":
        return "pdf"
    if ext in [".jpg", ".jpeg", ".png", ".tiff", ".bmp"]:
        return "image"
    if ext in [".txt", ".html", ".htm"]:
        return "text"
    return "unknown"


def safe_filename(name: str) -> str:
    """Return a filesystem-safe filename. Keeps an extension if present."""
    name = name.strip()
    # Split extension
    if "." in name:
        base, ext = name.rsplit(".", 1)
        ext = ext.lower()
    else:
        base, ext = name, ""

    # Replace any character that is not alnum, underscore, hyphen, or dot with underscore
    safe_base = re.sub(r"[^A-Za-z0-9._-]+", "_", base)
    # Collapse multiple underscores
    safe_base = re.sub(r"_+", "_", safe_base)
    safe_base = safe_base.strip("_")

    if ext:
        return f"{safe_base}.{ext}"
    return safe_base
