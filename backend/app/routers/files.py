import re
import shutil
from pathlib import Path
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel

from ..auth import current_user
from ..models import User
from ..paths import relpath, resolve_safe
from ..streaming import stream_file

router = APIRouter(prefix="/api/files", tags=["files"])

SUBTITLE_EXTS = {".srt", ".vtt"}
_SRT_TIMESTAMP = re.compile(r"(\d{2}:\d{2}:\d{2}),(\d{3})")


def _srt_to_vtt(srt: str) -> str:
    body = _SRT_TIMESTAMP.sub(r"\1.\2", srt.lstrip("﻿"))
    return "WEBVTT\n\n" + body


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


class SubtitleEntry(BaseModel):
    name: str
    path: str
    label: str


@router.get("/subtitles", response_model=list[SubtitleEntry])
async def list_subtitles(
    _: Annotated[User, Depends(current_user)],
    path: str,
) -> list[SubtitleEntry]:
    video = resolve_safe(path)
    if not video.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "video not found")
    stem = video.stem.lower()
    out: list[SubtitleEntry] = []
    try:
        children = list(video.parent.iterdir())
    except OSError:
        return out
    for child in children:
        if not child.is_file() or child.suffix.lower() not in SUBTITLE_EXTS:
            continue
        child_stem = child.stem.lower()
        if child_stem == stem:
            label = child.suffix.lower().lstrip(".").upper()
        elif child_stem.startswith(stem + "."):
            label = child_stem[len(stem) + 1 :] or child.suffix.lower().lstrip(".")
        else:
            continue
        out.append(
            SubtitleEntry(name=child.name, path=relpath(child), label=label)
        )
    out.sort(key=lambda s: s.label.lower())
    return out


@router.post("/subtitles", response_model=SubtitleEntry, status_code=status.HTTP_201_CREATED)
async def upload_subtitle(
    _: Annotated[User, Depends(current_user)],
    path: str,
    file: Annotated[UploadFile, File()],
) -> SubtitleEntry:
    video = resolve_safe(path)
    if not video.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "video not found")
    upload_name = Path(file.filename or "").name
    ext = Path(upload_name).suffix.lower()
    if ext not in SUBTITLE_EXTS:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "subtitle must be .srt or .vtt",
        )
    upload_stem = Path(upload_name).stem
    if not upload_stem or upload_stem.lower() == video.stem.lower():
        target_name = f"{video.stem}{ext}"
    else:
        target_name = f"{video.stem}.{upload_stem}{ext}"
    target = video.parent / target_name
    # Re-resolve through the sandbox to enforce the data-root check.
    target = resolve_safe(relpath(target))
    raw = await file.read()
    if not raw:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "empty subtitle file")
    target.write_bytes(raw)
    stem = video.stem.lower()
    label_src = target.stem.lower()
    if label_src == stem:
        label = ext.lstrip(".").upper()
    elif label_src.startswith(stem + "."):
        label = label_src[len(stem) + 1 :]
    else:
        label = target.stem
    return SubtitleEntry(name=target.name, path=relpath(target), label=label)


@router.get("/subtitle")
async def get_subtitle(
    _: Annotated[User, Depends(current_user)],
    path: str,
) -> Response:
    target = resolve_safe(path)
    if not target.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "subtitle not found")
    ext = target.suffix.lower()
    if ext not in SUBTITLE_EXTS:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            "unsupported subtitle format",
        )
    text = target.read_text(encoding="utf-8", errors="replace")
    if ext == ".srt":
        text = _srt_to_vtt(text)
    return Response(content=text, media_type="text/vtt; charset=utf-8")


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
