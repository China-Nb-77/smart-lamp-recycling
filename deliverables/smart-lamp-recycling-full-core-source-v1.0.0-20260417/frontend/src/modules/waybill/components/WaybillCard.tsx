import { AlertCircle, ArrowRightCircle, Truck } from 'lucide-react';
import type { TrackResponse } from '../../../types/api';

type WaybillCardProps = {
  payload: TrackResponse & {
    order_id?: string;
  };
  onAdvance: (waybillId: string) => void;
  onOpenTicket: (waybillId: string) => void;
};

export function WaybillCard({
  payload,
  onAdvance,
  onOpenTicket,
}: WaybillCardProps) {
  const latest = payload.events[payload.events.length - 1];

  return (
    <article className="biz-card biz-card--waybill">
      <div className="biz-card__head">
        <span className="biz-card__icon">
          <Truck size={19} />
        </span>
        <div>
          <strong>物流履约状态</strong>
          <p>{payload.waybill_id}</p>
        </div>
      </div>
      <div className="key-grid">
        <div>
          <span>当前状态</span>
          <strong>{payload.status}</strong>
        </div>
        <div>
          <span>最近轨迹</span>
          <strong>{latest?.desc || '暂无轨迹'}</strong>
        </div>
      </div>
      <ol className="timeline-list">
        {payload.events.map((event) => (
          <li key={`${event.eventTime}_${event.status}`}>
            <span className="timeline-list__dot" />
            <div>
              <strong>{event.status}</strong>
              <p>{event.desc}</p>
              <time>{event.eventTime}</time>
            </div>
          </li>
        ))}
      </ol>
      <div className="biz-card__actions">
        <button
          type="button"
          className="secondary-pill"
          onClick={() => onAdvance(payload.waybill_id)}
        >
          <ArrowRightCircle size={16} />
          推进状态
        </button>
        <button
          type="button"
          className="secondary-pill secondary-pill--danger"
          onClick={() => onOpenTicket(payload.waybill_id)}
        >
          <AlertCircle size={16} />
          异常转工单
        </button>
      </div>
    </article>
  );
}
