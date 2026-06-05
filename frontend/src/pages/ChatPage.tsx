import { useEffect, useMemo, useRef, useState } from 'react';
import type { ChangeEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { ChatHeader } from '../modules/chat/components/ChatHeader';
import { ChatComposer } from '../modules/chat/components/ChatComposer';
import { MessageList } from '../modules/chat/components/MessageList';
import { HistoryDrawer } from '../modules/history/components/HistoryDrawer';
import {
  createEmptySession,
  ensureSessionCollection,
  getCurrentSessionId,
  removeSession,
  saveSessions,
  setCurrentSessionId,
  upsertSession,
} from '../modules/history/services/session-service';
import { clearUserSession, getStoredUser } from '../auth/session';
import { agentApi } from '../services/agentApi';
import { findLocalSessionIdByRemoteId } from '../services/chatFlowStore';
import { buildVisionImageUrl } from '../services/visionApi';
import type { AgentConversationResponse } from '../types/agent';
import type {
  CheckoutPrefill,
  ChatCard,
  ChatMessage,
  ChatSession,
  PreferenceFormSubmission,
} from '../types/chat';
import type { LampInfo } from '../types/api';
import { createId, generateSessionTitle } from '../utils/text';

export function ChatPage() {
  const navigate = useNavigate();
  const initialSessions = useMemo(() => ensureSessionCollection(), []);
  const [sessions, setSessions] = useState<ChatSession[]>(initialSessions);
  const [currentSessionId, setCurrentSessionIdState] = useState(
    () => getCurrentSessionId() || initialSessions[0].id,
  );
  const [inputValue, setInputValue] = useState('');
  const [historyOpen, setHistoryOpen] = useState(false);
  const [notice, setNotice] = useState('');
  const [uploadingQuote, setUploadingQuote] = useState(false);
  const [preferenceSubmitting, setPreferenceSubmitting] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const galleryInputRef = useRef<HTMLInputElement | null>(null);
  const cameraInputRef = useRef<HTMLInputElement | null>(null);
  const assistantMainRef = useRef<HTMLElement | null>(null);
  const speechRecognitionRef = useRef<SpeechRecognition | null>(null);
  const speechTranscriptRef = useRef('');

  useEffect(() => {
    saveSessions(sessions);
  }, [sessions]);

  useEffect(() => {
    setCurrentSessionId(currentSessionId);
  }, [currentSessionId]);

  useEffect(() => {
    const scrollToLatest = () => {
      const main = assistantMainRef.current;
      if (!main) {
        return;
      }
      main.scrollTo({
        top: main.scrollHeight,
        behavior: 'auto',
      });
    };

    const frame = window.requestAnimationFrame(scrollToLatest);
    const timer = window.setTimeout(scrollToLatest, 120);

    return () => {
      window.cancelAnimationFrame(frame);
      window.clearTimeout(timer);
    };
  }, [sessions, currentSessionId]);

  useEffect(() => {
    if (!notice) {
      return undefined;
    }
    const timer = window.setTimeout(() => setNotice(''), 2400);
    return () => window.clearTimeout(timer);
  }, [notice]);

  const currentSession =
    sessions.find((session) => session.id === currentSessionId) || sessions[0];
  const userLabel = useMemo(() => {
    const user = getStoredUser();
    return user?.displayName || user?.realName || user?.username || '用户';
  }, []);

  function patchSession(sessionId: string, updater: (session: ChatSession) => ChatSession) {
    setSessions((collection) => {
      const current = collection.find((session) => session.id === sessionId);
      if (!current) {
        return collection;
      }
      return upsertSession(collection, updater(current));
    });
  }

  function appendCustomMessage(
    sessionId: string,
    message: ChatMessage,
    options: { updateTitle?: boolean } = {},
  ) {
    patchSession(sessionId, (session) => ({
      ...session,
      title:
        options.updateTitle && session.messages.length === 0
          ? generateSessionTitle(message.text)
          : session.title,
      updated_at: new Date().toISOString(),
      messages: [...session.messages, message],
    }));
  }

  function attachUploadedPreview(
    sessionId: string,
    userMessageId: string,
    response: AgentConversationResponse,
  ) {
    const recycleQuoteCard = response.messages
      .flatMap((message) => message.cards || [])
      .find((card) => card.type === 'recycle_quote');

    const storedPath =
      recycleQuoteCard?.type === 'recycle_quote'
        ? recycleQuoteCard.data.upload?.stored_path
        : '';

    if (!storedPath) {
      return;
    }

    patchSession(sessionId, (session) => ({
      ...session,
      updated_at: new Date().toISOString(),
      messages: session.messages.map((message) =>
        message.id === userMessageId
          ? {
              ...message,
              cards: (() => {
                const currentPreview = message.cards?.find(
                  (card) => card.type === 'uploaded_image',
                );
                const currentImageUrl =
                  currentPreview?.type === 'uploaded_image'
                    ? currentPreview.data.image_url
                    : '';
                if (currentImageUrl.startsWith('blob:')) {
                  URL.revokeObjectURL(currentImageUrl);
                }
                return [
                  {
                    type: 'uploaded_image' as const,
                    data: {
                      image_url: buildVisionImageUrl(storedPath),
                      alt: '已上传的旧灯图片',
                    },
                  },
                ];
              })(),
            }
          : message,
      ),
    }));
  }

  function openCheckout(sessionId: string) {
    const checkoutEntry = agentApi.prepareCheckout(sessionId);
    if (!checkoutEntry) {
      return false;
    }

    navigate(`/payment/orders/new?sessionId=${encodeURIComponent(sessionId)}`);
    return true;
  }

  function applyAgentResponse(
    sessionId: string,
    loadingMessageId: string,
    response: AgentConversationResponse,
  ) {
    const agentMessages = response.messages.map((message) =>
      createMessage(message.role, message.text, {
        cards: message.cards,
        suggestions:
          message.suggestions && message.suggestions.length > 0
            ? message.suggestions
            : buildSuggestions(message.cards || []),
      }),
    );

    patchSession(sessionId, (session) => {
      let replaced = false;
      const nextMessages: ChatMessage[] = session.messages.flatMap((message) => {
        if (message.id !== loadingMessageId) {
          return [message];
        }
        replaced = true;
        if (agentMessages.length === 0) {
          return [{ ...message, status: 'ready' as const, text: '' }];
        }
        const [first, ...rest] = agentMessages;
        return [{ ...first, id: loadingMessageId, status: 'ready' as const }, ...rest];
      });
      if (!replaced) {
        nextMessages.push(...agentMessages);
      }
      return {
        ...session,
        updated_at: new Date().toISOString(),
        messages: nextMessages,
      };
    });
  }

  function createNewChat() {
    if (currentSession.messages.length === 0) {
      setHistoryOpen(false);
      return;
    }
    const next = createEmptySession();
    setSessions((collection) => upsertSession(collection, next));
    setCurrentSessionIdState(next.id);
    setInputValue('');
    setHistoryOpen(false);
  }

  function handleDeleteSession(sessionId: string) {
    const next = removeSession(sessions, sessionId);
    setSessions(next);
    if (!next.some((session) => session.id === currentSessionId)) {
      setCurrentSessionIdState(next[0].id);
    }
  }

  function openGalleryPicker() {
    galleryInputRef.current?.click();
  }

  function openCameraPicker() {
    cameraInputRef.current?.click();
  }

  async function handleSelectedImage(file: File, sourceLabel = '上传图片') {
    const sessionId = currentSessionId;
    const loadingMessageId = createId('msg');
    const userMessageId = createId('msg');
    const localPreviewUrl = URL.createObjectURL(file);

    appendCustomMessage(
      sessionId,
      createMessage('user', `${sourceLabel}：${file.name}`, {
        id: userMessageId,
        cards: [
          {
            type: 'uploaded_image',
            data: {
              image_url: localPreviewUrl,
              alt: '已上传的旧灯图片',
            },
          },
        ],
      }),
      { updateTitle: true },
    );
    patchSession(sessionId, (session) => ({
      ...session,
      updated_at: new Date().toISOString(),
      messages: [
        ...session.messages,
        {
          id: loadingMessageId,
          role: 'assistant',
          text: '',
          created_at: new Date().toISOString(),
          status: 'loading',
        },
      ],
    }));

    setUploadingQuote(true);
    try {
      await agentApi.ensureSession(sessionId);
      const result = await agentApi.uploadOldLamp(sessionId, file);
      attachUploadedPreview(sessionId, userMessageId, result);
      applyAgentResponse(sessionId, loadingMessageId, result);
    } catch (error) {
      patchSession(sessionId, (session) => ({
        ...session,
        updated_at: new Date().toISOString(),
        messages: session.messages.map((message) =>
          message.id === loadingMessageId
            ? {
                ...message,
                text: '图片识别失败，请检查后端服务。',
                status: 'error',
                error_message: error instanceof Error ? error.message : '图片识别失败',
              }
            : message,
        ),
      }));
    } finally {
      setUploadingQuote(false);
    }
  }

  function handleFileInput(event: ChangeEvent<HTMLInputElement>, sourceLabel: string) {
    const file = event.currentTarget.files?.[0];
    event.currentTarget.value = '';
    if (!file) {
      return;
    }
    void handleSelectedImage(file, sourceLabel);
  }

  async function sendQuestion(question: string, appendUser = true) {
    const trimmed = question.trim();
    if (!trimmed) {
      return;
    }

    const sessionId = currentSessionId;
    if (isCheckoutPrompt(trimmed) && openCheckout(sessionId)) {
      return;
    }

    const loadingMessageId = createId('msg');
    const userMessage = createMessage('user', trimmed);

    patchSession(sessionId, (session) => ({
      ...session,
      title: session.messages.length === 0 ? generateSessionTitle(trimmed) : session.title,
      updated_at: new Date().toISOString(),
      messages: [
        ...session.messages,
        ...(appendUser ? [userMessage] : []),
        {
          id: loadingMessageId,
          role: 'assistant',
          text: '',
          created_at: new Date().toISOString(),
          status: 'loading',
        },
      ],
    }));

    setInputValue('');

    try {
      await agentApi.ensureSession(sessionId);
      const result = await agentApi.sendMessage(sessionId, trimmed);
      applyAgentResponse(sessionId, loadingMessageId, result);
    } catch (error) {
      patchSession(sessionId, (session) => ({
        ...session,
        updated_at: new Date().toISOString(),
        messages: session.messages.map((message) =>
          message.id === loadingMessageId
            ? {
                ...message,
                text: '请求失败，请检查后端服务。',
                status: 'error',
                error_message: error instanceof Error ? error.message : '请求失败',
                retry_action: {
                  kind: 'ask',
                  payload: {
                    question: trimmed,
                    session_id: sessionId,
                  },
                },
              }
            : message,
        ),
      }));
    }
  }

  function handleVoiceAction() {
    const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!Recognition) {
      setNotice('当前浏览器不支持语音识别');
      return;
    }

    if (isListening) {
      speechRecognitionRef.current?.stop();
      return;
    }

    const recognition = speechRecognitionRef.current || new Recognition();
    speechRecognitionRef.current = recognition;
    speechTranscriptRef.current = '';
    recognition.lang = 'zh-CN';
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.onresult = (event) => {
      const transcript = Array.from({ length: event.results.length })
        .map((_, index) => event.results[index]?.[0]?.transcript || '')
        .join('')
        .trim();
      speechTranscriptRef.current = transcript;
      setInputValue(transcript);
    };
    recognition.onerror = () => {
      setNotice('语音识别失败');
      setIsListening(false);
    };
    recognition.onend = () => {
      const transcript = speechTranscriptRef.current.trim();
      setIsListening(false);
      if (transcript) {
        void sendQuestion(transcript);
        speechTranscriptRef.current = '';
      }
    };
    recognition.start();
    setIsListening(true);
  }

  function handleRetry(message: ChatMessage) {
    if (message.retry_action?.kind === 'ask') {
      void sendQuestion(message.retry_action.payload.question, false);
    }
  }

  function handleJoinLampContext(lamp: LampInfo) {
    void sendQuestion(`请基于 ${lamp.name} 继续给出建议`);
  }

  function handleQuickPrompt(prompt: string) {
    if (prompt.includes('拍照')) {
      openCameraPicker();
      return;
    }
    if (prompt.includes('相册')) {
      openGalleryPicker();
      return;
    }
    if (prompt.includes('上传旧灯')) {
      openGalleryPicker();
      return;
    }
    if (isCheckoutPrompt(prompt) && openCheckout(currentSessionId)) {
      return;
    }
    void sendQuestion(prompt);
  }

  function handleSelectRecommendation(
    sessionId: string,
    skuId: string,
    options?: CheckoutPrefill,
  ) {
    void (async () => {
      try {
        const localSessionId = findLocalSessionIdByRemoteId(sessionId) || sessionId;
        const selection = await agentApi.selectRecommendation(localSessionId, skuId);
        setCurrentSessionIdState(localSessionId);
        patchSession(localSessionId, (session) => ({
          ...session,
          updated_at: new Date().toISOString(),
          messages: [
            ...session.messages.filter(
              (message) =>
                !(
                  message.cards?.length === 1 &&
                  message.cards[0]?.type === 'checkout_form'
                ),
            ),
            createMessage('user', '帮我下单'),
            createMessage('assistant', '', {
              cards: [
                {
                  type: 'checkout_form',
                  data: {
                    session_id: localSessionId,
                    prefill: {
                      ...options,
                      selected_new_sku: selection.draft.selected_new_sku,
                      selected_new_title:
                        options?.selected_new_title || selection.draft.selected_new_title,
                      selected_new_image_path:
                        options?.selected_new_image_path ||
                        selection.draft.selected_new_image_path,
                      selected_new_kind:
                        options?.selected_new_kind || selection.draft.selected_new_kind,
                      qty: options?.qty || selection.draft.qty,
                    },
                  },
                },
              ],
            }),
          ],
        }));
      } catch (error) {
        setNotice(error instanceof Error ? error.message : '操作失败，请稍后重试');
      }
    })();
  }

  async function handlePreferenceSubmit(payload: PreferenceFormSubmission) {
    const sessionId = payload.session_id;
    const summary = formatPreferenceSummary(payload);
    const loadingMessageId = createId('msg');
    const userMessage = createMessage('user', summary);

    patchSession(sessionId, (session) => ({
      ...session,
      title: session.messages.length === 0 ? generateSessionTitle(summary) : session.title,
      updated_at: new Date().toISOString(),
      messages: [
        ...session.messages,
        userMessage,
        {
          id: loadingMessageId,
          role: 'assistant',
          text: '',
          created_at: new Date().toISOString(),
          status: 'loading',
        },
      ],
    }));

    setPreferenceSubmitting(true);

    try {
      await agentApi.ensureSession(sessionId);
      const result = await agentApi.submitPreferences(payload);
      applyAgentResponse(sessionId, loadingMessageId, result);
    } catch (error) {
      patchSession(sessionId, (session) => ({
        ...session,
        updated_at: new Date().toISOString(),
        messages: session.messages.map((message) =>
          message.id === loadingMessageId
            ? {
                ...message,
                text: '提交失败，请稍后再试',
                status: 'error',
                error_message: error instanceof Error ? error.message : '提交失败',
                retry_action: {
                  kind: 'ask',
                  payload: {
                    question: summary,
                    session_id: sessionId,
                  },
                },
              }
            : message,
        ),
      }));
    } finally {
      setPreferenceSubmitting(false);
    }
  }

  return (
    <div className="assistant-shell">
      <ChatHeader
        title={currentSession.title}
        onOpenHistory={() => setHistoryOpen(true)}
        onNewChat={createNewChat}
        onOpenProfile={() => navigate('/profile')}
        onOpenAdmin={() => navigate('/admin/dashboard')}
        onLogout={() => {
          clearUserSession();
          navigate('/login', { replace: true });
        }}
      />

      <HistoryDrawer
        open={historyOpen}
        sessions={sessions}
        currentSessionId={currentSessionId}
        userLabel={userLabel}
        onClose={() => setHistoryOpen(false)}
        onSelect={(sessionId) => {
          setCurrentSessionIdState(sessionId);
          setHistoryOpen(false);
        }}
        onNewChat={createNewChat}
        onDelete={handleDeleteSession}
      />

      {notice ? <div className="notice-toast">{notice}</div> : null}

      <section className="assistant-main" ref={assistantMainRef}>
        {currentSession.messages.length > 0 ? (
          <MessageList
            messages={currentSession.messages}
            onRetry={handleRetry}
            onJoinLampContext={handleJoinLampContext}
            onContinueAsk={handleQuickPrompt}
            onOpenOrder={(orderId, qrToken) =>
              navigate(
                `/order/${encodeURIComponent(orderId)}/electronic?qrToken=${encodeURIComponent(
                  qrToken,
                )}`,
              )
            }
            onAdvanceWaybill={() => {
              setNotice('请在电子货单页查看物流状态');
            }}
            onOpenTicket={() => {
              setNotice('异常工单入口暂未启用');
            }}
            onSelectRecommendation={handleSelectRecommendation}
            onSubmitPreference={handlePreferenceSubmit}
            preferenceSubmitting={preferenceSubmitting}
          />
        ) : null}
      </section>

      <input
        ref={galleryInputRef}
        className="visually-hidden"
        type="file"
        accept="image/*"
        onChange={(event) => handleFileInput(event, '相册上传')}
      />
      <input
        ref={cameraInputRef}
        className="visually-hidden"
        type="file"
        accept="image/*"
        capture="environment"
        onChange={(event) => handleFileInput(event, '拍照上传')}
      />

      <ChatComposer
        value={inputValue}
        onChange={setInputValue}
        onSubmit={() => {
          void sendQuestion(inputValue);
        }}
        onOpenActions={() => {
          if (openCheckout(currentSessionId)) {
            return;
          }
          navigate(`/payment/orders/new?sessionId=${encodeURIComponent(currentSessionId)}`);
        }}
        onVoiceAction={handleVoiceAction}
        isListening={isListening}
        onPickImage={openGalleryPicker}
        onCaptureImage={openCameraPicker}
        uploadBusy={uploadingQuote}
      />
    </div>
  );
}

function createMessage(
  role: ChatMessage['role'],
  text: string,
  options: {
    id?: string;
    cards?: ChatCard[];
    suggestions?: string[];
  } = {},
): ChatMessage {
  return {
    id: options.id || createId('msg'),
    role,
    text,
    created_at: new Date().toISOString(),
    status: 'ready',
    cards: options.cards,
    suggestions: options.suggestions,
  };
}

function formatPreferenceSummary(payload: PreferenceFormSubmission) {
  const parts: string[] = [];
  if (payload.space) {
    parts.push(`安装空间：${payload.space}`);
  }
  if (payload.budget_level) {
    parts.push(`预算偏好：${payload.budget_level}`);
  }
  if (payload.install_type) {
    parts.push(`灯具类型：${payload.install_type}`);
  }
  if (payload.note) {
    parts.push(`备注：${payload.note}`);
  }
  if (parts.length === 0) {
    parts.push('请根据我填写的空间、预算和灯具类型推荐方案');
  }
  return parts.join('\n');
}

function buildSuggestions(_cards: ChatCard[]) {
  return [];
}

function isCheckoutPrompt(text: string) {
  return ['下单', '填写', '收货信息', '个人信息', '支付'].some((keyword) =>
    text.includes(keyword),
  );
}

