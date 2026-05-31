import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, QrCode, RefreshCw, Smartphone } from 'lucide-react';
import { ErrorState } from '../../components/feedback/ErrorState';
import { LoadingState } from '../../components/feedback/LoadingState';
import { paymentApi } from '../../services/paymentApi';
import { buildVisionImageUrl } from '../../services/visionApi';
import type { PaymentOrderView } from '../../modules/payment/types';
import { formatFen } from '../../modules/payment/utils';
import { getInstallTypeLabel, getLampDisplayTitle } from '../../modules/vision/display';

export function PaymentOrderDetailPage() {
  const { orderId = '' } = useParams();
  const navigate = useNavigate();
  const [order, setOrder] = useState<PaymentOrderView | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let disposed = false;

    async function run() {
      try {
        const result = await paymentApi.getPaymentStatus(orderId, true);
        if (!disposed) {
          setOrder(result);
          setLoading(false);
        }
      } catch (requestError) {
        if (!disposed) {
          setError(
            requestError instanceof Error ? requestError.message : 'Failed to load order.',
          );
          setLoading(false);
        }
      }
    }

    if (orderId) {
      void run();
    }

    return () => {
      disposed = true;
    };
  }, [orderId]);

  if (loading) {
    return (
      <main className="payment-page payment-page--center">
        <LoadingState label="Loading order details..." />
      </main>
    );
  }

  if (!order || error) {
    return (
      <main className="payment-page">
        <header className="payment-page__header">
          <Link className="icon-button" to="/payment/orders/new">
            <ArrowLeft size={20} />
          </Link>
          <strong>订单详情</strong>
          <span />
        </header>
        <ErrorState title="订单不可用" description={error || '未找到订单。'} />
      </main>
    );
  }

  return (
    <main className="payment-page">
      <header className="payment-page__header">
        <Link className="icon-button" to="/payment/orders/new">
          <ArrowLeft size={20} />
        </Link>
        <strong>订单详情</strong>
        <button type="button" className="icon-button" onClick={() => window.location.reload()}>
          <RefreshCw size={18} />
        </button>
      </header>

      <section className="payment-card">
        <div className="payment-card__header">
          <div>
            <strong>{order.order_id}</strong>
            <p>{order.trace_id || '无 trace_id'}</p>
          </div>
          <div className={`payment-tag payment-tag--${order.payment_status.toLowerCase()}`}>
            {order.payment_status}
          </div>
        </div>
        <div className="payment-meta-grid">
          <div>
            <span>订单状态</span>
            <strong>{order.order_status}</strong>
          </div>
          <div>
            <span>待支付金额</span>
            <strong>{formatFen(order.payable_total, order.amount_currency)}</strong>
          </div>
          <div>
            <span>支付流水</span>
            <strong>{order.transaction_id || '--'}</strong>
          </div>
          <div>
            <span>支付键</span>
            <strong>{order.payment_idempotent_key || '--'}</strong>
          </div>
        </div>
      </section>

      <section className="payment-card">
        <div className="payment-card__section-title">收货信息</div>
        <div className="payment-detail-list">
          <div>
            <span>收货人</span>
            <strong>{order.contact_name || '--'}</strong>
          </div>
          <div>
            <span>联系电话</span>
            <strong>{order.contact_phone || '--'}</strong>
          </div>
          <div>
            <span>收货地址</span>
            <strong>{order.full_address || '--'}</strong>
          </div>
        </div>
      </section>

      <section className="payment-card">
        <div className="payment-card__section-title">灯具明细</div>
        <div className="payment-items">
          {order.snapshot.items.map((item, index) => (
            <article
              key={`${item.selected_new_sku || item.selected_old_sku || index}`}
              className="payment-item"
            >
              {item.selected_new_image_path ? (
                <img
                  src={buildVisionImageUrl(item.selected_new_image_path)}
                  alt={item.selected_new_title || '灯具图片'}
                  className="payment-item__image"
                />
              ) : null}
              <div>
                <strong>
                  {getLampDisplayTitle({
                    visual_style: item.selected_new_kind,
                    fallbackTitle: item.selected_new_title,
                  })}
                </strong>
                <p>
                  旧灯：
                  {item.selected_old_kind
                    ? getInstallTypeLabel(item.selected_old_kind)
                    : item.selected_old_title || '旧灯具'}
                </p>
              </div>
              <strong>x{item.qty}</strong>
            </article>
          ))}
        </div>
      </section>

      <div className="payment-action-row">
        <button
          type="button"
          className="secondary-button payment-action"
          onClick={() =>
            navigate(
              `/payment/orders/${encodeURIComponent(order.order_id)}/pay?tradeType=NATIVE`,
            )
          }
        >
          <QrCode size={17} />
          扫码支付
        </button>
        <button
          type="button"
          className="primary-button payment-action"
          onClick={() =>
            navigate(`/payment/orders/${encodeURIComponent(order.order_id)}/pay?tradeType=H5`)
          }
        >
          <Smartphone size={17} />
          H5 支付
        </button>
      </div>

      {order.qr_token ? (
        <div className="payment-action-row">
          <Link
            className="secondary-button payment-action"
            to={`/order/${encodeURIComponent(order.order_id)}/electronic?qrToken=${encodeURIComponent(order.qr_token)}`}
          >
            查看电子货单
          </Link>
        </div>
      ) : null}
    </main>
  );
}
