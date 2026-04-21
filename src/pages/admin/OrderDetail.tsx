import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { adminAPI } from '../../api/admin';
import { ErrorState } from '../../components/feedback/ErrorState';

export function AdminOrderDetailPage() {
  const { id = '' } = useParams();
  const [detail, setDetail] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    void adminAPI.getOrderDetail(id)
      .then(setDetail)
      .catch((requestError) => setError(requestError instanceof Error ? requestError.message : '加载订单详情失败'));
  }, [id]);

  if (error) {
    return <ErrorState title="订单详情加载失败" description={error} />;
  }

  return (
    <section className="admin-card">
      <div className="payment-card__header">
        <div>
          <strong>订单详情</strong>
          <p>{id}</p>
        </div>
      </div>
      <pre className="admin-pre">{JSON.stringify(detail, null, 2)}</pre>
    </section>
  );
}
