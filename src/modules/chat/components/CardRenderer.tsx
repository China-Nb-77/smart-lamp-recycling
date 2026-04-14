import type { ChatCard, PreferenceFormSubmission } from '../../../types/chat';
import type { LampInfo } from '../../../types/api';
import { LampCard } from '../../lamp/components/LampCard';
import { CheckoutFormCard } from '../../payment/components/CheckoutFormCard';
import { ElectronicOrderSummaryCard } from '../../order/components/ElectronicOrderSummaryCard';
import { WaybillCard } from '../../waybill/components/WaybillCard';
import { TicketCard } from '../../ticket/components/TicketCard';
import { RecycleQuoteCard } from '../../vision/components/RecycleQuoteCard';
import { ReplacementRecommendationsCard } from '../../vision/components/ReplacementRecommendationsCard';
import { UploadedImageCard } from './UploadedImageCard';
import { PreferenceFormCard } from './PreferenceFormCard';

type CardRendererProps = {
  card: ChatCard;
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
  onSubmitPreference?: (payload: PreferenceFormSubmission) => void;
  preferenceSubmitting?: boolean;
};

export function CardRenderer({
  card,
  onJoinLampContext,
  onContinueAsk,
  onOpenOrder,
  onAdvanceWaybill,
  onOpenTicket,
  onSelectRecommendation,
  onSubmitPreference,
  preferenceSubmitting,
}: CardRendererProps) {
  switch (card.type) {
    case 'uploaded_image':
      return <UploadedImageCard imageUrl={card.data.image_url} alt={card.data.alt} />;

    case 'lamp':
      return (
        <LampCard
          lamp={card.data}
          onJoinContext={onJoinLampContext}
          onContinueAsk={onContinueAsk}
        />
      );

    case 'qr':
      return null;

    case 'electronic_order':
      return <ElectronicOrderSummaryCard payload={card.data} />;

    case 'waybill':
      return (
        <WaybillCard
          payload={card.data}
          onAdvance={onAdvanceWaybill}
          onOpenTicket={onOpenTicket}
        />
      );

    case 'ticket':
      return <TicketCard payload={card.data} />;

    case 'payment':
      return (
        <article className="biz-card">
          <div className="biz-card__head">
            <div>
              <strong>支付成功回调已接收</strong>
              <p>{card.data.order_id}</p>
            </div>
          </div>
          <div className="key-grid">
            <div>
              <span>code</span>
              <strong>{card.data.code}</strong>
            </div>
            <div>
              <span>waybill_id</span>
              <strong>{card.data.waybill_id}</strong>
            </div>
          </div>
        </article>
      );

    case 'create_waybill':
      return (
        <article className="biz-card">
          <div className="biz-card__head">
            <div>
              <strong>运单已创建</strong>
              <p>{card.data.order_id}</p>
            </div>
          </div>
          <div className="key-grid">
            <div>
              <span>waybill_id</span>
              <strong>{card.data.waybill_id}</strong>
            </div>
            <div>
              <span>status</span>
              <strong>{card.data.status}</strong>
            </div>
          </div>
        </article>
      );

    case 'waybill_advance':
      return (
        <article className="biz-card">
          <div className="biz-card__head">
            <div>
              <strong>履约状态已推进</strong>
              <p>{card.data.waybill_id}</p>
            </div>
          </div>
          <p className="biz-card__body">{card.data.message}</p>
        </article>
      );

    case 'recycle_quote':
      return <RecycleQuoteCard payload={card.data} />;

    case 'replacement_recommendations':
      return (
        <ReplacementRecommendationsCard
          payload={card.data}
          onSelect={onSelectRecommendation}
        />
      );

    case 'preference_form':
      return (
        <PreferenceFormCard
          payload={card.data}
          onSubmit={onSubmitPreference}
          submitting={preferenceSubmitting}
        />
      );

    case 'checkout_form':
      return (
        <CheckoutFormCard
          payload={card.data}
          onOpenOrder={onOpenOrder}
        />
      );

    case 'error':
      return (
        <article className="biz-card biz-card--ticket">
          <div className="biz-card__head">
            <div>
              <strong>二维码错误说明</strong>
              <p>{card.data.error_code}</p>
            </div>
          </div>
          <p className="biz-card__body">{card.data.message}</p>
          <p className="biz-card__caption">{card.data.suggestion}</p>
        </article>
      );
  }
}
