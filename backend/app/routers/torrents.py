from typing import Annotated, Literal

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from pydantic import BaseModel

from ..auth import current_user, user_from_cookie_token
from ..config import settings
from ..models import User
from ..torrent_service import service
from ..ws_manager import ws_manager

router = APIRouter(prefix="/api/torrents", tags=["torrents"])


class AddMagnetRequest(BaseModel):
    magnet: str


class TorrentDTO(BaseModel):
    infohash: str
    name: str
    progress: float
    state: str
    download_rate: int
    upload_rate: int
    num_peers: int
    total_size: int
    downloaded: int
    paused: bool


class PatchRequest(BaseModel):
    action: Literal["pause", "resume"]


@router.get("", response_model=list[TorrentDTO])
async def list_torrents(_: Annotated[User, Depends(current_user)]) -> list[TorrentDTO]:
    return [TorrentDTO(**t.to_dict()) for t in service.list()]


@router.post("", response_model=TorrentDTO, status_code=status.HTTP_201_CREATED)
async def add_torrent(
    _: Annotated[User, Depends(current_user)],
    magnet: Annotated[str | None, Form()] = None,
    file: Annotated[UploadFile | None, File()] = None,
) -> TorrentDTO:
    if file is not None:
        raw = await file.read()
        if not raw:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "empty .torrent file")
        info = await service.add_torrent_file(raw)
    elif magnet:
        if not magnet.startswith("magnet:"):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "not a magnet URI")
        info = await service.add_magnet(magnet)
    else:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "provide a magnet URI or a .torrent file"
        )
    return TorrentDTO(**info.to_dict())


@router.post("/magnet", response_model=TorrentDTO, status_code=status.HTTP_201_CREATED)
async def add_magnet_json(
    body: AddMagnetRequest,
    _: Annotated[User, Depends(current_user)],
) -> TorrentDTO:
    if not body.magnet.startswith("magnet:"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "not a magnet URI")
    info = await service.add_magnet(body.magnet)
    return TorrentDTO(**info.to_dict())


@router.patch("/{infohash}", response_model=TorrentDTO)
async def patch_torrent(
    infohash: str,
    body: PatchRequest,
    _: Annotated[User, Depends(current_user)],
) -> TorrentDTO:
    if body.action == "pause":
        ok = await service.pause(infohash)
    else:
        ok = await service.resume(infohash)
    if not ok:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "torrent not found")
    info = service.get(infohash)
    if info is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "torrent not found")
    return TorrentDTO(**info.to_dict())


@router.delete("/{infohash}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_torrent(
    infohash: str,
    _: Annotated[User, Depends(current_user)],
    delete_files: bool = False,
) -> None:
    ok = await service.remove(infohash, delete_files=delete_files)
    if not ok:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "torrent not found")


# ----- WebSocket -----

ws_router = APIRouter()


@ws_router.websocket("/ws/torrents")
async def torrents_ws(ws: WebSocket) -> None:
    token = ws.cookies.get(settings.cookie_name)
    if not user_from_cookie_token(token):
        await ws.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await ws_manager.connect(ws)
    # Send a snapshot on connect so the UI can populate without an extra REST call.
    snapshot = [t.to_dict() for t in service.list()]
    try:
        await ws.send_json({"type": "snapshot", "torrents": snapshot})
        while True:
            # We don't expect inbound messages, but receive_text yields if the
            # client closes / pings. Discard the payload.
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await ws_manager.disconnect(ws)
