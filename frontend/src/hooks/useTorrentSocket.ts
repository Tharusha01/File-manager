import { useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import type { Torrent } from '../api/client';

type Message =
  | { type: 'snapshot'; torrents: Torrent[] }
  | { type: 'progress'; torrent: Torrent }
  | { type: 'added'; torrent: Torrent }
  | { type: 'finished'; torrent: Torrent }
  | { type: 'metadata'; torrent: Torrent };

function wsUrl(): string {
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${proto}//${window.location.host}/ws/torrents`;
}

export function useTorrentSocket() {
  const qc = useQueryClient();

  useEffect(() => {
    let ws: WebSocket | null = null;
    let reconnectTimer: number | null = null;
    let cancelled = false;

    const connect = () => {
      ws = new WebSocket(wsUrl());

      ws.onmessage = (e) => {
        let msg: Message;
        try {
          msg = JSON.parse(e.data);
        } catch {
          return;
        }
        if (msg.type === 'snapshot') {
          qc.setQueryData<Torrent[]>(['torrents'], msg.torrents);
          return;
        }
        const updated = msg.torrent;
        qc.setQueryData<Torrent[]>(['torrents'], (prev) => {
          const list = prev ?? [];
          const idx = list.findIndex((t) => t.infohash === updated.infohash);
          if (idx === -1) return [...list, updated];
          const next = list.slice();
          next[idx] = { ...next[idx], ...updated };
          return next;
        });
      };

      ws.onclose = () => {
        if (!cancelled) {
          reconnectTimer = window.setTimeout(connect, 2000);
        }
      };
      ws.onerror = () => {
        ws?.close();
      };
    };

    connect();

    return () => {
      cancelled = true;
      if (reconnectTimer != null) window.clearTimeout(reconnectTimer);
      ws?.close();
    };
  }, [qc]);
}
