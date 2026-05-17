# File Manager

Self-hosted web app: paste a magnet link or `.torrent` file, the server downloads it, and you can browse, download, or stream the contents in your browser.

- Backend: Python (FastAPI + python-libtorrent)
- Frontend: React (Vite + TypeScript + Tailwind)
- Auth: single user (httpOnly cookie)
- Streaming: HTTP Range, direct play (mp4 / webm / mp3 / etc.)
- Deploy: one Docker container

## Quick start (Docker)

```bash
cp .env.example .env
# edit .env -- at minimum set JWT_SECRET and PASSWORD
docker compose up --build
```

App is at <http://localhost:8000>.

The `data/` directory is bind-mounted into the container at `/data`. SQLite DB and downloads live there.

## Local development (without Docker)

You need Python 3.11+ with `libtorrent` available, plus Node 20+.

```bash
# backend
cd backend
python -m venv .venv
source .venv/bin/activate         # on Windows: .venv\Scripts\activate
pip install -r requirements.txt
export DATA_DIR=$(pwd)/../data
export JWT_SECRET=dev-secret USERNAME=admin PASSWORD=admin
uvicorn app.main:app --reload --port 8000

# frontend (separate terminal)
cd frontend
npm install
npm run dev          # http://localhost:5173, proxies /api and /ws to :8000
```

> **Windows note:** installing python-libtorrent locally on Windows is awkward. Use Docker, or run the backend in WSL.

## Deploy to Railway

1. Push this repo to GitHub.
2. Create a new Railway project → "Deploy from repo" → pick this repo.
3. Add a **Volume** mounted at `/data`.
4. Set environment variables:
   - `JWT_SECRET` — a long random string
   - `USERNAME`, `PASSWORD` — your login
   - `DATA_DIR=/data`
5. Railway sets `PORT` automatically; the container respects it.

**Caveats** (important):
- Railway Volumes are size-capped (typically tens of GB). Don't expect a media library.
- Railway egress is metered — streaming a 4 GB movie twice ~ $1+ in bandwidth.
- libtorrent will work outbound-only on Railway (no inbound peer port). Downloads work; seeding is degraded.

For a real media setup, deploy the same image to a home server / NAS / cheap VPS.

## Endpoints

- `POST /api/auth/login` — body `{ username, password }`, sets cookie
- `POST /api/auth/logout`
- `GET /api/auth/me`
- `GET /api/torrents` — list
- `POST /api/torrents` — body `{ magnet }` or multipart `.torrent` upload
- `PATCH /api/torrents/{id}` — `{ action: "pause" | "resume" }`
- `DELETE /api/torrents/{id}?delete_files=true|false`
- `WS /ws/torrents` — live progress events
- `GET /api/files?path=...` — directory listing
- `GET /api/files/download?path=...` — download as attachment
- `GET /api/files/stream?path=...` — stream with HTTP Range
- `DELETE /api/files?path=...`
- `PATCH /api/files` — `{ path, new_path }`

## Out of scope

Transcoding, multi-user, search/RSS, TLS termination (handled by your reverse proxy or Railway).
