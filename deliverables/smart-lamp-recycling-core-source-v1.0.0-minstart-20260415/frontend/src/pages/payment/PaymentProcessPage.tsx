import { useEffect, useMemo, useRef, useState } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { ArrowLeft, ExternalLink, LoaderCircle, RefreshCw } from 'lucide-react';
import { ErrorState } from '../../components/feedback/ErrorState';
import { LoadingState } from '../../components/feedback/LoadingState';
import { QRCodePay } from '../../components/QRCodePay/QRCodePay';
import { PaymentStatus } from '../../components/PaymentStatus/PaymentStatus';
import { paymentApi } from '../../services/paymentApi';
import type {
  PaymentOrderView,
  PaymentPrepayResponse,
  PaymentTradeType,
} from '../../modules/payment/types';
import { createIdempotentKey, detectTradeType, formatFen } from '../../modules/payment/utils';

export function PaymentProcessPage() {
  const { orderId = '' } = useParams();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const requestedTradeType = searchParams.get('tradeType');
  const tradeType = useMemo<PaymentTradeType>(() => {
    return requestedTradeType === 'H5' || requestedTradeType === 'NATIVE'
      ? requestedTradeType
      : detectTradeType();
  }, [requestedTradeType]);
  const [order, setOrder] = useState<PaymentOrderView | null>(null);
  const [prepay, setPrepay] = useState<PaymentPrepayResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [confirming, setConfirming] = useState(false);
  const startedRef = useRef(false);
  const idempotentKey = useMemo(() => createIdempotentKey('prepay'), []);

  useEffect(() => {
    if (!orderId || startedRef.current) {
      return;
    }
    startedRef.current = true;

    let disposed = false;

    async function run() {
      try {
        const currentOrder = await paymentApi.getPaymentStatus(orderId, true);
        if (currentOrder.payment_status === 'PAID') {
          navigate(`/payment/orders/${encodeURIComponent(orderId)}/pay/success`, {
            replace: true,
          });
          return;
        }

        const prepayResult = await paymentApi.prepay(
          {
            order_id: orderId,
            amount: currentOrder.payable_total,
            trade_type: tradeType,
            return_url: `${window.location.origin}/payment/orders/${encodeURIComponent(orderId)}/pay/success`,
            app_name: 'AI Light Assistant',
            app_url: window.location.origin,
          },
          idempotentKey,
        );

        if (!disposed) {
          const refreshedOrder = await paymentApi.getPaymentStatus(orderId, true);
          setOrder(refreshedOrder);
          setPrepay(prepayResult);
          setLoading(false);
        }
      } catch (requestError) {
        if (!disposed) {
          setError(
            requestError instanceof Error ? requestError.message : 'Failed to start payment.',
          );
          setLoading(false);
        }
      }
    }

    void run();

    return () => {
      disposed = true;
    };
  }, [idempotentKey, navigate, orderId, tradeType]);

  useEffect(() => {
    if (!orderId) {
      return;
    }

    const timer = window.setInterval(async () => {
      try {
        const result = await paymentApi.getPaymentStatus(orderId, true);
        setOrder(result);
        if (result.payment_status === 'PAID') {
          navigate(`/payment/orders/${encodeURIComponent(orderId)}/pay/success`, {
            replace: true,
          });
        }
      } catch {
        // keep polling quietly; the page already surfaces the initial error
      }
    }, 3000);

    return () => {
      window.clearInterval(timer);
    };
  }, [navigate, orderId]);

  async function handleConfirmPayment() {
    if (!orderId) {
      return;
    }

    setConfirming(true);
    setError(null);

    try {
      const result = await paymentApi.confirmPayment(orderId);
      setOrder(result);
      navigate(`/payment/orders/${encodeURIComponent(orderId)}/pay/success`, {
        replace: true,
      });
    } catch (requestError) {
      setError(
        requestError instanceof Error ? requestError.message : 'Failed to confirm payment.',
      );
    } finally {
      setConfirming(false);
    }
  }

  if (loading) {
    return (
      <main className="payment-page payment-page--center">
        <LoadingState label="正在生成支付二维码..." />
      </main>
    );
  }

  if (!order || !prepay) {
    return (
      <main className="payment-page">
        <header className="payment-page__header">
          <Link className="icon-button" to={`/payment/orders/${encodeURIComponent(orderId)}`}>
            <ArrowLeft size={20} />
          </Link>
          <strong>支付</strong>
          <span />
        </header>
        <ErrorState title="支付不可用" description={error || '没有可用的支付信息。'} />
      </main>
    );
  }

  const payUrl = prepay.code_url || prepay.h5_url || '';

  return (
    <main className="payment-page">
      <header className="payment-page__header">
        <Link className="icon-button" to={`/payment/orders/${encodeURIComponent(orderId)}`}>
          <ArrowLeft size={20} />
        </Link>
        <strong>支付</strong>
        <button type="button" className="icon-button" onClick={() => window.location.reload()}>
          <RefreshCw size={18} />
        </button>
      </header>

      <PaymentStatus
        kind="processing"
        title="扫码支付"
        description={
          tradeType === 'H5'
            ? '当前由智能体后端统一生成支付入口，请优先使用下方二维码支付，支付完成后再确认。'
            : '请先使用下方二维码完成支付，支付成功后点击确认按钮，让智能体继续同步货单和物流。'
        }
        detail={`${order.order_id} | ${formatFen(order.payable_total, order.amount_currency)}`}
      />

      {error ? <ErrorState title="支付确认失败" description={error} /> : null}

      {payUrl ? (
        <QRCodePay
          codeUrl={payUrl}
          orderId={order.order_id}
          amount={order.payable_total}
          currency={order.amount_currency}
          tradeType={prepay.trade_type}
        />
      ) : null}

      <section className="payment-card">
        <div className="payment-card__section-title">支付确认</div>
        <p className="payment-copy">
          支付完成后点击下面按钮，前端会向智能体后端刷新订单状态，并继续同步电子货单和运单状态。
        </p>
        <button
          type="button"
          className="primary-button payment-anchor"
          onClick={() => {
            void handleConfirmPayment();
          }}
          disabled={confirming}
        >
          {confirming ? <LoaderCircle size={17} className="payment-status__spin" /> : null}
          我已完成支付
        </button>
        {payUrl ? (
          <a className="secondary-button payment-anchor" href={payUrl}>
            <ExternalLink size={17} />
            打开电子货单地址
          </a>
        ) : null}
      </section>

      <section className="payment-card">
        <div className="payment-card__section-title">当前状态</div>
        <div className="payment-meta-grid">
          <div>
            <span>支付状态</span>
            <strong>{order.payment_status}</strong>
          </div>
          <div>
            <span>支付方式</span>
            <strong>{prepay.trade_type}</strong>
          </div>
          <div>
            <span>二维码令牌</span>
            <strong>{prepay.qr_token || '--'}</strong>
          </div>
          <div>
            <span>过期时间</span>
            <strong>{prepay.time_expire || '--'}</strong>
          </div>
          <div>
            <span>支付流水</span>
            <strong>{order.transaction_id || '--'}</strong>
          </div>
          <div>
            <span>运单号</span>
            <strong>{order.waybill_id || '--'}</strong>
          </div>
        </div>
      </section>
    </main>
  );
}
