import type { ChatCard } from './chat';
import type { components } from '../generated/api-types';

type ConversationSchema = components['schemas']['ConversationResponse'];
type SelectionSchema = components['schemas']['RecommendationSelectResponse'];
type CheckoutSchema = components['schemas']['CheckoutFormResponse'];
type AddressSchema = components['schemas']['AddressResponse'];
type LogisticsSchema = components['schemas']['LogisticsResponse'];
type LogisticsMapSchema = components['schemas']['LogisticsMapResponse'];

export type AgentConversationMessage = {
  role: 'assistant' | 'user' | 'system';
  text: string;
  suggestions?: string[];
  cards?: ChatCard[];
};

export type AgentConversationResponse = Omit<ConversationSchema, 'messages' | 'state'> & {
  session_id: string;
  state: string;
  messages: AgentConversationMessage[];
};

export type AgentSelectionResponse = Omit<SelectionSchema, 'draft' | 'selected'> & {
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

export type AgentCheckoutFormResponse = Omit<CheckoutSchema, 'form_schema' | 'selection' | 'summary'> & {
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

export type AgentAddressResponse = AddressSchema;
export type AgentLogisticsResponse = Omit<LogisticsSchema, 'events' | 'nodes'> & {
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

export type AgentLogisticsMapResponse = Omit<LogisticsMapSchema, 'nodes' | 'route'> & {
  nodes: Array<{
    lng: number;
    lat: number;
    label: string;
    status: string;
  }>;
  route: number[][];
};

