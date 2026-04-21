import { Navigate } from 'react-router-dom';
import { getStoredUser, getUserToken } from '../auth/session';
import type { ReactNode } from 'react';

export function ProtectedRoute({ children }: { children: ReactNode }) {
  const token = getUserToken();
  const user = getStoredUser();
  if (!token || !user) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}
