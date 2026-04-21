import { useEffect, useState } from 'react';
import { adminAPI } from '../../api/admin';
import { ErrorState } from '../../components/feedback/ErrorState';

export function AdminUsersPage() {
  const [users, setUsers] = useState<Array<Record<string, unknown>>>([]);
  const [error, setError] = useState('');

  async function load() {
    try {
      const payload = await adminAPI.getUsers();
      setUsers(payload.list || []);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : '加载用户失败');
    }
  }

  useEffect(() => {
    void load();
  }, []);

  if (error) {
    return <ErrorState title="用户加载失败" description={error} />;
  }

  return (
    <section className="admin-card">
      <div className="payment-card__header">
        <div>
          <strong>用户管理</strong>
          <p>启用或停用用户账号</p>
        </div>
      </div>
      <div className="admin-table">
        <div className="admin-table__row admin-table__row--head">
          <span>用户名</span>
          <span>昵称</span>
          <span>联系方式</span>
          <span>状态</span>
        </div>
        {users.map((user) => (
          <div key={String(user.id)} className="admin-table__row">
            <span>{String(user.username || '')}</span>
            <span>{String(user.displayName || '')}</span>
            <span>{String(user.phone || user.email || '')}</span>
            <span className="admin-table__actions">
              <button
                type="button"
                className="secondary-pill"
                onClick={async () => {
                  await adminAPI.updateUserStatus(Number(user.id), Number(user.status) === 1 ? 0 : 1);
                  await load();
                }}
              >
                {Number(user.status) === 1 ? '禁用' : '启用'}
              </button>
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}
