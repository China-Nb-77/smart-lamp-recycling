import { Link, useLocation } from 'react-router-dom';
import { LayoutDashboard, Package, ReceiptText, Shield, Users } from 'lucide-react';

const links = [
  { to: '/admin/dashboard', label: '仪表盘', icon: LayoutDashboard },
  { to: '/admin/orders', label: '订单管理', icon: Package },
  { to: '/admin/records', label: '回收记录', icon: ReceiptText },
  { to: '/admin/users', label: '用户管理', icon: Users },
];

export function AdminSidebar() {
  const location = useLocation();
  return (
    <aside className="admin-sidebar">
      <div className="admin-brand">
        <span className="admin-brand__icon">
          <Shield size={18} />
        </span>
        <div>
          <strong>管理后台</strong>
          <p>智能灯具回收系统</p>
        </div>
      </div>

      <nav className="admin-nav">
        {links.map((item) => {
          const Icon = item.icon;
          const active = location.pathname === item.to || location.pathname.startsWith(`${item.to}/`);
          return (
            <Link
              key={item.to}
              to={item.to}
              className={`admin-nav__item${active ? ' admin-nav__item--active' : ''}`}
            >
              <Icon size={18} />
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
