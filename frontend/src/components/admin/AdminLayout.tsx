import { Outlet } from 'react-router-dom';
import { AdminSidebar } from './AdminSidebar';
import { AdminHeader } from './AdminHeader';

export function AdminLayout() {
  return (
    <div className="admin-shell">
      <AdminSidebar />
      <main className="admin-main">
        <AdminHeader />
        <div className="admin-content">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
