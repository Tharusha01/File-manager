import { useState } from 'react';
import { FileBrowser } from '../components/FileBrowser';

export function FilesPage() {
  const [path, setPath] = useState('');

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-4">
      <h1 className="text-2xl font-semibold">Files</h1>
      <FileBrowser path={path} onPathChange={setPath} />
    </div>
  );
}
