import type { TicketReason } from '../../types/api';

export type DebugEndpoint = {
  id: string;
  title: string;
  method: 'GET' | 'POST' | 'DELETE';
  pathTemplate: string;
  fields: Array<{
    key: string;
    label: string;
    placeholder: string;
    kind?: 'text' | 'textarea';
  }>;
  buildPath: (values: Record<string, string>) => string;
  buildBody?: (values: Record<string, string>) => unknown;
};

export const debugEndpoints: DebugEndpoint[] = [
  {
    id: 'qna-ask',
    title: 'POST /api/qna/ask',
    method: 'POST',
    pathTemplate: '/api/qna/ask',
    fields: [
      { key: 'question', label: 'question', placeholder: '今天有什么可以帮到你？' },
      { key: 'session_id', label: 'session_id', placeholder: 'local-session-1' },
      { key: 'recognized_sku', label: 'recognized_sku', placeholder: 'SKU001' },
    ],
    buildPath: () => '/api/qna/ask',
    buildBody: (values) => ({
      question: values.question,
      session_id: values.session_id,
      recognized_sku: values.recognized_sku,
    }),
  },
  {
    id: 'lamp-list',
    title: 'GET /api/lamp/list',
    method: 'GET',
    pathTemplate: '/api/lamp/list',
    fields: [],
    buildPath: () => '/api/lamp/list',
  },
  {
    id: 'lamp-search',
    title: 'POST /api/lamp/search',
    method: 'POST',
    pathTemplate: '/api/lamp/search',
    fields: [
      { key: 'question', label: 'question', placeholder: '推荐适合阅读的台灯' },
    ],
    buildPath: () => '/api/lamp/search',
    buildBody: (values) => ({
      question: values.question,
    }),
  },
  {
    id: 'lamp-add',
    title: 'POST /api/lamp/add',
    method: 'POST',
    pathTemplate: '/api/lamp/add',
    fields: [
      { key: 'sku', label: 'sku', placeholder: 'SKU004' },
      { key: 'name', label: 'name', placeholder: '智能吊灯 D' },
      { key: 'description', label: 'description', placeholder: '描述', kind: 'textarea' },
    ],
    buildPath: () => '/api/lamp/add',
    buildBody: (values) => ({
      sku: values.sku,
      name: values.name,
      description: values.description,
    }),
  },
  {
    id: 'lamp-delete',
    title: 'DELETE /api/lamp/{sku}',
    method: 'DELETE',
    pathTemplate: '/api/lamp/{sku}',
    fields: [{ key: 'sku', label: 'sku', placeholder: 'SKU001' }],
    buildPath: (values) => `/api/lamp/${encodeURIComponent(values.sku)}`,
  },
  {
    id: 'qr-generate',
    title: 'POST /api/qr/generate',
    method: 'POST',
    pathTemplate: '/api/qr/generate',
    fields: [{ key: 'order_id', label: 'order_id', placeholder: 'ORDER_1001' }],
    buildPath: () => '/api/qr/generate',
    buildBody: (values) => ({
      order_id: values.order_id,
    }),
  },
  {
    id: 'order-electronic',
    title: 'GET /api/order/{orderId}/electronic',
    method: 'GET',
    pathTemplate: '/api/order/{orderId}/electronic?qrToken=',
    fields: [
      { key: 'order_id', label: 'order_id', placeholder: 'ORDER_1001' },
      { key: 'qr_token', label: 'qr_token', placeholder: 'uuid-token' },
    ],
    buildPath: (values) =>
      `/api/order/${encodeURIComponent(values.order_id)}/electronic?qrToken=${encodeURIComponent(
        values.qr_token,
      )}`,
  },
  {
    id: 'qr-error',
    title: 'GET /api/qr/error?code=',
    method: 'GET',
    pathTemplate: '/api/qr/error?code=',
    fields: [{ key: 'code', label: 'code', placeholder: '401' }],
    buildPath: (values) => `/api/qr/error?code=${encodeURIComponent(values.code)}`,
  },
  {
    id: 'waybill-create',
    title: 'POST /api/waybill',
    method: 'POST',
    pathTemplate: '/api/waybill',
    fields: [{ key: 'order_id', label: 'order_id', placeholder: 'ORDER_1001' }],
    buildPath: () => '/api/waybill',
    buildBody: (values) => ({
      order_id: values.order_id,
    }),
  },
  {
    id: 'track',
    title: 'GET /api/track?waybillId=',
    method: 'GET',
    pathTemplate: '/api/track?waybillId=',
    fields: [{ key: 'waybill_id', label: 'waybill_id', placeholder: 'WB123456' }],
    buildPath: (values) => `/api/track?waybillId=${encodeURIComponent(values.waybill_id)}`,
  },
  {
    id: 'ticket',
    title: 'POST /api/ticket',
    method: 'POST',
    pathTemplate: '/api/ticket',
    fields: [
      { key: 'order_id', label: 'order_id', placeholder: 'ORDER_1001' },
      { key: 'waybill_id', label: 'waybill_id', placeholder: 'WB123456' },
      {
        key: 'reason',
        label: 'reason',
        placeholder: '识别不确定 / 地址不全 / 支付异常 / 轨迹异常 / 其他',
      },
      { key: 'detail', label: 'detail', placeholder: '问题详情', kind: 'textarea' },
    ],
    buildPath: () => '/api/ticket',
    buildBody: (values) => ({
      order_id: values.order_id,
      waybill_id: values.waybill_id,
      reason: (values.reason || '其他') as TicketReason,
      detail: values.detail,
    }),
  },
  {
    id: 'order-waybill',
    title: 'GET /api/order/{orderId}/waybill',
    method: 'GET',
    pathTemplate: '/api/order/{orderId}/waybill',
    fields: [{ key: 'order_id', label: 'order_id', placeholder: 'ORDER_1001' }],
    buildPath: (values) => `/api/order/${encodeURIComponent(values.order_id)}/waybill`,
  },
  {
    id: 'waybill-advance',
    title: 'POST /api/waybill/{waybillId}/advance',
    method: 'POST',
    pathTemplate: '/api/waybill/{waybillId}/advance',
    fields: [{ key: 'waybill_id', label: 'waybill_id', placeholder: 'WB123456' }],
    buildPath: (values) =>
      `/api/waybill/${encodeURIComponent(values.waybill_id)}/advance`,
  },
  {
    id: 'payment-success',
    title: 'POST /api/payment/success',
    method: 'POST',
    pathTemplate: '/api/payment/success',
    fields: [{ key: 'order_id', label: 'order_id', placeholder: 'ORDER_1001' }],
    buildPath: () => '/api/payment/success',
    buildBody: (values) => ({
      order_id: values.order_id,
    }),
  },
  {
    id: 'exception-trigger',
    title: 'POST /api/exception/trigger',
    method: 'POST',
    pathTemplate: '/api/exception/trigger',
    fields: [
      {
        key: 'type',
        label: 'type',
        placeholder: 'LOW_CONFIDENCE / ADDRESS_INCOMPLETE / PAYMENT_FAILED / TRACK_EMPTY',
      },
      { key: 'order_id', label: 'order_id', placeholder: 'ORDER_1001' },
      { key: 'detail', label: 'detail', placeholder: '异常详情', kind: 'textarea' },
    ],
    buildPath: () => '/api/exception/trigger',
    buildBody: (values) => ({
      type: values.type,
      order_id: values.order_id,
      detail: values.detail,
    }),
  },
];
