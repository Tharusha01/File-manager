import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { ChevronRight, Download, FileIcon, Film, Folder, Trash2 } from 'lucide-react';
import { api, type FileEntry } from '../api/client';
import { bytes } from '../lib/format';

const VIDEO_EXT = new Set(['mp4', 'webm', 'mkv', 'mov', 'm4v', 'avi', 'ogg']);
const AUDIO_EXT = new Set(['mp3', 'aac', 'ogg', 'wav', 'flac', 'm4a']);

function isMedia(name: string): boolean {
  const ext = name.split('.').pop()?.toLowerCase() ?? '';
  return VIDEO_EXT.has(ext) || AUDIO_EXT.has(ext);
}

export function FileBrowser({
  path,
  onPathChange,
}: {
  path: string;
  onPathChange: (p: string) => void;
}) {
  const navigate = useNavigate();
  const qc = useQueryClient();

  const { data, isLoading, error } = useQuery({
    queryKey: ['files', path],
    queryFn: () => api.listDir(path),
  });

  const remove = useMutation({
    mutationFn: (p: string) => api.deleteFile(p),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['files'] }),
  });

  const onClickEntry = (e: FileEntry) => {
    if (e.is_dir) onPathChange(e.path);
    else if (isMedia(e.name)) {
      navigate(`/watch?path=${encodeURIComponent(e.path)}`);
    } else {
      window.location.href = api.downloadUrl(e.path);
    }
  };

  const onDelete = (e: FileEntry) => {
    if (window.confirm(`Permanently delete "${e.name}"?`)) {
      remove.mutate(e.path);
    }
  };

  const segments = path ? path.split('/') : [];

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900">
      <div className="flex items-center gap-1 border-b border-slate-800 px-4 py-3 text-sm">
        <button
          onClick={() => onPathChange('')}
          className="rounded px-2 py-1 hover:bg-slate-800"
        >
          downloads
        </button>
        {segments.map((seg, i) => {
          const target = segments.slice(0, i + 1).join('/');
          return (
            <span key={target} className="flex items-center gap-1">
              <ChevronRight size={14} className="text-slate-600" />
              <button
                onClick={() => onPathChange(target)}
                className="rounded px-2 py-1 hover:bg-slate-800"
              >
                {seg}
              </button>
            </span>
          );
        })}
      </div>

      {isLoading && <div className="px-4 py-6 text-slate-400">Loading…</div>}
      {error && (
        <div className="px-4 py-6 text-rose-400">{(error as Error).message}</div>
      )}

      {data && data.entries.length === 0 && (
        <div className="px-4 py-10 text-center text-slate-500">
          This folder is empty.
        </div>
      )}

      {data && data.entries.length > 0 && (
        <ul className="divide-y divide-slate-800">
          {data.entries.map((entry) => (
            <li
              key={entry.path}
              className="flex items-center gap-3 px-4 py-3 hover:bg-slate-800/40"
            >
              <button
                onClick={() => onClickEntry(entry)}
                className="flex min-w-0 flex-1 items-center gap-3 text-left"
              >
                <span className="shrink-0 text-slate-400">
                  {entry.is_dir ? (
                    <Folder size={18} />
                  ) : isMedia(entry.name) ? (
                    <Film size={18} />
                  ) : (
                    <FileIcon size={18} />
                  )}
                </span>
                <span className="min-w-0 flex-1 truncate" title={entry.name}>
                  {entry.name}
                </span>
                <span className="shrink-0 text-xs text-slate-500">
                  {entry.is_dir ? '' : bytes(entry.size)}
                </span>
              </button>
              {!entry.is_dir && (
                <a
                  href={api.downloadUrl(entry.path)}
                  className="rounded-md p-2 text-slate-300 hover:bg-slate-800 hover:text-white"
                  title="Download"
                >
                  <Download size={16} />
                </a>
              )}
              <button
                onClick={() => onDelete(entry)}
                className="rounded-md p-2 text-rose-400 hover:bg-rose-500/10 hover:text-rose-300"
                title="Delete"
              >
                <Trash2 size={16} />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
