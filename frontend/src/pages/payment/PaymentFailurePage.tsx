import { Link, useParams, useSearchParams } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { PaymentStatus } from '../../components/PaymentStatus/PaymentStatus';

export function PaymentFailurePage() {
  const { orderId = '' } = useParams();
  const [searchParams] = useSearchParams();
  const reason = searchParams.get('reason') || 'PAYERROR';

  return (
    <main className="payment-page">
      <header className="payment-page__header">
        <Link className="icon-button" to={`/payment/orders/${encodeURIComponent(orderId)}`}>
          <ArrowLeft size={20} />
        </Link>
        <strong>支付失败</strong>
        <span />
      </header>

      <PaymentStatus
        kind="failure"
        title="支付未完成"
        description="后端订单状态没有进入 PAID，前端根据真实查询结果跳转到了失败页。"
        detail={`${orderId} · ${reason}`}
      />

      <div className="payment-action-row">
        <Link
          className="secondary-button payment-action"
          to={`/payment/orders/${encodeURIComponent(orderId)}`}
        >
          返回订单详情
        </Link>
        <Link
          className="primary-button payment-action"
          to={`/payment/orders/${encodeURIComponent(orderId)}/pay`}
        >
          重新支付
        </Link>
      </div>
    </main>
  );
}
