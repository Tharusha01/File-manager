import { useCallback, useEffect, useRef, useState, type ChangeEvent } from 'react';
import { api, type SubtitleEntry } from '../api/client';

export function VideoPlayer({ path }: { path: string }) {
  const [error, setError] = useState<string | null>(null);
  const [subs, setSubs] = useState<SubtitleEntry[]>([]);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const filename = path.split('/').pop() ?? path;
  const isH265 = /\.(hevc|x265|h265)$/i.test(filename) || /(hevc|x265|h265)/i.test(filename);

  const loadSubs = useCallback(async () => {
    try {
      const list = await api.listSubtitles(path);
      setSubs(list);
    } catch {
      setSubs([]);
    }
  }, [path]);

  useEffect(() => {
    loadSubs();
  }, [loadSubs]);

  const onUpload = async (e: ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (!f) return;
    setUploading(true);
    setError(null);
    try {
      await api.uploadSubtitle(path, f);
      await loadSubs();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to upload subtitle');
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  // Re-mount the <video> when the subtitle set changes so the browser picks
  // up newly-added <track> elements (it ignores tracks added after load).
  const videoKey = `${path}|${subs.map((s) => s.path).join(',')}`;

  return (
    <div className="flex flex-col gap-3">
      <div className="overflow-hidden rounded-lg border border-slate-800 bg-black">
        <video
          key={videoKey}
          src={api.streamUrl(path)}
          controls
          autoPlay
          preload="metadata"
          className="aspect-video w-full bg-black"
          onError={() =>
            setError(
              isH265
                ? "This video uses H.265/HEVC codec which your browser doesn't support. Try downloading the file and playing it with VLC or another player that supports HEVC."
                : "Couldn't play this file. The browser likely doesn't support its codec " +
                    '(common with .mkv / h.265). Direct play only — transcoding is not enabled.'
            )
          }
        >
          {subs.map((s, i) => (
            <track
              key={s.path}
              kind="subtitles"
              label={s.label}
              src={api.subtitleUrl(s.path)}
              default={i === 0}
            />
          ))}
        </video>
      </div>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0 flex-1 truncate text-sm text-slate-300" title={filename}>
          {filename}
        </div>
        <div className="flex items-center gap-2">
          <label
            className={`cursor-pointer rounded-md border border-slate-700 px-3 py-1.5 text-sm text-slate-200 hover:border-slate-500 ${
              uploading ? 'opacity-60' : ''
            }`}
          >
            {uploading ? 'Uploading…' : 'Add subtitle'}
            <input
              ref={fileInputRef}
              type="file"
              accept=".srt,.vtt"
              className="hidden"
              onChange={onUpload}
              disabled={uploading}
            />
          </label>
          <a
            href={api.downloadUrl(path)}
            className="rounded-md border border-slate-700 px-3 py-1.5 text-sm text-slate-200 hover:border-slate-500"
          >
            Download
          </a>
        </div>
      </div>
      {subs.length > 0 && (
        <div className="text-xs text-slate-500">
          Subtitles loaded: {subs.map((s) => s.label).join(', ')}
        </div>
      )}
      {error && (
        <div className="rounded-md border border-rose-500/30 bg-rose-500/10 p-3 text-sm text-rose-200">
          {error}
        </div>
      )}
    </div>
  );
}
