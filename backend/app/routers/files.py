import shutil
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse
from pydantic import BaseModel

from ..auth import current_user
from ..models import User
from ..paths import relpath, resolve_safe
from ..streaming import stream_file

router = APIRouter(prefix="/api/files", tags=["files"])


class FileEntry(BaseModel):
    name: str
    path: str          # forward-slash, relative to downloads root
    is_dir: bool
    size: int
    mtime: float


class ListResponse(BaseModel):
    path: str          # the directory we're listing, relative
    entries: list[FileEntry]


class RenameRequest(BaseModel):
    path: str
    new_path: str


@router.get("", response_model=ListResponse)
async def list_dir(
    _: Annotated[User, Depends(current_user)],
    path: str = "",
) -> ListResponse:
    target = resolve_safe(path)
    if not target.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not found")
    if not target.is_dir():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "not a directory")

    entries: list[FileEntry] = []
    for child in sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
        try:
            stat = child.stat()
        except OSError:
            continue
        entries.append(
            FileEntry(
                name=child.name,
                path=relpath(child),
                is_dir=child.is_dir(),
                size=stat.st_size if child.is_file() else 0,
                mtime=stat.st_mtime,
            )
        )
    return ListResponse(path=relpath(target), entries=entries)


@router.get("/download")
async def download(
    _: Annotated[User, Depends(current_user)],
    path: str,
) -> FileResponse:
    target = resolve_safe(path)
    if not target.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "file not found")
    return FileResponse(target, filename=target.name)


@router.get("/stream")
async def stream(
    request: Request,
    _: Annotated[User, Depends(current_user)],
    path: str,
):
    target = resolve_safe(path)
    return stream_file(target, request)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def delete_path(
    _: Annotated[User, Depends(current_user)],
    path: str,
) -> None:
    target = resolve_safe(path)
    if not target.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not found")
    if target == resolve_safe(""):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "cannot delete root")
    if target.is_dir():
        shutil.rmtree(target)
    else:
        target.unlink()


@router.patch("", status_code=status.HTTP_204_NO_CONTENT)
async def rename_path(
    body: RenameRequest,
    _: Annotated[User, Depends(current_user)],
) -> None:
    src = resolve_safe(body.path)
    dst = resolve_safe(body.new_path)
    if not src.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "source not found")
    if dst.exists():
        raise HTTPException(status.HTTP_409_CONFLICT, "destination already exists")
    dst.parent.mkdir(parents=True, exist_ok=True)
    src.rename(dst)
