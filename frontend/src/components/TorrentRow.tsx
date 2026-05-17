import { Pause, Play, Trash2 } from 'lucide-react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { api, type Torrent } from '../api/client';
import { bytes, rate } from '../lib/format';

export function TorrentRow({ torrent }: { torrent: Torrent }) {
  const qc = useQueryClient();

  const toggle = useMutation({
    mutationFn: () =>
      api.patchTorrent(torrent.infohash, torrent.paused ? 'resume' : 'pause'),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['torrents'] }),
  });

  const remove = useMutation({
    mutationFn: (deleteFiles: boolean) => api.deleteTorrent(torrent.infohash, deleteFiles),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['torrents'] }),
  });

  const onDelete = () => {
    const deleteFiles = window.confirm(
      `Remove "${torrent.name}". Also delete the downloaded files from disk?\n\n` +
        `OK = delete files too.\nCancel = keep files (just remove from list).`,
    );
    // confirm() can't return a tri-state; use a second prompt for "abort entirely"
    if (window.confirm(deleteFiles ? 'Confirm: delete files too?' : 'Confirm: remove from list (keep files)?')) {
      remove.mutate(deleteFiles);
    }
  };

  const pct = Math.round(torrent.progress * 100);

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900 p-4">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <div className="truncate font-medium" title={torrent.name}>
            {torrent.name}
          </div>
          <div className="mt-1 text-xs text-slate-400">
            {torrent.state} · {pct}% · {bytes(torrent.downloaded)} of {bytes(torrent.total_size)}
            {' · '}
            ↓ {rate(torrent.download_rate)} · ↑ {rate(torrent.upload_rate)} · {torrent.num_peers} peers
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-1">
          <button
            onClick={() => toggle.mutate()}
            disabled={toggle.isPending}
            className="rounded-md p-2 text-slate-300 hover:bg-slate-800 hover:text-white disabled:opacity-50"
            title={torrent.paused ? 'Resume' : 'Pause'}
          >
            {torrent.paused ? <Play size={16} /> : <Pause size={16} />}
          </button>
          <button
            onClick={onDelete}
            disabled={remove.isPending}
            className="rounded-md p-2 text-rose-400 hover:bg-rose-500/10 hover:text-rose-300 disabled:opacity-50"
            title="Remove"
          >
            <Trash2 size={16} />
          </button>
        </div>
      </div>
      <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-slate-800">
        <div
          className={`h-full transition-all ${
            torrent.paused ? 'bg-slate-500' : 'bg-emerald-500'
          }`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
