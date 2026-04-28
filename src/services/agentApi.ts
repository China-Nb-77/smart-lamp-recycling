import { ApiError, extractErrorMessage } from './api/client';
import {
  getChatFlowSession,
  getCheckoutDraft,
  patchChatFlowSession,
} from './chatFlowStore';
import type { ChatFlowSessionState } from './chatFlowStore';
import type {
  AgentAddressResponse,
  AgentCheckoutFormResponse,
  AgentConversationResponse,
  AgentLogisticsMapResponse,
  AgentLogisticsResponse,
  AgentSelectionResponse,
} from '../types/agent';
import type { ChatCard, PreferenceFieldKey, PreferenceFormSubmission } from '../types/chat';
import type { VisionRecommendationResponse, VisionQuoteResponse } from '../types/vision';
import { classifyLamp } from '../api/ai';

const unsupportedFlowError =
  '当前后端仅支持文本问答、本地图片识别，以及已接入的下单/物流流程。';

// 硬编码后端地址
const visionBaseUrl = 'http://114.215.177.52:8000/vision-api';

type VisionRequestOptions = {
  method?: 'GET' | 'POST';
  body?: unknown;
  formData?: FormData;
};

async function requestVisionAgent<T>(
  path: string,
  { method = 'GET', body, formData }: VisionRequestOptions = {},
) {
  const response = await fetch(`${visionBaseUrl}${path}`, {
    method,
    headers: formData
      ? undefined
      : {
          'Content-Type': 'application/json',
        },
    body: formData || (body === undefined ? undefined : JSON.stringify(body)),
  });

  const contentType = response.headers.get('content-type') || '';
  const payload = contentType.includes('application/json')
    ? await response.json()
    : await response.text();

  if (!response.ok) {
    throw new ApiError(extractErrorMessage(payload), response.status, payload);
  }

  return payload as T;
}

function extractQuote(response: AgentConversationResponse) {
  return response.messages
    .flatMap((message) => message.cards || [])
    .find((card): card is { type: 'recycle_quote'; data: VisionQuoteResponse } => card.type === 'recycle_quote')
    ?.data;
}

function extractRecommendations(response: AgentConversationResponse) {
  return response.messages
    .flatMap((message) => message.cards || [])
    .find(
      (card): card is { type: 'replacement_recommendations'; data: VisionRecommendationResponse } =>
        card.type === 'replacement_recommendations',
    )?.data;
}

const preferenceFieldLabels: Record<PreferenceFieldKey, string> = {
  space: '主要装在哪个空间？',
  budget_level: '预算更偏向哪一档？',
  install_type: '灯具类型？',
};

const preferenceFieldOrder: PreferenceFieldKey[] = ['space', 'budget_level', 'install_type'];

function isPreferenceComplete(state?: ChatFlowSessionState) {
  if (!state?.preferences) {
    return false;
  }
  return Boolean(state.preferences.space && state.preferences.budget_level && state.preferences.install_type);
}

function buildPreferenceFormCard(
  sessionId: string,
  quote?: VisionQuoteResponse,
  state?: ChatFlowSessionState,
): ChatCard | undefined {
  if (!quote?.follow_up_questions?.length) {
    return undefined;
  }

  const currentState = state || getChatFlowSession(sessionId);
  if (isPreferenceComplete(currentState)) {
    return undefined;
  }

  const fields: Extract<ChatCard, { type: 'preference_form' }>['data']['fields'] = [];

  preferenceFieldOrder.forEach((key) => {
    const question = quote.follow_up_questions.find((item) => item.id === key);
    if (!question || !question.options?.length) {
      return;
    }

    fields.push({
      key,
      label: question.question || preferenceFieldLabels[key],
      value: currentState?.preferences?.[key],
      options: question.options.map((option) => ({
        value: option.value,
        label: option.label,
      })),
    });
  });

  if (!fields.length) {
    return undefined;
  }

  return {
    type: 'preference_form',
    data: {
      session_id: sessionId,
      title: '完善装灯需求',
      note: '一次填完空间、预算和类型，方便智能体匹配方案',
      submit_label: '提交偏好并获取推荐',
      fields,
    },
  };
}

function findLastAssistantMessageIndex(messages: AgentConversationResponse['messages']) {
  for (let index = messages.length - 1; index >= 0; index -= 1) {
    if (messages[index]?.role === 'assistant') {
      return index;
    }
  }
  return -1;
}

function maybeAttachPreferenceFormCard(
  response: AgentConversationResponse,
  sessionId: string,
  quote?: VisionQuoteResponse,
  state?: ChatFlowSessionState,
): AgentConversationResponse {
  if (extractRecommendations(response) || state?.recommendations) {
    return response;
  }

  if (
    response.messages.some((message) =>
      (message.cards || []).some((card) => card.type === 'preference_form'),
    )
  ) {
    return response;
  }

  const card = buildPreferenceFormCard(sessionId, quote, state);
  if (!card) {
    return response;
  }

  const assistantIndex = findLastAssistantMessageIndex(response.messages);
  if (assistantIndex < 0) {
    return {
      ...response,
      messages: [
        ...response.messages,
        {
          role: 'assistant' as const,
          text: '',
          cards: [card],
        },
      ],
    };
  }

  const messages = response.messages.map((message, index) =>
    index === assistantIndex
      ? {
          ...message,
          cards: [...(message.cards || []), card],
        }
      : message,
  );

  return {
    ...response,
    messages,
  };
}

export const agentApi = {
  ensureSession(sessionId: string) {
    return requestVisionAgent<AgentConversationResponse>('/agent/sessions', {
      method: 'POST',
      body: {
        session_id: sessionId,
      },
    });
  },

  async uploadOldLamp(sessionId: string, file: File) {
    const lampTypeResult = await classifyLamp(file).catch(() => null);
    const formData = new FormData();
    formData.append('file', file);

    const response = await requestVisionAgent<AgentConversationResponse>(
      `/agent/sessions/${encodeURIComponent(sessionId)}/image`,
      {
        method: 'POST',
        formData,
      },
    );

    const recycleQuoteCard = response.messages
      .flatMap((message) => message.cards || [])
      .find((card): card is { type: 'recycle_quote'; data: VisionQuoteResponse } => card.type === 'recycle_quote');

    if (lampTypeResult && recycleQuoteCard) {
      recycleQuoteCard.data.summary.lamp_type_label =
        lampTypeResult.lamp_type || lampTypeResult.label || recycleQuoteCard.data.summary.lamp_type_label;
      recycleQuoteCard.data.summary.lamp_type_score =
        lampTypeResult.confidence || lampTypeResult.score || recycleQuoteCard.data.summary.lamp_type_score;
      recycleQuoteCard.data.summary.lamp_type_backend =
        lampTypeResult.backend || recycleQuoteCard.data.summary.lamp_type_backend;
      recycleQuoteCard.data.summary.lamp_type_model_id =
        lampTypeResult.model_id || recycleQuoteCard.data.summary.lamp_type_model_id;
    }

    const quote = extractQuote(response);
    const nextState = patchChatFlowSession(sessionId, (current) => ({
      ...current,
      quote,
      preferences: undefined,
      recommendations: undefined,
      selected_sku: undefined,
      draft: undefined,
    }));

    return maybeAttachPreferenceFormCard(response, sessionId, nextState.quote, nextState);
  },

  async sendMessage(sessionId: string, text: string) {
    const response = await requestVisionAgent<AgentConversationResponse>(
      `/agent/sessions/${encodeURIComponent(sessionId)}/messages`,
      {
        method: 'POST',
        body: {
          text,
        },
      },
    );

    const quote = extractQuote(response);
    const recommendations = extractRecommendations(response);

    const nextState = patchChatFlowSession(sessionId, (current) => ({
      ...current,
      quote: quote || current.quote,
      recommendations: recommendations || current.recommendations,
    }));

    return maybeAttachPreferenceFormCard(response, sessionId, nextState.quote, nextState);
  },

  prepareCheckout(sessionId: string) {
    return getCheckoutDraft(sessionId);
  },

  async selectRecommendation(sessionId: string, skuId: string): Promise<AgentSelectionResponse> {
    const response = await requestVisionAgent<AgentSelectionResponse>(
      `/agent/sessions/${encodeURIComponent(sessionId)}/recommendations/select`,
      {
        method: 'POST',
        body: {
          sku_id: skuId,
        },
      },
    );

    patchChatFlowSession(sessionId, (current) => ({
      ...current,
      selected_sku: skuId,
      draft: response.draft,
    }));

    return response;
  },

  async submitPreferences(payload: PreferenceFormSubmission) {
    const response = await requestVisionAgent<AgentConversationResponse>(
      `/agent/sessions/${encodeURIComponent(payload.session_id)}/preferences`,
      {
        method: 'POST',
        body: {
          install_type: payload.install_type,
          space: payload.space,
          budget_level: payload.budget_level,
          note: payload.note,
        },
      },
    );

    const quote = extractQuote(response);
    const recommendations = extractRecommendations(response);
    const nextState = patchChatFlowSession(payload.session_id, (current) => ({
      ...current,
      quote: quote || current.quote,
      preferences: {
        ...current.preferences,
        install_type: payload.install_type || current.preferences?.install_type,
        space: payload.space || current.preferences?.space,
        budget_level: payload.budget_level || current.preferences?.budget_level,
      },
      recommendations: recommendations || current.recommendations,
    }));

    return maybeAttachPreferenceFormCard(response, payload.session_id, nextState.quote, nextState);
  },

  async getCheckoutForm(_sessionId: string): Promise<AgentCheckoutFormResponse> {
    throw new Error(unsupportedFlowError);
  },

  async normalizeAddress(_payload: Record<string, unknown>): Promise<AgentAddressResponse> {
    throw new Error(unsupportedFlowError);
  },

  async locateAddress(_latitude: number, _longitude: number): Promise<AgentAddressResponse> {
    throw new Error(unsupportedFlowError);
  },

  async getLogistics(_orderId: string): Promise<AgentLogisticsResponse> {
    throw new Error(unsupportedFlowError);
  },

  async getLogisticsMap(_orderId: string): Promise<AgentLogisticsMapResponse> {
    throw new Error(unsupportedFlowError);
  },
};

export function getCheckoutEntry(sessionId: string) {
  return agentApi.prepareCheckout(sessionId);
}
