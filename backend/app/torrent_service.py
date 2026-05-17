"""Embedded libtorrent session.

Wraps a single ``lt.session``, runs an alert pump as an asyncio task, and
exposes a small async API for the routers.

Resume data is written to ``settings.resume_dir / <infohash>.fastresume``.
On startup we re-add every torrent from that directory so downloads survive
restarts. The DB ``TorrentRecord`` row is the canonical "this torrent exists"
fact; the resume file is "where libtorrent last left off".
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path

import libtorrent as lt
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .db import SessionLocal
from .models import TorrentRecord
from .ws_manager import ws_manager

logger = logging.getLogger(__name__)


@dataclass
class TorrentInfo:
    infohash: str
    name: str
    progress: float       # 0..1
    state: str
    download_rate: int    # bytes/sec
    upload_rate: int      # bytes/sec
    num_peers: int
    total_size: int
    downloaded: int
    paused: bool

    def to_dict(self) -> dict:
        return self.__dict__.copy()


def _state_str(_handle: "lt.torrent_handle", status: "lt.torrent_status") -> str:
    if status.paused:
        return "paused"
    s = status.state
    # libtorrent 2.x exposes states as a python enum-ish; str() usually yields
    # something like "downloading". Guard against unexpected reprs.
    name = getattr(s, "name", None)
    if isinstance(name, str):
        return name
    return str(s).rsplit(".", 1)[-1] or "unknown"


def _info_from_status(status: "lt.torrent_status") -> TorrentInfo:
    handle = status.handle
    info_hash = str(handle.info_hash())
    name = status.name or info_hash[:8]
    return TorrentInfo(
        infohash=info_hash,
        name=name,
        progress=float(status.progress),
        state=_state_str(handle, status),
        download_rate=int(status.download_rate),
        upload_rate=int(status.upload_rate),
        num_peers=int(status.num_peers),
        total_size=int(status.total_wanted) if status.total_wanted else 0,
        downloaded=int(status.total_wanted_done),
        paused=bool(status.paused),
    )


class TorrentService:
    def __init__(self) -> None:
        self._session: lt.session | None = None
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()
        self._handles: dict[str, lt.torrent_handle] = {}

    # ------------------------------------------------------------------ lifecycle

    async def start(self) -> None:
        if self._session is not None:
            return
        ses = lt.session(
            {
                "listen_interfaces": settings.listen_interfaces,
                # 0xffffffff = all alert categories. Numeric form is portable
                # across libtorrent versions; the named constants moved around.
                "alert_mask": 0xFFFFFFFF,
                "enable_dht": True,
                "enable_lsd": True,
                "enable_upnp": True,
                "enable_natpmp": True,
            }
        )
        self._session = ses
        await self._restore_from_disk()
        self._task = asyncio.create_task(self._alert_loop())

    async def stop(self) -> None:
        self._stop.set()
        if self._task:
            try:
                await asyncio.wait_for(self._task, timeout=5)
            except asyncio.TimeoutError:
                self._task.cancel()
        if self._session is not None:
            for h in self._session.get_torrents():
                try:
                    h.save_resume_data(lt.torrent_handle.save_info_dict)
                except Exception:
                    pass
            # Drain a couple of alerts so resume data gets persisted.
            for _ in range(20):
                alerts = self._session.pop_alerts()
                self._handle_resume_alerts(alerts)
                await asyncio.sleep(0.1)
        self._session = None

    # ------------------------------------------------------------------ public API

    async def add_magnet(self, magnet: str) -> TorrentInfo:
        ses = self._require()
        params = lt.parse_magnet_uri(magnet)
        params.save_path = str(settings.downloads_dir)
        handle = ses.add_torrent(params)
        return await self._register(handle, magnet=magnet)

    async def add_torrent_file(self, raw: bytes) -> TorrentInfo:
        ses = self._require()
        ti = lt.torrent_info(raw)
        params = lt.add_torrent_params()
        params.ti = ti
        params.save_path = str(settings.downloads_dir)
        handle = ses.add_torrent(params)
        return await self._register(handle, magnet=None)

    def list(self) -> list[TorrentInfo]:
        if self._session is None:
            return []
        return [_info_from_status(h.status()) for h in self._session.get_torrents()]

    def get(self, infohash: str) -> TorrentInfo | None:
        h = self._handles.get(infohash)
        if h is None:
            return None
        return _info_from_status(h.status())

    async def pause(self, infohash: str) -> bool:
        h = self._handles.get(infohash)
        if h is None:
            return False
        h.pause()
        return True

    async def resume(self, infohash: str) -> bool:
        h = self._handles.get(infohash)
        if h is None:
            return False
        h.resume()
        return True

    async def remove(self, infohash: str, delete_files: bool) -> bool:
        ses = self._require()
        h = self._handles.pop(infohash, None)
        if h is None:
            return False
        # `delete_files` constant moved between namespaces across libtorrent
        # versions; fall back to its numeric value (1) if neither is present.
        delete_files_flag = (
            getattr(lt.session, "delete_files", None)
            or getattr(lt, "delete_files", None)
            or 1
        )
        flags = delete_files_flag if delete_files else 0
        ses.remove_torrent(h, flags)

        async with SessionLocal() as db:
            await db.execute(
                delete(TorrentRecord).where(TorrentRecord.infohash == infohash)
            )
            await db.commit()

        resume_file = settings.resume_dir / f"{infohash}.fastresume"
        if resume_file.exists():
            try:
                resume_file.unlink()
            except OSError:
                pass
        return True

    # ------------------------------------------------------------------ internals

    def _require(self) -> lt.session:
        if self._session is None:
            raise RuntimeError("torrent service not started")
        return self._session

    async def _register(
        self, handle: lt.torrent_handle, *, magnet: str | None
    ) -> TorrentInfo:
        infohash = str(handle.info_hash())
        self._handles[infohash] = handle
        info = _info_from_status(handle.status())

        async with SessionLocal() as db:
            existing = await db.execute(
                select(TorrentRecord).where(TorrentRecord.infohash == infohash)
            )
            if existing.scalar_one_or_none() is None:
                db.add(
                    TorrentRecord(
                        infohash=infohash,
                        name=info.name,
                        magnet=magnet,
                    )
                )
                await db.commit()

        await ws_manager.broadcast({"type": "added", "torrent": info.to_dict()})
        return info

    async def _restore_from_disk(self) -> None:
        ses = self._require()
        async with SessionLocal() as db:
            result = await db.execute(select(TorrentRecord))
            records = list(result.scalars().all())

        for rec in records:
            resume_path = settings.resume_dir / f"{rec.infohash}.fastresume"
            try:
                if resume_path.exists():
                    raw = resume_path.read_bytes()
                    params = lt.read_resume_data(raw)
                    params.save_path = str(settings.downloads_dir)
                    handle = ses.add_torrent(params)
                elif rec.magnet:
                    params = lt.parse_magnet_uri(rec.magnet)
                    params.save_path = str(settings.downloads_dir)
                    handle = ses.add_torrent(params)
                else:
                    logger.warning(
                        "Cannot restore torrent %s: no resume data and no magnet",
                        rec.infohash,
                    )
                    continue
                self._handles[rec.infohash] = handle
            except Exception:
                logger.exception("Failed to restore torrent %s", rec.infohash)

    def _handle_resume_alerts(self, alerts: list) -> None:
        for a in alerts:
            t = type(a).__name__
            if t == "save_resume_data_alert":
                try:
                    infohash = str(a.handle.info_hash())
                    raw = lt.write_resume_data_buf(a.params)
                    target = settings.resume_dir / f"{infohash}.fastresume"
                    target.write_bytes(raw)
                except Exception:
                    logger.exception("Failed to persist resume data")

    async def _alert_loop(self) -> None:
        ses = self._require()
        last_resume_save = 0.0
        loop = asyncio.get_running_loop()

        while not self._stop.is_set():
            try:
                ses.post_torrent_updates()
                alerts = ses.pop_alerts()

                for a in alerts:
                    t = type(a).__name__
                    if t == "state_update_alert":
                        for st in a.status:
                            info = _info_from_status(st)
                            await ws_manager.broadcast(
                                {"type": "progress", "torrent": info.to_dict()}
                            )
                    elif t == "torrent_finished_alert":
                        try:
                            info = _info_from_status(a.handle.status())
                            await ws_manager.broadcast(
                                {"type": "finished", "torrent": info.to_dict()}
                            )
                        except Exception:
                            pass
                    elif t == "save_resume_data_alert":
                        self._handle_resume_alerts([a])
                    elif t == "metadata_received_alert":
                        try:
                            info = _info_from_status(a.handle.status())
                            await ws_manager.broadcast(
                                {"type": "metadata", "torrent": info.to_dict()}
                            )
                        except Exception:
                            pass

                # periodically ask all torrents to save resume data
                now = loop.time()
                if now - last_resume_save > 60:
                    last_resume_save = now
                    for h in ses.get_torrents():
                        try:
                            h.save_resume_data(lt.torrent_handle.save_info_dict)
                        except Exception:
                            pass

                try:
                    await asyncio.wait_for(self._stop.wait(), timeout=1.0)
                except asyncio.TimeoutError:
                    pass
            except Exception:
                logger.exception("alert loop error")
                await asyncio.sleep(1)


service = TorrentService()
