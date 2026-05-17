import { Link, useSearchParams } from 'react-router-dom';
import { ChevronLeft } from 'lucide-react';
import { VideoPlayer } from '../components/VideoPlayer';

export function WatchPage() {
  const [params] = useSearchParams();
  const path = params.get('path') ?? '';

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-4">
      <Link
        to="/files"
        className="inline-flex w-fit items-center gap-1 text-sm text-slate-400 hover:text-slate-200"
      >
        <ChevronLeft size={14} /> Back to files
      </Link>
      {path ? (
        <VideoPlayer path={path} />
      ) : (
        <div className="rounded-lg border border-slate-800 bg-slate-900 px-4 py-10 text-center text-slate-400">
          No file selected.
        </div>
      )}
    </div>
  );
}
