import { AlertCircle, RotateCcw } from 'lucide-react';
import type { ChatCard, ChatMessage, PreferenceFormSubmission } from '../../../types/chat';
import type { LampInfo } from '../../../types/api';
import { formatTimeLabel } from '../../../utils/date';
import { LoadingState } from '../../../components/feedback/LoadingState';
import { CardRenderer } from './CardRenderer';

type MessageListProps = {
  messages: ChatMessage[];
  onRetry: (message: ChatMessage) => void;
  onJoinLampContext: (lamp: LampInfo) => void;
  onContinueAsk: (prompt: string) => void;
  onOpenOrder: (orderId: string, qrToken: string) => void;
  onAdvanceWaybill: (waybillId: string) => void;
  onOpenTicket: (waybillId: string) => void;
  onSelectRecommendation: (
    sessionId: string,
    skuId: string,
    options?: Extract<ChatCard, { type: 'checkout_form' }>['data']['prefill'],
  ) => void;
  onSubmitPreference: (payload: PreferenceFormSubmission) => void;
  preferenceSubmitting: boolean;
};

export function MessageList({
  messages,
  onRetry,
  onJoinLampContext,
  onContinueAsk,
  onOpenOrder,
  onAdvanceWaybill,
  onOpenTicket,
  onSelectRecommendation,
  onSubmitPreference,
  preferenceSubmitting,
}: MessageListProps) {
  const hasRecommendationCard = messages.some((message) =>
    message.cards?.some((card) => card.type === 'replacement_recommendations'),
  );

  return (
    <div className="message-list">
      {messages.map((message) => {
        const hasPreferenceForm = message.cards?.some(
          (card) => card.type === 'preference_form',
        );
        const hideText = message.cards?.some(
          (card) => card.type === 'uploaded_image',
        );
        const hasCards = Boolean(message.cards?.length);
        const hasError = message.status === 'error';
        const hasSuggestions = Boolean(message.suggestions?.length);
        const hasText =
          !hideText &&
          (message.status === 'loading' || message.text.trim().length > 0);
        const hideSuggestions = hasPreferenceForm || hasRecommendationCard;
        const showSuggestions = hasSuggestions && !hideSuggestions;
        const hasVisibleContent = hasText || hasCards || hasError;

        if (!hasVisibleContent && !showSuggestions) {
          return null;
        }

        return (
          <article
            key={message.id}
            className={`message-bubble message-bubble--${message.role}`}
          >
            {!hasText ? null : (
              <div className="message-bubble__text">
                {message.status === 'loading' ? (
                  <LoadingState label="正在处理中..." />
                ) : (
                  <p>{message.text}</p>
                )}
              </div>
            )}
            {hasCards ? (
              <div className="message-bubble__cards">
                {(message.cards || []).map((card, index) => (
                  <CardRenderer
                    key={`${message.id}_${card.type}_${index}`}
                    card={card}
                    onJoinLampContext={onJoinLampContext}
                    onContinueAsk={onContinueAsk}
                    onOpenOrder={onOpenOrder}
                    onAdvanceWaybill={onAdvanceWaybill}
                    onOpenTicket={onOpenTicket}
                    onSelectRecommendation={onSelectRecommendation}
                    onSubmitPreference={onSubmitPreference}
                    preferenceSubmitting={preferenceSubmitting}
                  />
                ))}
              </div>
            ) : null}
            {showSuggestions ? (
              <div className="message-suggestions">
                {(message.suggestions || []).map((item) => (
                  <button
                    key={`${message.id}_${item}`}
                    type="button"
                    className="suggestion-pill"
                    onClick={() => onContinueAsk(item)}
                  >
                    {item}
                  </button>
                ))}
              </div>
            ) : null}
            {hasError ? (
              <div className="message-error">
                <AlertCircle size={16} />
                <span>{message.error_message || '请求失败，请稍后重试'}</span>
                <button type="button" onClick={() => onRetry(message)}>
                  <RotateCcw size={14} />
                  重试
                </button>
              </div>
            ) : null}
            <time className="message-time">{formatTimeLabel(message.created_at)}</time>
          </article>
        );
      })}
    </div>
  );
}
