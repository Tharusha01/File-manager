import { useState } from 'react';
import { api } from '../api/client';

export function VideoPlayer({ path }: { path: string }) {
  const [error, setError] = useState<string | null>(null);
  const filename = path.split('/').pop() ?? path;
  const isH265 = /\.(hevc|x265|h265)$/i.test(filename) || /(hevc|x265|h265)/i.test(filename);

  return (
    <div className="flex flex-col gap-3">
      <div className="overflow-hidden rounded-lg border border-slate-800 bg-black">
        <video
          src={api.streamUrl(path)}
          controls
          autoPlay
          preload="metadata"
          className="aspect-video w-full bg-black"
          onError={() =>
            setError(
              isH265
                ? "This video uses H.265/HEVC codec which your browser doesn't support. Try downloading the file and playing it with VLC or another player that supports HEVC.",
                : "Couldn't play this file. The browser likely doesn't support its codec " +
                    '(common with .mkv / h.265). Direct play only — transcoding is not enabled.',
            )
          }
        />
      </div>
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0 truncate text-sm text-slate-300" title={filename}>
          {filename}
        </div>
        <a
          href={api.downloadUrl(path)}
          className="rounded-md border border-slate-700 px-3 py-1.5 text-sm text-slate-200 hover:border-slate-500"
        >
          Download
        </a>
      </div>
      {error && (
        <div className="rounded-md border border-rose-500/30 bg-rose-500/10 p-3 text-sm text-rose-200">
          {error}
        </div>
      )}
    </div>
  );
}
