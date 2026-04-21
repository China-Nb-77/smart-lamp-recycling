import { useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { ArrowLeft, CreditCard, LoaderCircle, LocateFixed } from 'lucide-react';
import { ErrorState } from '../../components/feedback/ErrorState';
import { LoadingState } from '../../components/feedback/LoadingState';
import { paymentApi } from '../../services/paymentApi';
import { buildVisionImageUrl } from '../../services/visionApi';
import {
  buildOrderPayload,
  createDefaultPaymentForm,
  createIdempotentKey,
  formatFen,
} from '../../modules/payment/utils';
import { getCurrentPositionWithFallback } from '../../modules/payment/geolocation';
import type { PaymentFormState } from '../../modules/payment/types';
import type { AgentCheckoutFormResponse } from '../../types/agent';
import { getInstallTypeLabel } from '../../modules/vision/display';

export function PaymentOrderCreatePage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const sessionId = searchParams.get('sessionId') || '';
  const selectedNewSku = searchParams.get('newSku') || '';
  const selectedOldSku = searchParams.get('oldSku') || '';
  const payableTotal = searchParams.get('payableTotal') || '';
  const [schema, setSchema] = useState<AgentCheckoutFormResponse | null>(null);
  const [form, setForm] = useState<PaymentFormState>(() => createDefaultPaymentForm());
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [locating, setLocating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let disposed = false;

    async function run() {
      try {
        const result = await paymentApi.getCheckoutForm(sessionId || 'manual-checkout');
        if (disposed) {
          return;
        }

        setSchema(result);
        setForm((current) => ({
          ...current,
          ...result.defaults,
          session_id: result.session_id,
          selected_new_sku:
            selectedNewSku || result.defaults.selected_new_sku || current.selected_new_sku,
          selected_old_sku:
            selectedOldSku || result.defaults.selected_old_sku || current.selected_old_sku,
          payable_total:
            payableTotal || result.defaults.payable_total || current.payable_total,
        }));
        setLoading(false);
      } catch (requestError) {
        if (!disposed) {
          setError(
            requestError instanceof Error ? requestError.message : '加载表单失败。',
          );
          setLoading(false);
        }
      }
    }

    void run();
    return () => {
      disposed = true;
    };
  }, [payableTotal, selectedNewSku, selectedOldSku, sessionId]);

  const setField = (key: keyof PaymentFormState, value: string) => {
    setForm((current) => ({
      ...current,
      [key]: value,
    }));
  };

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

  async function handleLocate() {
    setLocating(true);
    setError(null);

    try {
      const position = await getCurrentPositionWithFallback();
      const normalized = await paymentApi.locateAddress(
        position.coords.latitude,
        position.coords.longitude,
        form.full_address,
      );
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
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : '定位失败');
    } finally {
      setLocating(false);
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);

    try {
      if (!schema?.selection.selected_new_sku) {
        throw new Error('请先回到聊天页选择推荐灯具。');
      }
      if (form.full_address.includes('请补充详细地址')) {
        throw new Error('请先补充详细收货地址');
      }

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
        buildOrderPayload(nextForm, schema.selection),
        createIdempotentKey('order'),
      );
      navigate(`/payment/orders/${encodeURIComponent(order.order_id)}/pay`);
    } catch (requestError) {
      setError(
        requestError instanceof Error ? requestError.message : '创建订单失败',
      );
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return (
      <main className="payment-page payment-page--center">
        <LoadingState label="正在加载下单表单..." />
      </main>
    );
  }

  if (!schema) {
    return (
      <main className="payment-page">
        <header className="payment-page__header">
          <Link className="icon-button" to="/">
            <ArrowLeft size={20} />
          </Link>
          <strong>填写信息</strong>
          <span />
        </header>
        <ErrorState title="表单不可用" description={error || '没有可用的下单草稿。'} />
      </main>
    );
  }

  const oldLampLabel = schema.selection.selected_old_kind
    ? getInstallTypeLabel(schema.selection.selected_old_kind)
    : schema.summary.old_lamp;
  const newLampLabel = schema.selection.selected_new_kind
    ? getInstallTypeLabel(schema.selection.selected_new_kind)
    : schema.summary.new_lamp;

  return (
    <main className="payment-page">
      <header className="payment-page__header">
        <Link className="icon-button" to="/">
          <ArrowLeft size={20} />
        </Link>
        <strong>{schema.schema.title}</strong>
        <Link className="payment-link-button" to="/">
          返回聊天
        </Link>
      </header>

      <section className="payment-hero">
        <span className="payment-hero__badge">
          <CreditCard size={18} />
          智能体下单流程
        </span>
        <h1>确认收货信息后，下一步就是微信扫码支付。</h1>
        <p>{schema.summary.todo}</p>
      </section>

      <section className="payment-card">
        <div className="payment-card__section-title">灯具信息</div>
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
            {schema.selection.selected_new_image_path ? (
              <img
                src={buildVisionImageUrl(schema.selection.selected_new_image_path)}
                alt="推荐新灯图片"
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
      </section>

      {error ? <ErrorState title="提交失败" description={error} /> : null}

      <form className="payment-form" onSubmit={handleSubmit}>
        {schema.schema.fields.map((field) => {
          const value = form[field.key as keyof PaymentFormState] || '';

          if (field.component === 'select') {
            return (
              <label key={field.key}>
                <span>{field.label}</span>
                <select
                  value={value}
                  onChange={(event) =>
                    setField(field.key as keyof PaymentFormState, event.target.value)
                  }
                  required={field.required}
                >
                  {(field.options || []).map((option) => (
                    <option key={`${field.key}_${option.value}`} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
            );
          }

          if (field.component === 'textarea') {
            return (
              <label key={field.key} className="payment-form__wide">
                <span>{field.label}</span>
                <div className="payment-form__textarea-wrap">
                  <textarea
                    rows={3}
                    value={value}
                    placeholder={field.placeholder}
                    onChange={(event) =>
                      setField(field.key as keyof PaymentFormState, event.target.value)
                    }
                    onBlur={() => {
                      void handleNormalizeAddress();
                    }}
                    required={field.required}
                  />
                  {field.action === 'locate' ? (
                      <button
                        type="button"
                        className="icon-button payment-form__locate"
                      onClick={() => {
                        void handleLocate();
                        }}
                        disabled={locating}
                        aria-label="定位"
                        title="定位"
                      >
                      {locating ? (
                        <>
                          <LoaderCircle size={18} className="payment-status__spin" />
                          <span>定位中</span>
                        </>
                      ) : (
                        <>
                          <LocateFixed size={18} />
                          <span>定位</span>
                        </>
                      )}
                    </button>
                  ) : null}
                </div>
              </label>
            );
          }

          return (
            <label key={field.key}>
              <span>{field.label}</span>
              <input
                type={field.type || 'text'}
                value={value}
                placeholder={field.placeholder}
                onChange={(event) =>
                  setField(field.key as keyof PaymentFormState, event.target.value)
                }
                required={field.required}
              />
            </label>
          );
        })}

        <button
          type="submit"
          className="primary-button payment-form__submit"
          disabled={submitting || !schema.selection.selected_new_sku}
        >
          {submitting ? <LoaderCircle size={18} className="payment-status__spin" /> : null}
          {schema.schema.submit_label}
        </button>
      </form>
    </main>
  );
}

