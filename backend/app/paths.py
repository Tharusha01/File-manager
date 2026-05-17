"""Sandboxed path resolution against settings.downloads_dir.

Every file route MUST go through resolve_safe(). Do not duplicate this logic.
"""

from pathlib import Path

from fastapi import HTTPException, status

from .config import settings


def resolve_safe(rel: str | None) -> Path:
    """Resolve `rel` (a user-supplied path, possibly empty) under downloads_dir.

    Rejects anything that escapes the root via .. or absolute paths.
    Returns an absolute, fully-resolved Path. Existence is NOT checked here
    (callers may want to create it).
    """
    root = settings.downloads_dir.resolve()
    candidate = (root / (rel or "")).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "path escapes data root")
    return candidate


def relpath(p: Path) -> str:
    """Render a resolved path as a forward-slash relative path under downloads_dir."""
    root = settings.downloads_dir.resolve()
    try:
        return p.resolve().relative_to(root).as_posix()
    except ValueError:
        return ""
