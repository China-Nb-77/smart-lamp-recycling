import { useEffect, useState } from 'react';
import { adminAPI } from '../../api/admin';
import { ErrorState } from '../../components/feedback/ErrorState';

export function AdminRecordsPage() {
  const [records, setRecords] = useState<Array<Record<string, unknown>>>([]);
  const [error, setError] = useState('');

  useEffect(() => {
    void adminAPI.getRecords()
      .then((payload) => setRecords(payload.list || []))
      .catch((requestError) => setError(requestError instanceof Error ? requestError.message : '加载记录失败'));
  }, []);

  if (error) {
    return <ErrorState title="记录加载失败" description={error} />;
  }

  return (
    <section className="admin-card">
      <div className="payment-card__header">
        <div>
          <strong>回收记录</strong>
          <p>查看问答与回收链路产生的记录</p>
        </div>
      </div>
      <div className="admin-list">
        {records.map((record) => (
          <article key={String(record.id)} className="admin-list__item">
            <strong>{String(record.traceId || record.id || '')}</strong>
            <p>{String(record.question || '')}</p>
            <span>{String(record.createdAt || '')}</span>
          </article>
        ))}
      </div>
    </section>
  );
}
