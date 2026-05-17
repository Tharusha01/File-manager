import { useRef, useState, type ChangeEvent } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, Upload } from 'lucide-react';
import { api } from '../api/client';

export function AddTorrentDialog() {
  const [open, setOpen] = useState(false);
  const [magnet, setMagnet] = useState('');
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const qc = useQueryClient();

  const addMagnet = useMutation({
    mutationFn: (m: string) => api.addMagnet(m),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['torrents'] });
      setMagnet('');
      setOpen(false);
    },
    onError: (e: Error) => setError(e.message),
  });

  const upload = useMutation({
    mutationFn: (file: File) => api.uploadTorrent(file),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['torrents'] });
      setOpen(false);
    },
    onError: (e: Error) => setError(e.message),
  });

  const onFile = (e: ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) upload.mutate(f);
  };

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="inline-flex items-center gap-2 rounded-md bg-emerald-500 px-3 py-2 text-sm font-medium text-slate-950 hover:bg-emerald-400"
      >
        <Plus size={16} /> Add torrent
      </button>
    );
  }

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900 p-4">
      <div className="mb-3 text-sm font-medium">Add torrent</div>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          setError(null);
          if (magnet.trim()) addMagnet.mutate(magnet.trim());
        }}
        className="flex flex-col gap-3"
      >
        <input
          type="text"
          autoFocus
          placeholder="magnet:?xt=urn:btih:…"
          value={magnet}
          onChange={(e) => setMagnet(e.target.value)}
          className="rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm placeholder-slate-500 focus:border-emerald-500 focus:outline-none"
        />
        <div className="flex flex-wrap gap-2">
          <button
            type="submit"
            disabled={!magnet.trim() || addMagnet.isPending}
            className="rounded-md bg-emerald-500 px-3 py-2 text-sm font-medium text-slate-950 hover:bg-emerald-400 disabled:opacity-50"
          >
            {addMagnet.isPending ? 'Adding…' : 'Add magnet'}
          </button>
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={upload.isPending}
            className="inline-flex items-center gap-2 rounded-md border border-slate-700 px-3 py-2 text-sm text-slate-200 hover:border-slate-500 disabled:opacity-50"
          >
            <Upload size={14} />
            {upload.isPending ? 'Uploading…' : 'Upload .torrent'}
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".torrent,application/x-bittorrent"
            className="hidden"
            onChange={onFile}
          />
          <button
            type="button"
            onClick={() => {
              setOpen(false);
              setError(null);
              setMagnet('');
            }}
            className="ml-auto rounded-md px-3 py-2 text-sm text-slate-400 hover:text-slate-200"
          >
            Cancel
          </button>
        </div>
        {error && <div className="text-sm text-rose-400">{error}</div>}
      </form>
    </div>
  );
}
