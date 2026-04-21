import { useEffect, useState } from 'react';
import { adminAPI } from '../../api/admin';
import { ErrorState } from '../../components/feedback/ErrorState';

export function AdminDashboardPage() {
  const [stats, setStats] = useState<{ orders: number; tickets: number; users: number; records: number } | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    void adminAPI.getStats()
      .then(setStats)
      .catch((requestError) => setError(requestError instanceof Error ? requestError.message : '加载统计失败'));
  }, []);

  if (error) {
    return <ErrorState title="仪表盘加载失败" description={error} />;
  }

  return (
    <section className="admin-grid">
      {[
        ['订单总数', stats?.orders ?? 0],
        ['工单总数', stats?.tickets ?? 0],
        ['用户总数', stats?.users ?? 0],
        ['记录总数', stats?.records ?? 0],
      ].map(([label, value]) => (
        <article key={String(label)} className="admin-card">
          <span className="admin-card__label">{label}</span>
          <strong>{value}</strong>
        </article>
      ))}
    </section>
  );
}
