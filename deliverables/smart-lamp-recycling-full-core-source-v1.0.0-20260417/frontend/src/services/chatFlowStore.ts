import type { CheckoutDraft } from '../modules/payment/types';
import type {
  VisionRecommendation,
  VisionRecommendationResponse,
  VisionQuoteResponse,
} from '../types/vision';
import { readJson, writeJson } from './storage/local-store';

const CHAT_FLOW_STORAGE_KEY = 'ai-light.chat.flow';

export type ChatFlowPreferences = Partial<
  Record<'install_type' | 'budget_level' | 'material' | 'space', string>
>;

export type ChatFlowSessionState = {
  quote?: VisionQuoteResponse;
  preferences?: ChatFlowPreferences;
  recommendations?: VisionRecommendationResponse;
  selected_sku?: string;
  draft?: CheckoutDraft;
};

type ChatFlowStore = Record<string, ChatFlowSessionState>;

function loadStore() {
  return readJson<ChatFlowStore>(CHAT_FLOW_STORAGE_KEY, {});
}

function saveStore(store: ChatFlowStore) {
  writeJson(CHAT_FLOW_STORAGE_KEY, store);
}

export function getChatFlowSession(sessionId: string) {
  const store = loadStore();
  return store[sessionId];
}

export function patchChatFlowSession(
  sessionId: string,
  updater: (current: ChatFlowSessionState) => ChatFlowSessionState,
) {
  const store = loadStore();
  const next = updater(store[sessionId] || {});
  store[sessionId] = next;
  saveStore(store);
  return next;
}

export function clearChatFlowSession(sessionId: string) {
  const store = loadStore();
  delete store[sessionId];
  saveStore(store);
}

export function selectRecommendationFromFlow(sessionId: string, skuId?: string) {
  const state = getChatFlowSession(sessionId);
  const recommendations = state?.recommendations?.recommendations || [];
  if (!recommendations.length) {
    return null;
  }
  if (!skuId) {
    return recommendations[0];
  }
  return recommendations.find((item) => item.sku_id === skuId) || recommendations[0];
}

export function buildCheckoutDraftFromFlow(
  sessionId: string,
  selected: VisionRecommendation,
) {
  const state = getChatFlowSession(sessionId);
  const quote = state?.quote;
  return {
    selected_old_sku: quote?.summary.matched_sku_id,
    selected_old_title: quote?.summary.matched_title,
    selected_old_image_path: quote?.upload?.stored_path,
    selected_old_kind: quote?.summary.recognized_type,
    selected_new_sku: selected.sku_id,
    selected_new_title: selected.title,
    selected_new_image_path: selected.image_path,
    selected_new_kind: selected.visual_style,
    selected_new_price: selected.base_price,
    recycle_quote: quote?.summary.recycle_quote,
    currency: quote?.summary.currency || 'CNY',
    qty: 1,
  } satisfies CheckoutDraft;
}

export function saveCheckoutDraftFromRecommendation(sessionId: string, skuId?: string) {
  const selected = selectRecommendationFromFlow(sessionId, skuId);
  if (!selected) {
    return null;
  }

  const draft = buildCheckoutDraftFromFlow(sessionId, selected);
  patchChatFlowSession(sessionId, (current) => ({
    ...current,
    selected_sku: selected.sku_id,
    draft,
  }));
  return {
    selected,
    draft,
  };
}

export function getCheckoutDraft(sessionId: string) {
  return getChatFlowSession(sessionId)?.draft || null;
}
