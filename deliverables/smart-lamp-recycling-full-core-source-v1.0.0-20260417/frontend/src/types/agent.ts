import type { ChatCard } from './chat';

export type AgentConversationMessage = {
  role: 'assistant' | 'user' | 'system';
  text: string;
  suggestions?: string[];
  cards?: ChatCard[];
};

export type AgentConversationResponse = {
  session_id: string;
  state: string;
  messages: AgentConversationMessage[];
};

export type AgentSelectionResponse = {
  session_id: string;
  selected: {
    sku_id: string;
    title: string;
    image_path?: string;
    visual_style?: string;
    base_price: number;
  };
  draft: {
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
  next_action: {
    type: string;
    form_schema_url: string;
  };
};

export type AgentFormFieldOption = {
  value: string;
  label: string;
};

export type AgentFormField = {
  key: string;
  label: string;
  component: 'input' | 'textarea' | 'select';
  type?: string;
  required?: boolean;
  action?: string;
  placeholder?: string;
  options?: AgentFormFieldOption[];
};

export type AgentCheckoutFormResponse = {
  session_id: string;
  schema: {
    title: string;
    submit_label: string;
    fields: AgentFormField[];
  };
  defaults: Record<string, string>;
  selection: {
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
  summary: {
    old_lamp: string;
    new_lamp: string;
    recycle_quote: number;
    currency: string;
    payable_total_fen: number;
    todo: string;
  };
};

export type AgentAddressResponse = {
  full_address: string;
  region: string;
  province: string;
  city: string;
  district: string;
  street: string;
  postal_code: string;
  longitude: number;
  latitude: number;
  location_source: string;
  address_source: string;
  validated: boolean;
  completion_tips: string[];
};

export type AgentLogisticsResponse = {
  order_id: string;
  waybill_id: string;
  status: string;
  trace_id: string;
  provider: string;
  events: Array<{
    time: string;
    event: string;
    status: string;
  }>;
  nodes: Array<{
    lng: number;
    lat: number;
    label: string;
    status: string;
  }>;
};

export type AgentLogisticsMapResponse = {
  order_id: string;
  waybill_id: string;
  provider: string;
  nodes: Array<{
    lng: number;
    lat: number;
    label: string;
    status: string;
  }>;
  route: number[][];
};
