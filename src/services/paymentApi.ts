import { ApiError, extractErrorMessage } from './api/client';
import type {
  PaymentCreateOrderRequest,
  PaymentOrderView,
  PaymentPrepayRequest,
  PaymentPrepayResponse,
  PaymentSnapshot,
} from '../modules/payment/types';
import type {
  AgentAddressResponse,
  AgentCheckoutFormResponse,
  AgentLogisticsMapResponse,
  AgentLogisticsResponse,
} from '../types/agent';
import type { ElectronicOrderResponse } from '../types/api';

const visionBaseUrl = import.meta.env.VITE_VISION_API_BASE_URL || '/vision-api';
const songBaseUrl = import.meta.env.VITE_SONG_API_BASE_URL || '/song-api';
const SONG_ORDER_CACHE_KEY = 'ai-light.song.order-cache';

type RequestOptions = {
  method?: 'GET' | 'POST';
  body?: unknown;
  headers?: Record<string, string>;
};

type SongApiEnvelope<T> = {
  code: number;
  message: string;
  data: T;
};

type SongOrderQr = {
  qr_content?: string;
  qr_status?: string;
  expires_at?: string;
};

type SongOrderView = Omit<PaymentOrderView, 'snapshot'> & {
  snapshot: PaymentSnapshot;
  qr?: SongOrderQr;
};

type SongTrackPayload = {
  events?: Array<{
    time?: string;
    desc?: string;
  }>;
};

type SongElectronicOrderPayload = {
  trace_id?: string;
  order_id: string;
  status?: string;
  pay_status?: string;
  qr_status?: string;
  product_info?: {
    items?: Array<{
      selected_old_sku?: string;
      selected_new_sku?: string;
      qty?: number;
    }>;
  };
  amount?: {
    payable_total?: number;
    paid_amount_total?: number;
    currency?: string;
    amount_unit?: string;
  };
  waybill?: {
    waybill_id?: string;
    status?: string;
  };
  events?: Array<{
    time?: string;
    desc?: string;
  }>;
};

type SongOrderCacheEntry = {
  qr_token?: string;
  snapshot_items?: PaymentSnapshot['items'];
};

type SongOrderCache = Record<string, SongOrderCacheEntry>;

async function parseResponsePayload(response: Response) {
  const contentType = response.headers.get('content-type') || '';
  return contentType.includes('application/json') ? await response.json() : await response.text();
}

async function requestAgent<T>(
  path: string,
  { method = 'GET', body, headers }: RequestOptions = {},
) {
  const response = await fetch(`${visionBaseUrl}${path}`, {
    method,
    headers:
      body === undefined
        ? headers
        : {
            'Content-Type': 'application/json',
            ...(headers || {}),
          },
    body: body === undefined ? undefined : JSON.stringify(body),
  });

  const payload = await parseResponsePayload(response);
  if (!response.ok) {
    throw new ApiError(extractErrorMessage(payload), response.status, payload);
  }

  return payload as T;
}

async function requestSong<T>(
  path: string,
  { method = 'GET', body, headers }: RequestOptions = {},
) {
  const response = await fetch(`${songBaseUrl}${path}`, {
    method,
    headers:
      body === undefined
        ? headers
        : {
            'Content-Type': 'application/json',
            ...(headers || {}),
          },
    body: body === undefined ? undefined : JSON.stringify(body),
  });

  const payload = await parseResponsePayload(response);
  if (!response.ok) {
    throw new ApiError(extractErrorMessage(payload), response.status, payload);
  }

  if (payload && typeof payload === 'object' && 'code' in payload) {
    const envelope = payload as SongApiEnvelope<T>;
    if (envelope.code !== 0) {
      throw new ApiError(envelope.message || '请求失败，请稍后重试', response.status, payload);
    }
    return envelope.data;
  }

  return payload as T;
}

function canUseStorage() {
  return typeof window !== 'undefined' && typeof window.localStorage !== 'undefined';
}

function loadSongOrderCache(): SongOrderCache {
  if (!canUseStorage()) {
    return {};
  }

  try {
    const raw = window.localStorage.getItem(SONG_ORDER_CACHE_KEY);
    if (!raw) {
      return {};
    }
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === 'object' ? (parsed as SongOrderCache) : {};
  } catch {
    return {};
  }
}

function saveSongOrderCache(store: SongOrderCache) {
  if (!canUseStorage()) {
    return;
  }
  window.localStorage.setItem(SONG_ORDER_CACHE_KEY, JSON.stringify(store));
}

function patchSongOrderCache(orderId: string, patch: SongOrderCacheEntry) {
  const store = loadSongOrderCache();
  store[orderId] = {
    ...(store[orderId] || {}),
    ...patch,
  };
  saveSongOrderCache(store);
  return store[orderId];
}

function getSongOrderCache(orderId: string) {
  return loadSongOrderCache()[orderId];
}

function extractQrToken(qrContent?: string) {
  if (!qrContent) {
    return undefined;
  }

  try {
    const parsed = new URL(
      qrContent,
      typeof window !== 'undefined' ? window.location.origin : 'http://localhost',
    );
    return (
      parsed.searchParams.get('token') ||
      parsed.searchParams.get('qrToken') ||
      undefined
    );
  } catch {
    return undefined;
  }
}

function toText(value: unknown, fallback = ''): string {
  if (typeof value === 'string') {
    return value;
  }
  if (value === null || value === undefined) {
    return fallback;
  }
  return String(value);
}

function toNumber(value: unknown, fallback = 0): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function buildAddressFromParts(parts: string[]) {
  return parts.filter(Boolean).join(' ');
}

function adaptAgentAddressResponse(
  payload: Partial<AgentAddressResponse> & Record<string, unknown>,
  fallback: {
    fullAddress?: string;
    latitude?: number;
    longitude?: number;
  } = {},
): AgentAddressResponse {
  const region = toText(payload.region);
  const province = toText(payload.province);
  const city = toText(payload.city);
  const district = toText(payload.district);
  const street = toText(payload.street);
  const postalCode = toText(payload.postal_code);
  const fullAddress =
    toText(payload.full_address) ||
    fallback.fullAddress ||
    buildAddressFromParts([region, province, city, district, street]);
  const locationSource =
    toText(payload.location_source) ||
    toText(payload.source) ||
    'USER_INPUT';
  const addressSource = toText(payload.address_source) || locationSource;
  const completionTips = Array.isArray(payload.completion_tips)
    ? payload.completion_tips
        .map((item) => toText(item).trim())
        .filter(Boolean)
    : [];

  return {
    full_address: fullAddress,
    region,
    province,
    city,
    district,
    street,
    postal_code: postalCode,
    longitude: toNumber(payload.longitude, fallback.longitude ?? 0),
    latitude: toNumber(payload.latitude, fallback.latitude ?? 0),
    location_source: locationSource,
    address_source: addressSource,
    validated:
      typeof payload.validated === 'boolean' ? payload.validated : Boolean(fullAddress),
    completion_tips: completionTips,
  };
}

function mergeSnapshotItems(
  items: PaymentSnapshot['items'],
  cachedItems?: PaymentSnapshot['items'],
): PaymentSnapshot['items'] {
  if (!cachedItems?.length) {
    return items;
  }

  return items.map((item, index) => {
    const matched =
      cachedItems.find(
        (candidate) =>
          (candidate.selected_new_sku &&
            candidate.selected_new_sku === item.selected_new_sku) ||
          (candidate.selected_old_sku &&
            candidate.selected_old_sku === item.selected_old_sku),
      ) || cachedItems[index];

    return matched ? { ...matched, ...item } : item;
  });
}

function adaptSongOrderView(
  payload: SongOrderView,
  cachedItems?: PaymentSnapshot['items'],
): PaymentOrderView {
  const cache = getSongOrderCache(payload.order_id);
  const snapshotItems = mergeSnapshotItems(
    payload.snapshot?.items || [],
    cachedItems || cache?.snapshot_items,
  );
  const qrToken =
    extractQrToken(payload.qr?.qr_content) ||
    cache?.qr_token ||
    null;

  patchSongOrderCache(payload.order_id, {
    qr_token: qrToken || undefined,
    snapshot_items: snapshotItems,
  });

  return {
    ...payload,
    snapshot: {
      ...payload.snapshot,
      items: snapshotItems,
    },
    qr_status: payload.qr_status || payload.qr?.qr_status || null,
    qr_expires_at: payload.qr_expires_at || payload.qr?.expires_at || null,
    qr_token: qrToken,
  };
}

function adaptSongPrepayResponse(payload: PaymentPrepayResponse): PaymentPrepayResponse {
  const tokenFromUrl = extractQrToken(payload.code_url || payload.h5_url);
  const tokenFromCache = getSongOrderCache(payload.order_id)?.qr_token;
  return {
    ...payload,
    trade_type: payload.trade_type === 'H5' ? 'H5' : 'NATIVE',
    qr_token: payload.qr_token || tokenFromUrl || tokenFromCache,
  };
}

function adaptSongElectronicOrder(
  payload: SongElectronicOrderPayload,
  orderId: string,
  _qrToken: string,
): ElectronicOrderResponse {
  const cachedItems = getSongOrderCache(orderId)?.snapshot_items || [];
  const sourceItems = payload.product_info?.items || [];
  const amountFen = payload.amount?.payable_total || 0;
  const totalQty =
    sourceItems.reduce((sum, item) => sum + Number(item.qty || 0), 0) || 1;
  const unitPrice = Number((amountFen / 100 / totalQty).toFixed(2));
  const timeline =
    payload.events?.map((event) => ({
      time: event.time || '',
      event: event.desc || '',
    })) || [];
  const paidAt =
    payload.events?.find((event) => (event.desc || '').includes('支付'))?.time || '';

  return {
    order_id: payload.order_id,
    trace_id: payload.trace_id || '',
    code: 'SUCCESS',
    status_code: 200,
    order_basic: {
      order_id: payload.order_id,
      status: payload.status || '',
      created_at: timeline[0]?.time || '',
    },
    items: sourceItems.map((item, index) => {
      const cached =
        cachedItems.find(
          (candidate) =>
            (candidate.selected_new_sku &&
              candidate.selected_new_sku === item.selected_new_sku) ||
            (candidate.selected_old_sku &&
              candidate.selected_old_sku === item.selected_old_sku),
        ) || cachedItems[index];
      return {
        sku:
          item.selected_new_sku ||
          item.selected_old_sku ||
          `SKU-${index + 1}`,
        name:
          cached?.selected_new_title ||
          cached?.selected_old_title ||
          item.selected_new_sku ||
          item.selected_old_sku ||
          '灯具',
        qty: Number(item.qty || 1),
        price: unitPrice,
      };
    }),
    payment: {
      total: Number((amountFen / 100).toFixed(2)),
      pay_status: payload.pay_status || '',
      paid_at: paidAt,
    },
    waybill: {
      waybill_id: payload.waybill?.waybill_id || '',
      status: payload.waybill?.status || '',
    },
    timeline,
  };
}

function adaptSongLogistics(
  orderId: string,
  payload: SongTrackPayload,
  waybillId?: string | null,
  status?: string | null,
): AgentLogisticsResponse {
  return {
    order_id: orderId,
    waybill_id: waybillId || '',
    status: status || '',
    trace_id: orderId,
    provider: 'song-backend',
    events: (payload.events || []).map((event) => ({
      time: event.time || '',
      event: event.desc || '',
      status: status || '',
    })),
    nodes: [],
  };
}

function getCheckoutFormPath(sessionId: string) {
  return `/agent/forms/checkout?session_id=${encodeURIComponent(sessionId)}`;
}

function getSongPaymentStatusPath(orderId: string, sync = true) {
  return `/payment/status?order_id=${encodeURIComponent(orderId)}&sync=${sync ? 'true' : 'false'}`;
}

function getSongTrackPath(orderId: string) {
  return `/track?order_id=${encodeURIComponent(orderId)}`;
}

function wait(ms: number) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

export const paymentApi = {
  getCheckoutForm(sessionId: string) {
    return requestAgent<AgentCheckoutFormResponse>(getCheckoutFormPath(sessionId));
  },

  async normalizeAddress(payload: Record<string, unknown>) {
    const result = await requestAgent<Partial<AgentAddressResponse> & Record<string, unknown>>(
      '/agent/addresses/normalize',
      {
        method: 'POST',
        body: payload,
      },
    );
    return adaptAgentAddressResponse(result, {
      fullAddress: toText(payload.full_address),
      latitude: toNumber(payload.latitude, 0),
      longitude: toNumber(payload.longitude, 0),
    });
  },

  async locateAddress(latitude: number, longitude: number, fullAddress?: string) {
    try {
      const result = await requestAgent<Partial<AgentAddressResponse> & Record<string, unknown>>(
        '/agent/addresses/locate',
        {
          method: 'POST',
          body: {
            latitude,
            longitude,
            full_address: fullAddress,
          },
        },
      );
      return adaptAgentAddressResponse(result, {
        fullAddress,
        latitude,
        longitude,
      });
    } catch {
      return adaptAgentAddressResponse(
        {
          full_address: fullAddress || '',
          latitude,
          longitude,
          location_source: 'BROWSER_GEOLOCATION',
          address_source: 'BROWSER_GEOLOCATION',
          validated: Boolean(fullAddress),
          completion_tips: ['定位结果不完整，请手动补充详细地址。'],
        },
        { fullAddress, latitude, longitude },
      );
    }
  },

  async createOrder(payload: PaymentCreateOrderRequest, idempotentKey: string) {
    const result = await requestSong<SongOrderView>('/create_order', {
      method: 'POST',
      body: payload,
      headers: {
        'Idempotent-Key': idempotentKey,
      },
    });

    return adaptSongOrderView(result, payload.items);
  },

  async getOrder(orderId: string) {
    const result = await requestSong<SongOrderView>(getSongPaymentStatusPath(orderId, false));
    return adaptSongOrderView(result);
  },

  async getPaymentStatus(orderId: string, sync = true) {
    const result = await requestSong<SongOrderView>(getSongPaymentStatusPath(orderId, sync));
    return adaptSongOrderView(result);
  },

  async prepay(payload: PaymentPrepayRequest, idempotentKey: string) {
    const result = await requestSong<PaymentPrepayResponse>('/pay/prepay', {
      method: 'POST',
      body: {
        ...payload,
        idempotent_key: idempotentKey,
      },
      headers: {
        'Idempotent-Key': idempotentKey,
      },
    });

    const adapted = adaptSongPrepayResponse(result);
    if (!adapted.qr_token) {
      const latestOrder = await this.getPaymentStatus(payload.order_id, false).catch(() => null);
      if (latestOrder?.qr_token) {
        adapted.qr_token = latestOrder.qr_token;
      }
    }
    return adapted;
  },

  async confirmPayment(orderId: string) {
    let latest = await this.getPaymentStatus(orderId, true);
    if (latest.payment_status === 'PAID') {
      return latest;
    }

    for (let attempt = 0; attempt < 4; attempt += 1) {
      await wait(1500);
      latest = await this.getPaymentStatus(orderId, true);
      if (latest.payment_status === 'PAID') {
        return latest;
      }
    }

    return latest;
  },

  async getElectronicOrder(orderId: string, qrToken: string) {
    const result = await requestSong<SongElectronicOrderPayload>(
      `/order-view?order_id=${encodeURIComponent(orderId)}&token=${encodeURIComponent(qrToken)}`,
    );
    return adaptSongElectronicOrder(result, orderId, qrToken);
  },

  async getLogistics(orderId: string) {
    const [track, order] = await Promise.all([
      requestSong<SongTrackPayload>(getSongTrackPath(orderId)),
      this.getPaymentStatus(orderId, false).catch(() => null),
    ]);

    return adaptSongLogistics(
      orderId,
      track,
      order?.waybill_id || '',
      order?.waybill_status || '',
    );
  },

  async getLogisticsMap(orderId: string) {
    const order = await this.getPaymentStatus(orderId, false).catch(() => null);
    const hasLocation =
      order &&
      typeof order.receiver_longitude === 'number' &&
      typeof order.receiver_latitude === 'number';

    return {
      order_id: orderId,
      waybill_id: order?.waybill_id || '',
      provider: 'song-backend',
      nodes: hasLocation
        ? [
            {
              lng: Number(order.receiver_longitude),
              lat: Number(order.receiver_latitude),
              label: '收货地址',
              status: order?.waybill_status || '',
            },
          ]
        : [],
      route: hasLocation
        ? [[Number(order.receiver_longitude), Number(order.receiver_latitude)]]
        : [],
    } satisfies AgentLogisticsMapResponse;
  },
};
