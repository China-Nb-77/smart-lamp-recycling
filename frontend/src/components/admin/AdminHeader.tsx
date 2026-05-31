import { LogOut } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { clearAdminSession, getStoredAdmin } from '../../auth/session';

export function AdminHeader() {
  const navigate = useNavigate();
  const admin = getStoredAdmin();

  return (
    <header className="admin-header">
      <div>
        <strong>{admin?.realName || admin?.displayName || admin?.username || '管理员'}</strong>
        <p>{admin?.role || 'admin'}</p>
      </div>
      <button
        type="button"
        className="secondary-pill"
        onClick={() => {
          clearAdminSession();
          navigate('/admin/login');
        }}
      >
        <LogOut size={16} />
        退出
      </button>
    </header>
  );
}
