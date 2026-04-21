import { Navigate } from 'react-router-dom';
import { getAdminToken, getStoredAdmin } from '../auth/session';
import type { ReactNode } from 'react';

export function AdminProtectedRoute({ children }: { children: ReactNode }) {
  const token = getAdminToken();
  const admin = getStoredAdmin();
  if (!token || !admin) {
    return <Navigate to="/admin/login" replace />;
  }
  return <>{children}</>;
}
