import type { ReactNode } from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';

export function ProtectedRoute({ children }: { children: ReactNode }) {
  const { state } = useAuth();
  if (state.status === 'loading') {
    return (
      <div className="flex h-full items-center justify-center text-slate-400">
        Loading…
      </div>
    );
  }
  if (state.status === 'anon') {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}
