export type PaymentCreateOrderRequest = {
  session_id?: string;
  trace_id?: string;
  user: {
    user_id?: string;
    name: string;
    phone: string;
  };
  address: {
    full_address: string;
    region?: string;
    province?: string;
    city?: string;
    district?: string;
    street?: string;
    postal_code?: string;
    longitude?: number;
    latitude?: number;
    location_source?: string;
    address_source?: string;
  };
  items: Array<{
    selected_old_sku?: string;
    selected_old_title?: string;
    selected_old_image_path?: string;
    selected_old_kind?: string;
    selected_new_sku?: string;
    selected_new_title?: string;
    selected_new_image_path?: string;
    selected_new_kind?: string;
    qty: number;
  }>;
  payable_total: number;
  currency?: string;
  amount_unit?: string;
  access_domain?: string;
};

export type PaymentSnapshot = {
  trace_id?: string;
  payable_total: number;
  currency: string;
  amount_unit: string;
  access_domain?: string;
  user?: {
    user_id?: string;
    name?: string;
    phone?: string;
  };
  address?: {
    full_address?: string;
    region?: string;
    province?: string;
    city?: string;
    district?: string;
    street?: string;
    postal_code?: string;
    longitude?: number;
    latitude?: number;
    location_source?: string;
    address_source?: string;
  };
  items: Array<{
    selected_old_sku?: string;
    selected_old_title?: string;
    selected_old_image_path?: string;
    selected_old_kind?: string;
    selected_new_sku?: string;
    selected_new_title?: string;
    selected_new_image_path?: string;
    selected_new_kind?: string;
    qty: number;
  }>;
};

export type PaymentOrderView = {
  order_id: string;
  trace_id?: string;
  user_id?: string | null;
  contact_name?: string | null;
  contact_phone?: string | null;
  address_region?: string | null;
  full_address?: string | null;
  receiver_longitude?: number | null;
  receiver_latitude?: number | null;
  location_source?: string | null;
  address_source?: string | null;
  access_domain?: string | null;
  status: string;
  order_status: string;
  payment_status: string;
  pay_status: string;
  payable_total: number;
  amount_currency: string;
  amount_unit: string;
  snapshot: PaymentSnapshot;
  paid_amount_total?: number | null;
  paid_at?: string | null;
  qr_status?: string | null;
  qr_expires_at?: string | null;
  waybill_id?: string | null;
  waybill_status?: string | null;
  prepay_id?: string | null;
  transaction_id?: string | null;
  payment_idempotent_key?: string | null;
  payment_trade_type?: string | null;
  payment_code_url?: string | null;
  payment_h5_url?: string | null;
  payment_updated_at?: string | null;
  wechat_pay_enabled?: boolean;
  wechat_pay_configured?: boolean;
  qr_token?: string | null;
  recycle_progress?: Array<{
    key: string;
    label: string;
    done: boolean;
  }>;
  shipment_progress?: Array<{
    key: string;
    label: string;
    done: boolean;
  }>;
  mock_mode?: boolean;
};

export type CheckoutDraft = {
  selected_old_sku?: string;
  selected_old_title?: string;
  selected_old_image_path?: string;
  selected_old_kind?: string;
  selected_new_sku: string;
  selected_new_title: string;
  selected_new_image_path?: string;
  selected_new_kind?: string;
  selected_new_price: number;
  recycle_quote?: number;
  currency?: string;
  qty?: number;
};

export type PaymentTradeType = 'NATIVE' | 'H5';

export type PaymentPrepayRequest = {
  trace_id?: string;
  order_id: string;
  amount?: number;
  idempotent_key?: string;
  openid?: string;
  trade_type?: PaymentTradeType;
  payer_client_ip?: string;
  return_url?: string;
  app_name?: string;
  app_url?: string;
};

export type PaymentPrepayResponse = {
  order_id: string;
  trace_id?: string;
  idempotent_key?: string;
  amount: number;
  payable_total: number;
  amount_currency: string;
  amount_unit: string;
  payment_status: string;
  pay_status: string;
  trade_type: PaymentTradeType;
  code_url?: string;
  h5_url?: string;
  return_url?: string | null;
  time_expire?: string;
  qr_token?: string;
};

export type PaymentTrackResponse = {
  order_id: string;
  events: Array<{
    time: string;
    event: string;
  }>;
};

export type PaymentFormState = {
  session_id: string;
  trace_id: string;
  user_id: string;
  name: string;
  gender: string;
  phone: string;
  full_address: string;
  region: string;
  province: string;
  city: string;
  district: string;
  street: string;
  postal_code: string;
  longitude: string;
  latitude: string;
  location_source: string;
  address_source: string;
  selected_old_sku: string;
  selected_new_sku: string;
  qty: string;
  payable_total: string;
};
