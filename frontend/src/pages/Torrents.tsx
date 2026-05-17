import { useQuery } from '@tanstack/react-query';
import { api, type Torrent } from '../api/client';
import { AddTorrentDialog } from '../components/AddTorrentDialog';
import { TorrentRow } from '../components/TorrentRow';
import { useTorrentSocket } from '../hooks/useTorrentSocket';

export function TorrentsPage() {
  useTorrentSocket();

  const { data, isLoading, error } = useQuery<Torrent[]>({
    queryKey: ['torrents'],
    queryFn: () => api.listTorrents(),
  });

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Torrents</h1>
        <AddTorrentDialog />
      </div>

      {isLoading && <div className="text-slate-400">Loading…</div>}
      {error && <div className="text-rose-400">{(error as Error).message}</div>}

      {data && data.length === 0 && (
        <div className="rounded-lg border border-dashed border-slate-700 px-4 py-12 text-center text-slate-500">
          No torrents yet. Paste a magnet link to get started.
        </div>
      )}

      {data && data.length > 0 && (
        <div className="flex flex-col gap-3">
          {data.map((t) => (
            <TorrentRow key={t.infohash} torrent={t} />
          ))}
        </div>
      )}
    </div>
  );
}
