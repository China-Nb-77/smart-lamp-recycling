import { FileText, ExternalLink } from 'lucide-react';
import type { ElectronicOrderResponse } from '../../../types/api';

type ElectronicOrderSummaryCardProps = {
  payload: ElectronicOrderResponse;
  qr_token?: string;
  onOpenOrder?: (orderId: string, qrToken: string) => void;
};

export function ElectronicOrderSummaryCard({
  payload,
  qr_token,
  onOpenOrder,
}: ElectronicOrderSummaryCardProps) {
  return (
    <article className="biz-card biz-card--order">
      <div className="biz-card__head">
        <span className="biz-card__icon">
          <FileText size={19} />
        </span>
        <div>
          <strong>电子订单摘要</strong>
          <p>{payload.order_id}</p>
        </div>
      </div>
      <div className="key-grid">
        <div>
          <span>订单状态</span>
          <strong>{payload.order_basic?.status || '--'}</strong>
        </div>
        <div>
          <span>支付状态</span>
          <strong>{payload.payment?.pay_status || '--'}</strong>
        </div>
        <div>
          <span>总金额</span>
          <strong>
            {payload.payment?.total !== undefined ? `¥${payload.payment.total}` : '--'}
          </strong>
        </div>
        <div>
          <span>运单号</span>
          <strong>{payload.waybill?.waybill_id || '--'}</strong>
        </div>
      </div>
      {qr_token && onOpenOrder ? (
        <div className="biz-card__actions">
          <button
            type="button"
            className="secondary-pill"
            onClick={() => onOpenOrder(payload.order_id, qr_token)}
          >
            <ExternalLink size={16} />
            打开完整电子订单
          </button>
        </div>
      ) : null}
    </article>
  );
}
