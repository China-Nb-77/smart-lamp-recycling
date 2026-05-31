import type {
  AdvanceWaybillResponse,
  CreateWaybillResponse,
  ElectronicOrderResponse,
  GenerateQrResponse,
  LampInfo,
  PaymentSuccessResponse,
  QrErrorResponse,
  TicketResponse,
  TrackResponse,
} from './api';
import type {
  VisionQuoteResponse,
  VisionRecommendationResponse,
} from './vision';

export type PreferenceFieldKey = 'install_type' | 'space' | 'budget_level';

export type PreferenceFormSubmission = {
  session_id: string;
  install_type?: string;
  space?: string;
  budget_level?: string;
  note?: string;
};

export type CheckoutPrefill = {
  name?: string;
  phone?: string;
  full_address?: string;
  street?: string;
  longitude?: number;
  latitude?: number;
  selected_new_sku?: string;
  selected_new_title?: string;
  selected_new_image_path?: string;
  selected_new_kind?: string;
  qty?: number;
  selection_summary?: string;
};

export type ChatCard =
  | {
      type: 'uploaded_image';
      data: {
        image_url: string;
        alt: string;
      };
    }
  | {
      type: 'lamp';
      data: LampInfo;
    }
  | {
      type: 'qr';
      data: GenerateQrResponse & {
        order_id: string;
      };
    }
  | {
      type: 'electronic_order';
      data: ElectronicOrderResponse;
    }
  | {
      type: 'waybill';
      data: TrackResponse & {
        order_id?: string;
      };
    }
  | {
      type: 'waybill_advance';
      data: AdvanceWaybillResponse;
    }
  | {
      type: 'ticket';
      data: TicketResponse;
    }
  | {
      type: 'payment';
      data: PaymentSuccessResponse & {
        order_id: string;
      };
    }
  | {
      type: 'error';
      data: QrErrorResponse;
    }
  | {
      type: 'create_waybill';
      data: CreateWaybillResponse & {
        order_id: string;
      };
    }
  | {
      type: 'recycle_quote';
      data: VisionQuoteResponse;
    }
  | {
      type: 'preference_form';
      data: {
        session_id: string;
        title: string;
        note?: string;
        submit_label: string;
        fields: Array<{
          key: PreferenceFieldKey;
          label: string;
          value?: string;
          options: Array<{
            value: string;
            label: string;
          }>;
        }>;
      };
    }
  | {
      type: 'replacement_recommendations';
      data: VisionRecommendationResponse;
    }
  | {
      type: 'checkout_form';
      data: {
        session_id: string;
        prefill?: CheckoutPrefill;
      };
    };

export type RetryAction =
  | {
      kind: 'ask';
      payload: {
        question: string;
        session_id: string;
      };
    }
  | {
      kind: 'fetch-waybill';
      payload: {
        order_id: string;
      };
    };

export type ChatMessage = {
  id: string;
  role: 'user' | 'assistant' | 'system';
  text: string;
  created_at: string;
  status: 'ready' | 'loading' | 'error';
  error_message?: string;
  retry_action?: RetryAction;
  cards?: ChatCard[];
  suggestions?: string[];
};

export type ChatSession = {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  messages: ChatMessage[];
};
