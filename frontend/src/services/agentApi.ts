import { ApiError, extractErrorMessage } from './api/client';
import { visionBaseUrl } from './api/base-url';
import {
  getChatFlowSession,
  getCheckoutDraft,
  getServerSessionBinding,
  patchChatFlowSession,
} from './chatFlowStore';
import type { ChatFlowServerSession, ChatFlowSessionState } from './chatFlowStore';
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

type SessionBootstrapResponse = AgentConversationResponse & {
  session_token: string;
  user_id: string;
  expires_at: string;
};

type VisionRequestOptions = {
  method?: 'GET' | 'POST';
  body?: unknown;
  formData?: FormData;
  headers?: Record<string, string>;
};

async function requestVisionAgent<T>(
  path: string,
  { method = 'GET', body, formData, headers }: VisionRequestOptions = {},
) {
  const response = await fetch(`${visionBaseUrl}${path}`, {
    method,
    headers: formData
      ? headers
      : {
          'Content-Type': 'application/json',
          ...(headers || {}),
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

function withSessionAuth(binding: ChatFlowServerSession) {
  return {
    Authorization: `Bearer ${binding.session_token}`,
  };
}

function requireServerSession(localSessionId: string) {
  const binding = getServerSessionBinding(localSessionId);
  if (!binding) {
    throw new Error('会话尚未初始化，请重新上传图片或刷新会话。');
  }
  return binding;
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
  space: '主要安装在哪个空间？',
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
      note: '一次填完空间、预算和类型，方便工作流给出目录推荐',
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
  async ensureSession(localSessionId: string) {
    const existing = getServerSessionBinding(localSessionId);
    if (existing) {
      return {
        session_id: existing.session_id,
        state: 'init',
        messages: [],
      } satisfies AgentConversationResponse;
    }

    const response = await requestVisionAgent<SessionBootstrapResponse>('/agent/sessions', {
      method: 'POST',
      body: {
        client_session_id: localSessionId,
      },
    });

    patchChatFlowSession(localSessionId, (current) => ({
      ...current,
      server_session: {
        session_id: response.session_id,
        session_token: response.session_token,
        user_id: response.user_id,
        expires_at: response.expires_at,
      },
    }));

    return response;
  },

  async uploadOldLamp(localSessionId: string, file: File) {
    await this.ensureSession(localSessionId);
    const binding = requireServerSession(localSessionId);
    const formData = new FormData();
    formData.append('file', file);

    const response = await requestVisionAgent<AgentConversationResponse>(
      `/agent/sessions/${encodeURIComponent(binding.session_id)}/image`,
      {
        method: 'POST',
        formData,
        headers: withSessionAuth(binding),
      },
    );

    const quote = extractQuote(response);
    const nextState = patchChatFlowSession(localSessionId, (current) => ({
      ...current,
      quote,
      preferences: undefined,
      recommendations: undefined,
      selected_sku: undefined,
      draft: undefined,
    }));

    return maybeAttachPreferenceFormCard(response, localSessionId, nextState.quote, nextState);
  },

  async sendMessage(localSessionId: string, text: string) {
    await this.ensureSession(localSessionId);
    const binding = requireServerSession(localSessionId);
    const response = await requestVisionAgent<AgentConversationResponse>(
      `/agent/sessions/${encodeURIComponent(binding.session_id)}/messages`,
      {
        method: 'POST',
        body: { text },
        headers: withSessionAuth(binding),
      },
    );

    const quote = extractQuote(response);
    const recommendations = extractRecommendations(response);

    const nextState = patchChatFlowSession(localSessionId, (current) => ({
      ...current,
      quote: quote || current.quote,
      recommendations: recommendations || current.recommendations,
    }));

    return maybeAttachPreferenceFormCard(response, localSessionId, nextState.quote, nextState);
  },

  prepareCheckout(sessionId: string) {
    return getCheckoutDraft(sessionId);
  },

  async selectRecommendation(localSessionId: string, skuId: string): Promise<AgentSelectionResponse> {
    await this.ensureSession(localSessionId);
    const binding = requireServerSession(localSessionId);
    const response = await requestVisionAgent<AgentSelectionResponse>(
      `/agent/sessions/${encodeURIComponent(binding.session_id)}/recommendations/select`,
      {
        method: 'POST',
        body: { sku_id: skuId },
        headers: withSessionAuth(binding),
      },
    );

    patchChatFlowSession(localSessionId, (current) => ({
      ...current,
      selected_sku: skuId,
      draft: response.draft,
    }));

    return response;
  },

  async submitPreferences(payload: PreferenceFormSubmission) {
    await this.ensureSession(payload.session_id);
    const binding = requireServerSession(payload.session_id);
    const response = await requestVisionAgent<AgentConversationResponse>(
      `/agent/sessions/${encodeURIComponent(binding.session_id)}/preferences`,
      {
        method: 'POST',
        body: {
          install_type: payload.install_type,
          space: payload.space,
          budget_level: payload.budget_level,
          note: payload.note,
        },
        headers: withSessionAuth(binding),
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

  async getCheckoutForm(localSessionId: string): Promise<AgentCheckoutFormResponse> {
    await this.ensureSession(localSessionId);
    const binding = requireServerSession(localSessionId);
    return requestVisionAgent<AgentCheckoutFormResponse>(
      `/agent/forms/checkout?session_id=${encodeURIComponent(binding.session_id)}`,
      {
        headers: withSessionAuth(binding),
      },
    );
  },

  async normalizeAddress(_payload: Record<string, unknown>): Promise<AgentAddressResponse> {
    throw new Error('请使用 paymentApi.normalizeAddress');
  },

  async locateAddress(_latitude: number, _longitude: number): Promise<AgentAddressResponse> {
    throw new Error('请使用 paymentApi.locateAddress');
  },

  async getLogistics(_orderId: string): Promise<AgentLogisticsResponse> {
    throw new Error('请使用 paymentApi.getLogistics');
  },

  async getLogisticsMap(_orderId: string): Promise<AgentLogisticsMapResponse> {
    throw new Error('请使用 paymentApi.getLogisticsMap');
  },
};

export function getCheckoutEntry(sessionId: string) {
  return agentApi.prepareCheckout(sessionId);
}
