"""Security utilities: filename sanitisation and path-traversal prevention.

Authentication and authorisation are NOT implemented in Phase 1.
They are planned for a future phase.
"""

import re
import unicodedata
from pathlib import Path, PurePosixPath


_SAFE_FILENAME_RE = re.compile(r"[^\w\-.]")


def sanitize_filename(filename: str) -> str:
    """Return a filesystem-safe version of *filename*.

    - Normalises unicode to ASCII.
    - Strips path separators and traversal sequences.
    - Replaces unsafe characters with underscores.
    - Limits length to 200 characters.
    """
    # Normalise unicode
    filename = unicodedata.normalize("NFKD", filename)
    filename = filename.encode("ascii", "ignore").decode("ascii")

    # Strip directory components
    filename = Path(filename).name

    # Replace unsafe characters
    filename = _SAFE_FILENAME_RE.sub("_", filename)

    # Collapse multiple underscores/dots
    filename = re.sub(r"_+", "_", filename).strip("_.")

    return filename[:200] or "unnamed"


def safe_join(base: Path, *parts: str) -> Path:
    """Join *parts* onto *base*, raising ValueError on path traversal."""
    resolved_base = base.resolve()
    candidate = (base / Path(*parts)).resolve()
    if not str(candidate).startswith(str(resolved_base)):
        raise ValueError(f"Path traversal detected: {parts}")
    return candidate
