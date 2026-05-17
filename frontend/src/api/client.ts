export type Torrent = {
  infohash: string;
  name: string;
  progress: number;
  state: string;
  download_rate: number;
  upload_rate: number;
  num_peers: number;
  total_size: number;
  downloaded: number;
  paused: boolean;
};

export type FileEntry = {
  name: string;
  path: string;
  is_dir: boolean;
  size: number;
  mtime: number;
};

export type ListResponse = {
  path: string;
  entries: FileEntry[];
};

async function request<T>(input: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(input, {
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...(init.headers ?? {}),
    },
    ...init,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      // ignore
    }
    const err = new Error(detail) as Error & { status: number };
    err.status = res.status;
    throw err;
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  // auth
  me: () => request<{ username: string }>('/api/auth/me'),
  login: (username: string, password: string) =>
    request<{ username: string }>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    }),
  logout: () => request<{ ok: boolean }>('/api/auth/logout', { method: 'POST' }),

  // torrents
  listTorrents: () => request<Torrent[]>('/api/torrents'),
  addMagnet: (magnet: string) =>
    request<Torrent>('/api/torrents/magnet', {
      method: 'POST',
      body: JSON.stringify({ magnet }),
    }),
  uploadTorrent: async (file: File): Promise<Torrent> => {
    const fd = new FormData();
    fd.append('file', file);
    const res = await fetch('/api/torrents', {
      method: 'POST',
      credentials: 'include',
      body: fd,
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail ?? res.statusText);
    }
    return res.json();
  },
  patchTorrent: (infohash: string, action: 'pause' | 'resume') =>
    request<Torrent>(`/api/torrents/${encodeURIComponent(infohash)}`, {
      method: 'PATCH',
      body: JSON.stringify({ action }),
    }),
  deleteTorrent: (infohash: string, deleteFiles: boolean) =>
    request<void>(
      `/api/torrents/${encodeURIComponent(infohash)}?delete_files=${deleteFiles}`,
      { method: 'DELETE' },
    ),

  // files
  listDir: (path: string) =>
    request<ListResponse>(`/api/files?path=${encodeURIComponent(path)}`),
  deleteFile: (path: string) =>
    request<void>(`/api/files?path=${encodeURIComponent(path)}`, {
      method: 'DELETE',
    }),
  downloadUrl: (path: string) => `/api/files/download?path=${encodeURIComponent(path)}`,
  streamUrl: (path: string) => `/api/files/stream?path=${encodeURIComponent(path)}`,

  // subtitles
  listSubtitles: (videoPath: string) =>
    request<SubtitleEntry[]>(
      `/api/files/subtitles?path=${encodeURIComponent(videoPath)}`,
    ),
  uploadSubtitle: async (videoPath: string, file: File): Promise<SubtitleEntry> => {
    const fd = new FormData();
    fd.append('file', file);
    const res = await fetch(
      `/api/files/subtitles?path=${encodeURIComponent(videoPath)}`,
      { method: 'POST', credentials: 'include', body: fd },
    );
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail ?? res.statusText);
    }
    return res.json();
  },
  subtitleUrl: (path: string) =>
    `/api/files/subtitle?path=${encodeURIComponent(path)}`,
};

export type SubtitleEntry = {
  name: string;
  path: string;
  label: string;
};
