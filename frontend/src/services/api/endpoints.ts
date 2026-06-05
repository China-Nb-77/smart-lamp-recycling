import type {
  AdvanceWaybillResponse,
  AskRequest,
  AskResponse,
  CreateWaybillRequest,
  CreateWaybillResponse,
  ElectronicOrderResponse,
  GenerateQrRequest,
  GenerateQrResponse,
  LampInfo,
  LampSearchRequest,
  LampSearchResponse,
  OpenTicketRequest,
  OrderWaybillResponse,
  PaymentSuccessRequest,
  PaymentSuccessResponse,
  QrErrorResponse,
  StatusMessageResponse,
  TicketResponse,
  TrackResponse,
  TriggerExceptionRequest,
  TriggerExceptionResponse,
} from '../../types/api';
import { request } from './client';

// Keep snake_case here to match the audited Spring Boot request/response fields exactly.
export const api = {
  ask(payload: AskRequest) {
    return request<AskResponse>('/api/qna/ask', {
      method: 'POST',
      body: payload,
    });
  },
  listLamps() {
    return request<LampInfo[]>('/api/lamp/list');
  },
  searchLamp(payload: LampSearchRequest) {
    return request<LampSearchResponse>('/api/lamp/search', {
      method: 'POST',
      body: payload,
    });
  },
  addLamp(payload: LampInfo) {
    return request<StatusMessageResponse>('/api/lamp/add', {
      method: 'POST',
      body: payload,
    });
  },
  deleteLamp(sku: string) {
    return request<StatusMessageResponse>(`/api/lamp/${encodeURIComponent(sku)}`, {
      method: 'DELETE',
    });
  },
  generateQr(payload: GenerateQrRequest) {
    return request<GenerateQrResponse>('/api/qr/generate', {
      method: 'POST',
      body: payload,
    });
  },
  getElectronicOrder(order_id: string, qr_token: string) {
    return request<ElectronicOrderResponse>(
      `/api/order/${encodeURIComponent(order_id)}/electronic?qrToken=${encodeURIComponent(
        qr_token,
      )}`,
    );
  },
  getQrError(code: string) {
    return request<QrErrorResponse>(`/api/qr/error?code=${encodeURIComponent(code)}`);
  },
  createWaybill(payload: CreateWaybillRequest) {
    return request<CreateWaybillResponse>('/api/waybill', {
      method: 'POST',
      body: payload,
    });
  },
  trackWaybill(waybill_id: string) {
    return request<TrackResponse>(
      `/api/track?waybillId=${encodeURIComponent(waybill_id)}`,
    );
  },
  openTicket(payload: OpenTicketRequest) {
    return request<TicketResponse>('/api/ticket', {
      method: 'POST',
      body: payload,
    });
  },
  getWaybillByOrder(order_id: string) {
    return request<OrderWaybillResponse>(
      `/api/order/${encodeURIComponent(order_id)}/waybill`,
    );
  },
  advanceWaybill(waybill_id: string) {
    return request<AdvanceWaybillResponse>(
      `/api/waybill/${encodeURIComponent(waybill_id)}/advance`,
      {
        method: 'POST',
      },
    );
  },
  paymentSuccess(payload: PaymentSuccessRequest) {
    return request<PaymentSuccessResponse>('/api/payment/success', {
      method: 'POST',
      body: payload,
    });
  },
  triggerException(payload: TriggerExceptionRequest) {
    return request<TriggerExceptionResponse>('/api/exception/trigger', {
      method: 'POST',
      body: payload,
    });
  },
};
