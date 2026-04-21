import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { PaymentStatus } from '../../components/PaymentStatus/PaymentStatus';
import { LoadingState } from '../../components/feedback/LoadingState';
import { paymentApi } from '../../services/paymentApi';
import type { PaymentOrderView } from '../../modules/payment/types';
import { formatFen } from '../../modules/payment/utils';

export function PaymentSuccessPage() {
  const { orderId = '' } = useParams();
  const [order, setOrder] = useState<PaymentOrderView | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let disposed = false;

    const run = async () => {
      try {
        const result = await paymentApi.getPaymentStatus(orderId, true);
        if (!disposed) {
          setOrder(result);
          setLoading(false);
        }
      } catch {
        if (!disposed) {
          setLoading(false);
        }
      }
    };

    void run();
    const timer = window.setInterval(run, 3000);
    return () => {
      disposed = true;
      window.clearInterval(timer);
    };
  }, [orderId]);

  if (loading) {
    return (
      <main className="payment-page payment-page--center">
        <LoadingState label="正在确认支付结果..." />
      </main>
    );
  }

  const isPaid = order?.payment_status === 'PAID';

  return (
    <main className="payment-page">
      <header className="payment-page__header">
        <Link className="icon-button" to={`/payment/orders/${encodeURIComponent(orderId)}`}>
          <ArrowLeft size={20} />
        </Link>
        <strong>支付结果</strong>
        <span />
      </header>

      <PaymentStatus
        kind={isPaid ? 'success' : 'processing'}
        title={isPaid ? '支付成功' : '正在同步状态'}
        description={
          isPaid
            ? '支付已确认，下一步可以查看电子货单和物流地图。'
            : '页面已回到支付结果页，但本地订单状态还在同步。'
        }
        detail={
          order ? `${order.order_id} | ${formatFen(order.payable_total, order.amount_currency)}` : orderId
        }
      />

      {order ? (
        <section className="payment-card">
          <div className="payment-meta-grid">
            <div>
              <span>支付状态</span>
              <strong>{order.payment_status}</strong>
            </div>
            <div>
              <span>支付流水</span>
              <strong>{order.transaction_id || '--'}</strong>
            </div>
            <div>
              <span>支付时间</span>
              <strong>{order.paid_at || '--'}</strong>
            </div>
            <div>
              <span>运单号</span>
              <strong>{order.waybill_id || '--'}</strong>
            </div>
          </div>
        </section>
      ) : null}

      <div className="payment-action-row">
        <Link
          className="secondary-button payment-action"
          to={`/payment/orders/${encodeURIComponent(orderId)}`}
        >
          返回订单
        </Link>
        {order?.qr_token ? (
          <Link
            className="secondary-button payment-action"
            to={`/order/${encodeURIComponent(orderId)}/electronic?qrToken=${encodeURIComponent(order.qr_token)}`}
          >
            查看电子货单
          </Link>
        ) : null}
        <Link className="primary-button payment-action" to="/payment/orders/new">
          新建订单
        </Link>
      </div>
    </main>
  );
}
