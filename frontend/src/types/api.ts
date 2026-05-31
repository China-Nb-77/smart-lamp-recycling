import type { components } from '../generated/api-types';

type ElectronicOrderSchema = components['schemas']['ElectronicOrderResponse'];

export type AskRequest = {
  question: string;
  session_id?: string;
  image_url?: string;
  recognized_sku?: string;
};

export type AskResponse = {
  trace_id: string;
  answer: string;
  session_id: string;
};

export type LampInfo = {
  sku: string;
  name: string;
  description: string;
};

export type LampSearchRequest = {
  question: string;
};

export type LampSearchResponse = Partial<LampInfo>;

export type StatusMessageResponse = {
  status: string;
  message: string;
};

export type GenerateQrRequest = {
  order_id: string;
};

export type GenerateQrResponse = {
  trace_id: string;
  qr_token: string;
  qr_url: string;
  expire_at: string;
};

export type ElectronicOrderBasic = {
  order_id: string;
  status: string;
  created_at: string;
};

export type ElectronicOrderItem = {
  sku: string;
  name: string;
  qty: number;
  price: number;
};

export type ElectronicOrderPayment = {
  total: number;
  pay_status: string;
  paid_at: string;
};

export type ElectronicOrderWaybill = {
  waybill_id: string;
  status: string;
};

export type ElectronicOrderTimelineEvent = {
  time: string;
  event: string;
};

export type ElectronicOrderResponse = Omit<
  ElectronicOrderSchema,
  'order_basic' | 'items' | 'payment' | 'waybill' | 'timeline'
> & {
  order_id: string;
  trace_id: string;
  code: string;
  status_code: number;
  order_basic?: ElectronicOrderBasic;
  items?: ElectronicOrderItem[];
  payment?: ElectronicOrderPayment;
  waybill?: ElectronicOrderWaybill;
  timeline?: ElectronicOrderTimelineEvent[];
};

export type QrErrorResponse = {
  trace_id: string;
  error_code: string;
  message: string;
  suggestion: string;
};

export type CreateWaybillRequest = {
  order_id: string;
};

export type CreateWaybillResponse = {
  waybill_id: string;
  status: string;
  trace_id: string;
};

export type TrackEvent = {
  eventTime: string;
  status: string;
  desc: string;
};

export type TrackResponse = {
  waybill_id: string;
  status: string;
  events: TrackEvent[];
  trace_id: string;
};

export type OpenTicketRequest = {
  order_id: string;
  waybill_id?: string;
  reason: string;
  detail?: string;
};

export type TicketResponse = {
  ticket_id: string;
  status: string;
  reason: string;
  trace_id: string;
};

export type OrderWaybillResponse = {
  order_id: string;
  waybill_id: string | null;
  status: string;
  trace_id: string;
};

export type AdvanceWaybillResponse = {
  waybill_id: string;
  status?: string;
  message: string;
  trace_id: string;
};

export type PaymentSuccessRequest = {
  order_id: string;
};

export type PaymentSuccessResponse = {
  code: string;
  message: string;
  waybill_id: string;
  trace_id: string;
};

export type TriggerExceptionRequest = {
  type: string;
  order_id: string;
  detail?: string;
};

export type TriggerExceptionResponse = TicketResponse;

export const ticket_reason_options = [
  '识别不确定',
  '地址不全',
  '支付异常',
  '轨迹异常',
  '其他',
] as const;

export type TicketReason = (typeof ticket_reason_options)[number];

export const exception_type_options = [
  'LOW_CONFIDENCE',
  'ADDRESS_INCOMPLETE',
  'PAYMENT_FAILED',
  'TRACK_EMPTY',
] as const;

export type ExceptionType = (typeof exception_type_options)[number];
