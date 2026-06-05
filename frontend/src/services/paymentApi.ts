import { ApiError, extractErrorMessage } from './api/client';
import { visionBaseUrl } from './api/base-url';
import { findServerSessionByRemoteId, getServerSessionBinding } from './chatFlowStore';
import type {
  PaymentCreateOrderRequest,
  PaymentOrderView,
  PaymentPrepayRequest,
  PaymentPrepayResponse,
} from '../modules/payment/types';
import type {
  AgentAddressResponse,
  AgentCheckoutFormResponse,
  AgentLogisticsMapResponse,
  AgentLogisticsResponse,
} from '../types/agent';
import type { ElectronicOrderResponse } from '../types/api';

type RequestOptions = {
  method?: 'GET' | 'POST';
  body?: unknown;
  headers?: Record<string, string>;
};

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

function sessionAuthByRemoteId(remoteSessionId?: string) {
  if (!remoteSessionId) {
    return undefined;
  }
  const binding = findServerSessionByRemoteId(remoteSessionId);
  if (!binding) {
    return undefined;
  }
  return {
    Authorization: `Bearer ${binding.session_token}`,
  };
}

function adaptPrepayResponse(payload: {
  order_id: string;
  trace_id: string;
  qr_token: string;
  code_url: string;
  h5_url: string;
  expire_at: string;
  payable_total: number;
  currency: string;
  amount_unit: string;
  trade_type: string;
}): PaymentPrepayResponse {
  return {
    order_id: payload.order_id,
    trace_id: payload.trace_id,
    amount: payload.payable_total,
    payable_total: payload.payable_total,
    amount_currency: payload.currency,
    amount_unit: payload.amount_unit,
    payment_status: 'UNPAID',
    pay_status: 'UNPAID',
    trade_type: payload.trade_type === 'H5' ? 'H5' : 'NATIVE',
    code_url: payload.code_url,
    h5_url: payload.h5_url,
    time_expire: payload.expire_at,
    qr_token: payload.qr_token,
  };
}

export const paymentApi = {
  getCheckoutForm(localSessionId: string) {
    const binding = getServerSessionBinding(localSessionId) || null;
    return requestAgent<AgentCheckoutFormResponse>(
      `/agent/forms/checkout?session_id=${encodeURIComponent(binding?.session_id || localSessionId)}`,
      {
        headers: binding
          ? {
              Authorization: `Bearer ${binding.session_token}`,
            }
          : undefined,
      },
    );
  },

  normalizeAddress(payload: Record<string, unknown>) {
    return requestAgent<AgentAddressResponse>('/agent/addresses/normalize', {
      method: 'POST',
      body: payload,
    });
  },

  locateAddress(latitude: number, longitude: number, fullAddress?: string) {
    return requestAgent<AgentAddressResponse>('/agent/addresses/locate', {
      method: 'POST',
      body: {
        latitude,
        longitude,
        full_address: fullAddress,
      },
    });
  },

  createOrder(payload: PaymentCreateOrderRequest, _idempotentKey: string) {
    return requestAgent<PaymentOrderView>('/agent/orders', {
      method: 'POST',
      body: payload,
      headers: sessionAuthByRemoteId(payload.session_id),
    });
  },

  getOrder(orderId: string) {
    return requestAgent<PaymentOrderView>(`/agent/orders/${encodeURIComponent(orderId)}?sync=false`);
  },

  getPaymentStatus(orderId: string, sync = true) {
    return requestAgent<PaymentOrderView>(
      `/agent/orders/${encodeURIComponent(orderId)}?sync=${sync ? 'true' : 'false'}`,
    );
  },

  async prepay(payload: PaymentPrepayRequest, idempotentKey: string) {
    const response = await requestAgent<{
      order_id: string;
      trace_id: string;
      qr_token: string;
      code_url: string;
      h5_url: string;
      expire_at: string;
      payable_total: number;
      currency: string;
      amount_unit: string;
      trade_type: string;
    }>(`/agent/orders/${encodeURIComponent(payload.order_id)}/qr`, {
      method: 'POST',
      body: {
        trade_type: payload.trade_type || 'NATIVE',
        return_url: payload.return_url,
        idempotent_key: idempotentKey,
      },
    });
    return adaptPrepayResponse(response);
  },

  async confirmPayment(orderId: string) {
    let latest = await this.getPaymentStatus(orderId, true);
    if (latest.payment_status === 'PAID') {
      return latest;
    }

    for (let attempt = 0; attempt < 4; attempt += 1) {
      await new Promise((resolve) => window.setTimeout(resolve, 1500));
      latest = await this.getPaymentStatus(orderId, true);
      if (latest.payment_status === 'PAID') {
        return latest;
      }
    }

    return latest;
  },

  getElectronicOrder(orderId: string, qrToken: string) {
    return requestAgent<ElectronicOrderResponse>(
      `/agent/orders/${encodeURIComponent(orderId)}/electronic?qrToken=${encodeURIComponent(qrToken)}`,
    );
  },

  getLogistics(orderId: string) {
    return requestAgent<AgentLogisticsResponse>(
      `/agent/orders/${encodeURIComponent(orderId)}/logistics`,
    );
  },

  getLogisticsMap(orderId: string) {
    return requestAgent<AgentLogisticsMapResponse>(
      `/agent/orders/${encodeURIComponent(orderId)}/logistics-map`,
    );
  },
};
