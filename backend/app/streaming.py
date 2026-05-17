"""HTTP Range request streaming for video/audio playback in the browser.

Returns 206 Partial Content for Range requests; otherwise 200 with the full body.
Always advertises Accept-Ranges: bytes so the <video> tag enables seek.
"""

from collections.abc import AsyncIterator
from mimetypes import guess_type
from pathlib import Path

import anyio
from fastapi import HTTPException, Request, status
from fastapi.responses import StreamingResponse

CHUNK = 1024 * 1024  # 1 MiB


def _parse_range(header: str, file_size: int) -> tuple[int, int] | None:
    """Parse `bytes=START-END`. Returns (start, end_inclusive) or None if malformed."""
    if not header.startswith("bytes="):
        return None
    spec = header[6:].split(",", 1)[0].strip()
    if "-" not in spec:
        return None
    start_s, end_s = spec.split("-", 1)
    try:
        if start_s == "":
            # suffix range: bytes=-N -> last N bytes
            length = int(end_s)
            if length <= 0:
                return None
            start = max(file_size - length, 0)
            end = file_size - 1
        else:
            start = int(start_s)
            end = int(end_s) if end_s else file_size - 1
    except ValueError:
        return None
    if start > end or start >= file_size:
        return None
    end = min(end, file_size - 1)
    return start, end


async def _file_iter(path: Path, start: int, end: int) -> AsyncIterator[bytes]:
    remaining = end - start + 1
    async with await anyio.open_file(path, "rb") as f:
        await f.seek(start)
        while remaining > 0:
            chunk = await f.read(min(CHUNK, remaining))
            if not chunk:
                break
            remaining -= len(chunk)
            yield chunk


def stream_file(path: Path, request: Request) -> StreamingResponse:
    if not path.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "file not found")

    file_size = path.stat().st_size
    media_type = guess_type(path.name)[0] or "application/octet-stream"
    range_header = request.headers.get("range")

    if range_header:
        rng = _parse_range(range_header, file_size)
        if rng is None:
            return StreamingResponse(
                iter(()),
                status_code=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE,
                headers={"Content-Range": f"bytes */{file_size}"},
            )
        start, end = rng
        headers = {
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(end - start + 1),
        }
        return StreamingResponse(
            _file_iter(path, start, end),
            status_code=status.HTTP_206_PARTIAL_CONTENT,
            media_type=media_type,
            headers=headers,
        )

    headers = {
        "Accept-Ranges": "bytes",
        "Content-Length": str(file_size),
    }
    return StreamingResponse(
        _file_iter(path, 0, file_size - 1),
        media_type=media_type,
        headers=headers,
    )
