import { useEffect, useMemo, useRef, useState } from 'react';
import { LoaderCircle } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { LoadingState } from '../../../components/feedback/LoadingState';
import { getCheckoutDraft, selectRecommendationFromFlow } from '../../../services/chatFlowStore';
import { paymentApi } from '../../../services/paymentApi';
import { buildVisionImageUrl } from '../../../services/visionApi';
import type { GenerateQrResponse } from '../../../types/api';
import type { ChatCard } from '../../../types/chat';
import type { AgentCheckoutFormResponse } from '../../../types/agent';
import type { PaymentFormState, PaymentOrderView } from '../types';
import {
  buildOrderPayload,
  createDefaultPaymentForm,
  createIdempotentKey,
  formatFen,
} from '../utils';
import { getInstallTypeLabel } from '../../vision/display';

type CheckoutFormCardProps = {
  payload: Extract<ChatCard, { type: 'checkout_form' }>['data'];
  onOpenOrder: (orderId: string, qrToken: string) => void;
};

type GeneratedOrderState = {
  orderId: string;
  qr: GenerateQrResponse;
};

export function CheckoutFormCard({ payload, onOpenOrder }: CheckoutFormCardProps) {
  const navigate = useNavigate();
  const [schema, setSchema] = useState<AgentCheckoutFormResponse | null>(null);
  const [form, setForm] = useState<PaymentFormState>(() => createDefaultPaymentForm());
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [generatedOrder, setGeneratedOrder] = useState<GeneratedOrderState | null>(null);
  const [paidOrder, setPaidOrder] = useState<PaymentOrderView | null>(null);
  const [checkingPayment, setCheckingPayment] = useState(false);
  const autoPrepayTriggeredRef = useRef(false);
  const tradeType = useMemo(() => 'H5' as const, []);

  useEffect(() => {
    let disposed = false;

    async function run() {
      try {
        const result = await paymentApi.getCheckoutForm(payload.session_id);
        if (disposed) {
          return;
        }

        setSchema(result);
        setForm((current) => ({
          ...current,
          ...result.defaults,
          session_id: result.session_id,
          name: payload.prefill?.name || result.defaults.name || current.name,
          phone: payload.prefill?.phone || result.defaults.phone || current.phone,
          full_address:
            payload.prefill?.full_address ||
            result.defaults.full_address ||
            current.full_address,
          street: payload.prefill?.street || result.defaults.street || current.street,
          longitude:
            payload.prefill?.longitude !== undefined
              ? String(payload.prefill.longitude)
              : result.defaults.longitude || current.longitude,
          latitude:
            payload.prefill?.latitude !== undefined
              ? String(payload.prefill.latitude)
              : result.defaults.latitude || current.latitude,
          selected_new_sku:
            payload.prefill?.selected_new_sku ||
            result.selection.selected_new_sku ||
            result.defaults.selected_new_sku ||
            current.selected_new_sku,
          selected_old_sku:
            result.selection.selected_old_sku ||
            result.defaults.selected_old_sku ||
            current.selected_old_sku,
          qty: String(payload.prefill?.qty || result.defaults.qty || current.qty || '1'),
          payable_total: result.defaults.payable_total || current.payable_total,
        }));
        setLoading(false);
      } catch (requestError) {
        if (!disposed) {
          setError(requestError instanceof Error ? requestError.message : '下单卡片加载失败');
          setLoading(false);
        }
      }
    }

    autoPrepayTriggeredRef.current = false;
    setLoading(true);
    setError(null);
    setGeneratedOrder(null);
    setPaidOrder(null);
    void run();

    return () => {
      disposed = true;
    };
  }, [payload.session_id, payload.prefill]);

  useEffect(() => {
    if (!generatedOrder || paidOrder) {
      return;
    }

    const orderId = generatedOrder.orderId;
    let disposed = false;

    async function pollOrderStatus() {
      try {
        const latest = await paymentApi.getPaymentStatus(orderId, true);
        if (disposed) {
          return;
        }
        if (latest.payment_status === 'PAID') {
          setPaidOrder(latest);
          setError(null);
        }
      } catch {
        // polling should be silent
      }
    }

    void pollOrderStatus();
    const timer = window.setInterval(() => {
      void pollOrderStatus();
    }, 3000);

    return () => {
      disposed = true;
      window.clearInterval(timer);
    };
  }, [generatedOrder, paidOrder]);

  function extractTokenFromQrUrl(qrUrl: string) {
    try {
      const parsed = new URL(qrUrl, window.location.origin);
      return parsed.searchParams.get('token') || parsed.searchParams.get('qrToken') || '';
    } catch {
      return '';
    }
  }

  async function handleNormalizeAddress() {
    try {
      const normalized = await paymentApi.normalizeAddress({
        full_address: form.full_address,
        region: form.region,
        province: form.province,
        city: form.city,
        district: form.district,
        street: form.street,
        postal_code: form.postal_code,
        longitude: form.longitude,
        latitude: form.latitude,
        location_source: form.location_source,
        address_source: form.address_source,
      });

      setForm((current) => ({
        ...current,
        full_address: normalized.full_address,
        region: normalized.region,
        province: normalized.province,
        city: normalized.city,
        district: normalized.district,
        street: normalized.street,
        postal_code: normalized.postal_code,
        longitude: String(normalized.longitude),
        latitude: String(normalized.latitude),
        location_source: normalized.location_source,
        address_source: normalized.address_source,
      }));
      return normalized;
    } catch {
      return null;
    }
  }

  async function ensureOrderGenerated() {
    if (generatedOrder) {
      return generatedOrder;
    }

    const activeSchema = schema;
    if (!activeSchema) {
      setError('下单卡片加载中，请稍后重试');
      return null;
    }

    if (!activeSchema.selection.selected_new_sku && !form.selected_new_sku) {
      setError('请先选择推荐灯具');
      return null;
    }

    if (!form.full_address || form.full_address.includes('请补充详细地址')) {
      setError('请先补充详细收货地址');
      return null;
    }

    setSubmitting(true);
    setError(null);

    try {
      const normalized = await handleNormalizeAddress();
      const nextForm: PaymentFormState = normalized
        ? {
            ...form,
            full_address: normalized.full_address,
            region: normalized.region,
            province: normalized.province,
            city: normalized.city,
            district: normalized.district,
            street: normalized.street,
            postal_code: normalized.postal_code,
            longitude: String(normalized.longitude),
            latitude: String(normalized.latitude),
            location_source: normalized.location_source,
            address_source: normalized.address_source,
          }
        : form;

      const order = await paymentApi.createOrder(
        buildOrderPayload(nextForm, activeSchema.selection),
        createIdempotentKey('order'),
      );

      const prepay = await paymentApi.prepay(
        {
          order_id: order.order_id,
          amount: order.payable_total,
          trade_type: tradeType,
          return_url: `${window.location.origin}/payment/orders/${encodeURIComponent(order.order_id)}/pay/success`,
          app_name: 'AI Light Assistant',
          app_url: window.location.origin,
        },
        createIdempotentKey('prepay'),
      );

      const qrUrl = prepay.code_url || prepay.h5_url;
      if (!qrUrl) {
        throw new Error('支付二维码生成失败');
      }

      const nextGeneratedOrder: GeneratedOrderState = {
        orderId: order.order_id,
        qr: {
          trace_id: prepay.trace_id || order.trace_id || '',
          qr_token: prepay.qr_token || extractTokenFromQrUrl(qrUrl),
          qr_url: qrUrl,
          expire_at: prepay.time_expire || '',
        },
      };
      setGeneratedOrder(nextGeneratedOrder);
      return nextGeneratedOrder;
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : '创建订单失败');
      return null;
    } finally {
      setSubmitting(false);
    }
  }

  useEffect(() => {
    if (loading || !schema || generatedOrder || paidOrder || autoPrepayTriggeredRef.current) {
      return;
    }
    autoPrepayTriggeredRef.current = true;
    void ensureOrderGenerated();
  }, [loading, schema, generatedOrder, paidOrder, form.full_address]);

  async function handleRefreshPaymentStatus() {
    if (!generatedOrder) {
      return;
    }

    setCheckingPayment(true);
    setError(null);
    try {
      const latest = await paymentApi.getPaymentStatus(generatedOrder.orderId, true);
      if (latest.payment_status === 'PAID') {
        setPaidOrder(latest);
      } else {
        setError('已刷新，当前还未收到支付成功回执');
      }
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : '刷新支付状态失败');
    } finally {
      setCheckingPayment(false);
    }
  }

  function buildEtaText(order: PaymentOrderView) {
    const baseline = order.paid_at || order.payment_updated_at || new Date().toISOString();
    const eta = new Date(baseline);
    if (Number.isNaN(eta.getTime())) {
      return '尽快';
    }
    eta.setMinutes(eta.getMinutes() + 38);
    const hh = String(eta.getHours()).padStart(2, '0');
    const mm = String(eta.getMinutes()).padStart(2, '0');
    return `${hh}:${mm}`;
  }

  async function handlePayNow() {
    const order = await ensureOrderGenerated();
    if (!order) {
      return;
    }
    void paymentApi.confirmPayment(order.orderId).catch(() => null);
    navigate(`/payment/orders/${encodeURIComponent(order.orderId)}/pay/success`);
  }

  async function handleOpenOrderDetail() {
    const order = await ensureOrderGenerated();
    if (!order) {
      return;
    }
    if (!order.qr.qr_token) {
      setError('订单已创建，但暂未拿到订单访问凭证，请稍后重试');
      return;
    }
    onOpenOrder(order.orderId, order.qr.qr_token);
  }

  if (loading) {
    return (
      <section className="payment-card">
        <LoadingState label="正在加载下单卡片..." />
      </section>
    );
  }

  if (!schema) {
    return (
      <section className="payment-card">
        <div className="payment-card__section-title">下单卡片不可用</div>
      </section>
    );
  }

  const flowDraft = getCheckoutDraft(payload.session_id);
  const flowSelected = selectRecommendationFromFlow(
    payload.session_id,
    payload.prefill?.selected_new_sku || schema.selection.selected_new_sku,
  );

  const oldLampLabel = schema.selection.selected_old_kind
    ? getInstallTypeLabel(schema.selection.selected_old_kind)
    : schema.summary.old_lamp;

  const newLampLabel =
    payload.prefill?.selected_new_kind ||
    schema.selection.selected_new_kind ||
    schema.summary.new_lamp;

  const displayTitle =
    payload.prefill?.selected_new_title ||
    schema.selection.selected_new_title ||
    flowDraft?.selected_new_title ||
    flowSelected?.title ||
    schema.summary.new_lamp;

  const displayImagePath =
    payload.prefill?.selected_new_image_path ||
    schema.selection.selected_new_image_path ||
    flowDraft?.selected_new_image_path ||
    flowSelected?.image_path ||
    '';

  const displayQty = payload.prefill?.qty || Number(form.qty || '1') || 1;
  const selectionSummary = payload.prefill?.selection_summary;

  return (
    <section className={`payment-card${error ? ' payment-card--has-error' : ''}`}>
      <div className="payment-card__section-title">下单卡片</div>

      <div className="payment-selection-grid">
        <article className="payment-selection-card">
          {schema.selection.selected_old_image_path ? (
            <img
              src={buildVisionImageUrl(schema.selection.selected_old_image_path)}
              alt="旧灯图片"
              className="payment-selection-card__image"
            />
          ) : null}
          <span>旧灯</span>
          <strong>{oldLampLabel}</strong>
        </article>
        <article className="payment-selection-card">
          {displayImagePath ? (
            <img
              src={buildVisionImageUrl(displayImagePath)}
              alt="新灯图片"
              className="payment-selection-card__image"
            />
          ) : null}
          <span>新灯</span>
          <strong>{newLampLabel}</strong>
        </article>
      </div>

      <div className="payment-meta-grid">
        <div>
          <span>旧灯种类</span>
          <strong>{schema.summary.old_lamp}</strong>
        </div>
        <div>
          <span>新灯种类</span>
          <strong>{schema.summary.new_lamp}</strong>
        </div>
        <div>
          <span>旧灯回收抵扣</span>
          <strong>
            {schema.summary.currency} {schema.summary.recycle_quote.toFixed(2)}
          </strong>
        </div>
        <div>
          <span>待支付金额</span>
          <strong>{formatFen(Number(form.payable_total), schema.summary.currency)}</strong>
        </div>
      </div>

      {paidOrder ? (
        <>
          <article className="payment-success-inline">
            <div className="payment-success-inline__head">
              <strong>下单成功</strong>
              <p>{paidOrder.snapshot.items[0]?.selected_new_title || displayTitle}</p>
            </div>

            <div className="payment-success-inline__product">
              {paidOrder.snapshot.items[0]?.selected_new_image_path || displayImagePath ? (
                <img
                  src={buildVisionImageUrl(
                    paidOrder.snapshot.items[0]?.selected_new_image_path || displayImagePath,
                  )}
                  alt={paidOrder.snapshot.items[0]?.selected_new_title || '灯具图片'}
                  className="payment-success-inline__image"
                />
              ) : (
                <div className="payment-success-inline__image payment-success-inline__image--empty">
                  灯具
                </div>
              )}
              <div className="payment-success-inline__detail">
                <strong>{paidOrder.snapshot.items[0]?.selected_new_title || displayTitle}</strong>
                <p>
                  {getInstallTypeLabel(paidOrder.snapshot.items[0]?.selected_new_kind || '') || newLampLabel}
                  {' / '}
                  x{paidOrder.snapshot.items[0]?.qty || displayQty}
                </p>
                <strong>{formatFen(paidOrder.payable_total, paidOrder.amount_currency)}</strong>
              </div>
            </div>

            <div className="payment-success-inline__meta">
              <div>
                <span>配送至</span>
                <strong>{paidOrder.snapshot.address?.full_address || form.full_address}</strong>
              </div>
              <div>
                <span>联系人</span>
                <strong>
                  {paidOrder.snapshot.user?.name || form.name}
                  {' '}
                  {paidOrder.snapshot.user?.phone || form.phone}
                </strong>
              </div>
            </div>

            <button
              type="button"
              className="secondary-button payment-success-inline__action"
              onClick={() => {
                const qrToken = paidOrder.qr_token || generatedOrder?.qr.qr_token;
                if (qrToken) {
                  onOpenOrder(paidOrder.order_id, qrToken);
                }
              }}
            >
              订单详情
            </button>
          </article>

          <div className="payment-chat-pill">已完成支付</div>

          <article className="payment-success-status">
            <div>
              <strong>商家已接单</strong>
              <p>预计 {buildEtaText(paidOrder)} 送达</p>
            </div>
            <button
              type="button"
              className="icon-button"
              onClick={() => {
                void handleRefreshPaymentStatus();
              }}
              disabled={checkingPayment}
            >
              {checkingPayment ? <LoaderCircle size={16} className="payment-status__spin" /> : '↻'}
            </button>
          </article>
        </>
      ) : (
        <>
          <article className="payment-pending-inline">
            <div className="payment-pending-inline__head">
              <strong>{generatedOrder ? '已为你生成订单（预支付）' : '确认下单并支付'}</strong>
              <p>{generatedOrder?.orderId || `${form.name} ${form.phone}`}</p>
            </div>

            <div className="payment-success-inline__product">
              {displayImagePath ? (
                <img
                  src={buildVisionImageUrl(displayImagePath)}
                  alt={displayTitle}
                  className="payment-success-inline__image"
                />
              ) : (
                <div className="payment-success-inline__image payment-success-inline__image--empty">
                  灯具
                </div>
              )}
              <div className="payment-success-inline__detail">
                <strong>{displayTitle}</strong>
                <p>{selectionSummary || `${newLampLabel} / x${displayQty}`}</p>
                <strong>{formatFen(Number(form.payable_total), schema.summary.currency)}</strong>
              </div>
            </div>

            <div className="payment-success-inline__meta">
              <div>
                <span>配送至</span>
                <strong>{form.full_address}</strong>
              </div>
              <div>
                <span>联系人</span>
                <strong>
                  {form.name} {form.phone}
                </strong>
              </div>
            </div>

            <div className="payment-pending-inline__actions">
              <button
                type="button"
                className="secondary-button payment-anchor"
                onClick={() => {
                  void handleOpenOrderDetail();
                }}
                disabled={submitting}
              >
                {submitting ? <LoaderCircle size={17} className="payment-status__spin" /> : null}
                进店选购
              </button>
              <button
                type="button"
                className="primary-button payment-anchor"
                onClick={() => {
                  void handlePayNow();
                }}
                disabled={submitting}
              >
                {submitting ? <LoaderCircle size={17} className="payment-status__spin" /> : null}
                支付宝付款
              </button>
            </div>
          </article>

          {generatedOrder ? (
            <button
              type="button"
              className="primary-button payment-form__submit"
              onClick={() => {
                void handleRefreshPaymentStatus();
              }}
              disabled={checkingPayment}
            >
              {checkingPayment ? <LoaderCircle size={18} className="payment-status__spin" /> : null}
              我已完成支付
            </button>
          ) : null}
        </>
      )}
    </section>
  );
}
