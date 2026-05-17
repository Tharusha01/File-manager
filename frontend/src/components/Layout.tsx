import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom';
import { Download, Folder, LogOut } from 'lucide-react';
import { useAuth } from '../auth/AuthContext';

export function Layout() {
  const { logout, state } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const linkCls = ({ isActive }: { isActive: boolean }) =>
    [
      'flex items-center gap-2 px-3 py-2 rounded-md text-sm transition-colors',
      isActive
        ? 'bg-slate-800 text-white'
        : 'text-slate-300 hover:bg-slate-800/60 hover:text-white',
    ].join(' ');

  return (
    <div className="flex h-full flex-col">
      <header className="flex items-center justify-between border-b border-slate-800 bg-slate-900 px-6 py-3">
        <Link to="/torrents" className="text-lg font-semibold tracking-tight">
          File Manager
        </Link>
        <nav className="flex items-center gap-2">
          <NavLink to="/torrents" className={linkCls}>
            <Download size={16} /> Torrents
          </NavLink>
          <NavLink to="/files" className={linkCls}>
            <Folder size={16} /> Files
          </NavLink>
          <button
            onClick={handleLogout}
            className="ml-3 flex items-center gap-2 rounded-md px-3 py-2 text-sm text-slate-300 hover:bg-slate-800/60 hover:text-white"
          >
            <LogOut size={16} />
            {state.status === 'authed' ? state.username : 'Logout'}
          </button>
        </nav>
      </header>
      <main className="flex-1 overflow-auto px-6 py-6">
        <Outlet />
      </main>
    </div>
  );
}
