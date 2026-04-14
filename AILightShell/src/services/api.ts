import {API_BASE_URL, H5_BASE_URL} from '../config/env';
import {saveLatestOrder} from '../store/session';

type RequestConfig = {
  path: string;
  method?: 'GET' | 'POST';
  body?: unknown;
  headers?: Record<string, string>;
};

async function request<T>({
  path,
  method = 'GET',
  body,
  headers = {},
}: RequestConfig): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...headers,
    },
    body: body ? JSON.stringify(body) : undefined,
  });

  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload?.message || '请求失败');
  }

  return payload?.data ?? payload;
}

export async function createOrderFlow() {
  const traceId = `rn_trace_${Date.now()}`;
  const quote = await request<any>({
    method: 'POST',
    path: '/quote',
    body: {
      trace_id: traceId,
      selected_old_sku: 'OLD_001',
      user_id: 'rn_user_001',
      name: 'RN Tester',
      phone: '13800000000',
      full_address: 'Shanghai Pudong Test Rd 100',
      region: 'shanghai',
      city: 'Shanghai',
      district: 'Pudong',
      longitude: 121.544,
      latitude: 31.221,
      location_source: 'RN_SHELL',
      address_source: 'NATIVE_FORM',
      qty: 1,
    },
  });

  const selectedNewSku =
    quote?.selected_new_sku || quote?.options?.[0]?.new_sku || 'NEW-SKU-101';
  const payableTotal = quote?.payable_total || 1990;

  const order = await request<any>({
    method: 'POST',
    path: '/create_order',
    body: {
      trace_id: traceId,
      user: {
        user_id: 'rn_user_001',
        name: 'RN Tester',
        phone: '13800000000',
      },
      address: {
        full_address: 'Shanghai Pudong Test Rd 100',
        region: 'shanghai',
        city: 'Shanghai',
        district: 'Pudong',
        longitude: 121.544,
        latitude: 31.221,
        location_source: 'RN_SHELL',
        address_source: 'NATIVE_FORM',
      },
      items: [
        {
          selected_old_sku: 'OLD_001',
          selected_new_sku: selectedNewSku,
          qty: 1,
        },
      ],
      payable_total: payableTotal,
      currency: 'CNY',
      amount_unit: 'FEN',
      access_domain: H5_BASE_URL,
    },
    headers: {
      'Idempotent-Key': `rn-order-${traceId}`,
    },
  });

  await saveLatestOrder(order);
  return {
    quote,
    order,
  };
}

export async function createPrepay(orderId: string) {
  return request<any>({
    method: 'POST',
    path: '/pay/prepay',
    body: {
      trace_id: `rn_prepay_${Date.now()}`,
      order_id: orderId,
      amount: 1990,
      idempotent_key: `rn-prepay-${orderId}`,
      openid: 'rn_openid_demo',
    },
    headers: {
      'Idempotent-Key': `rn-prepay-${orderId}`,
    },
  });
}

export async function mockNotify(orderId: string) {
  return request<any>({
    method: 'POST',
    path: '/wechat/notify',
    body: {
      order_id: orderId,
      transaction_id: `rn_txn_${Date.now()}`,
      status: 'SUCCESS',
      paid_amount_fen: 1990,
      paid_at: new Date().toISOString(),
    },
  });
}
