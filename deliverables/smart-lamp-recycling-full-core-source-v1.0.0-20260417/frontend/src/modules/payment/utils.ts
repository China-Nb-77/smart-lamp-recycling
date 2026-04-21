import type {
  CheckoutDraft,
  PaymentCreateOrderRequest,
  PaymentFormState,
  PaymentTradeType,
} from './types';

export function createTraceId(prefix = 'trace') {
  return `${prefix}_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

export function createIdempotentKey(prefix = 'idem') {
  return `${prefix}:${Date.now()}:${Math.random().toString(36).slice(2, 8)}`;
}

export function detectTradeType(): PaymentTradeType {
  const ua = navigator.userAgent.toLowerCase();
  return ua.includes('android') || ua.includes('iphone') || ua.includes('mobile')
    ? 'H5'
    : 'NATIVE';
}

export function appendRedirectUrl(h5Url: string, redirectUrl?: string | null) {
  if (!redirectUrl) {
    return h5Url;
  }

  const divider = h5Url.includes('?') ? '&' : '?';
  return `${h5Url}${divider}redirect_url=${encodeURIComponent(redirectUrl)}`;
}

export function formatFen(amount?: number | null, currency = 'CNY') {
  if (amount === undefined || amount === null) {
    return '--';
  }

  const value = amount / 100;
  if (currency === 'CNY') {
    return `¥${value.toFixed(2)}`;
  }
  return `${value.toFixed(2)} ${currency}`;
}

export function toFenAmount(amount: number) {
  return Math.max(Math.round(amount * 100), 1);
}

export function buildOrderPayload(
  form: PaymentFormState,
  draft?: CheckoutDraft | null,
): PaymentCreateOrderRequest {
  return {
    session_id: form.session_id || undefined,
    trace_id: form.trace_id,
    user: {
      user_id: form.user_id || undefined,
      name: form.name,
      phone: form.phone,
    },
    address: {
      full_address: form.full_address,
      region: form.region || undefined,
      province: form.province || undefined,
      city: form.city || undefined,
      district: form.district || undefined,
      street: form.street || undefined,
      postal_code: form.postal_code || undefined,
      longitude: form.longitude ? Number(form.longitude) : undefined,
      latitude: form.latitude ? Number(form.latitude) : undefined,
      location_source: form.location_source || 'USER_INPUT',
      address_source: form.address_source || 'USER_INPUT',
    },
    items: [
      {
        selected_old_sku: form.selected_old_sku || undefined,
        selected_old_title: draft?.selected_old_title,
        selected_old_image_path: draft?.selected_old_image_path,
        selected_old_kind: draft?.selected_old_kind,
        selected_new_sku: form.selected_new_sku || undefined,
        selected_new_title: draft?.selected_new_title,
        selected_new_image_path: draft?.selected_new_image_path,
        selected_new_kind: draft?.selected_new_kind,
        qty: Number(form.qty),
      },
    ],
    payable_total: Number(form.payable_total),
    currency: 'CNY',
    amount_unit: 'FEN',
    access_domain: window.location.origin,
  };
}

export function applyCheckoutDraft(
  current: PaymentFormState,
  draft?: CheckoutDraft | null,
): PaymentFormState {
  if (!draft) {
    return current;
  }

  const payableTotal =
    toFenAmount(draft.selected_new_price) - toFenAmount(draft.recycle_quote || 0);

  return {
    ...current,
    selected_old_sku: draft.selected_old_sku || current.selected_old_sku,
    selected_new_sku: draft.selected_new_sku,
    qty: String(draft.qty || 1),
    payable_total: String(Math.max(payableTotal, 100)),
  };
}

export function createDefaultPaymentForm(draft?: CheckoutDraft | null): PaymentFormState {
  const base: PaymentFormState = {
    session_id: '',
    trace_id: createTraceId('tr_pay'),
    user_id: 'user_demo_001',
    name: '张三',
    gender: '先生',
    phone: '13800000000',
    full_address: '上海市浦东新区测试路 100 号',
    region: 'shanghai',
    province: '上海市',
    city: '上海市',
    district: '浦东新区',
    street: '测试路 100 号',
    postal_code: '200120',
    longitude: '121.544',
    latitude: '31.221',
    location_source: 'USER_INPUT',
    address_source: 'USER_INPUT',
    selected_old_sku: '',
    selected_new_sku: '',
    qty: '1',
    payable_total: '19900',
  };

  return applyCheckoutDraft(base, draft);
}
