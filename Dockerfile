# syntax=docker/dockerfile:1.6

# ---- 1. Build React frontend ----
FROM node:20-alpine AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# ---- 2. Python runtime (Debian-based so apt's python3-libtorrent matches) ----
FROM debian:bookworm-slim AS runtime
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    DATA_DIR=/data \
    PORT=8000

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        python3 \
        python3-venv \
        python3-pip \
        python3-libtorrent \
        ca-certificates \
        tini \
    && rm -rf /var/lib/apt/lists/*

# venv inherits the apt-installed libtorrent via system-site-packages,
# but pip-installed FastAPI/etc. live inside the venv.
RUN python3 -m venv --system-site-packages /opt/venv
ENV PATH=/opt/venv/bin:$PATH

WORKDIR /app
COPY backend/requirements.txt ./
RUN pip install -r requirements.txt

COPY backend/app ./app
COPY --from=web /web/dist ./static

RUN mkdir -p /data

VOLUME ["/data"]
EXPOSE 8000

ENTRYPOINT ["tini", "--"]
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
