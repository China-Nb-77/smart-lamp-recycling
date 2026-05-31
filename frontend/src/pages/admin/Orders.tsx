import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { adminAPI } from '../../api/admin';
import { ErrorState } from '../../components/feedback/ErrorState';

export function AdminOrdersPage() {
  const [orders, setOrders] = useState<Array<Record<string, string>>>([]);
  const [error, setError] = useState('');

  useEffect(() => {
    void adminAPI.getOrders()
      .then((payload) => setOrders(payload.list || []))
      .catch((requestError) => setError(requestError instanceof Error ? requestError.message : '加载订单失败'));
  }, []);

  if (error) {
    return <ErrorState title="订单加载失败" description={error} />;
  }

  return (
    <section className="admin-card">
      <div className="payment-card__header">
        <div>
          <strong>订单管理</strong>
          <p>查看所有履约订单与当前状态</p>
        </div>
      </div>
      <div className="admin-table">
        <div className="admin-table__row admin-table__row--head">
          <span>订单号</span>
          <span>运单号</span>
          <span>状态</span>
          <span>创建时间</span>
        </div>
        {orders.map((order) => (
          <Link key={order.orderId} to={`/admin/orders/${encodeURIComponent(order.orderId)}`} className="admin-table__row">
            <span>{order.orderId}</span>
            <span>{order.waybillId}</span>
            <span>{order.status}</span>
            <span>{order.createdAt}</span>
          </Link>
        ))}
      </div>
    </section>
  );
}
