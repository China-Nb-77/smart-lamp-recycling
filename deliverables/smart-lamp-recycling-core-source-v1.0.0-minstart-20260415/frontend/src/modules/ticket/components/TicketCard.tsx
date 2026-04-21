import { ClipboardList } from 'lucide-react';
import type { TicketResponse } from '../../../types/api';

type TicketCardProps = {
  payload: TicketResponse;
};

export function TicketCard({ payload }: TicketCardProps) {
  return (
    <article className="biz-card biz-card--ticket">
      <div className="biz-card__head">
        <span className="biz-card__icon">
          <ClipboardList size={19} />
        </span>
        <div>
          <strong>异常工单已创建</strong>
          <p>{payload.ticket_id}</p>
        </div>
      </div>
      <div className="key-grid">
        <div>
          <span>状态</span>
          <strong>{payload.status}</strong>
        </div>
        <div>
          <span>原因</span>
          <strong>{payload.reason}</strong>
        </div>
      </div>
    </article>
  );
}
