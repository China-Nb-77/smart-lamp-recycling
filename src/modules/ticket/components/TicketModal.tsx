import { X } from 'lucide-react';
import { ticket_reason_options, type TicketReason } from '../../../types/api';

type TicketModalProps = {
  open: boolean;
  defaultOrderId: string;
  defaultWaybillId: string;
  onClose: () => void;
  onSubmit: (payload: {
    order_id: string;
    waybill_id?: string;
    reason: TicketReason;
    detail: string;
  }) => void;
};

export function TicketModal({
  open,
  defaultOrderId,
  defaultWaybillId,
  onClose,
  onSubmit,
}: TicketModalProps) {
  if (!open) {
    return null;
  }

  return (
    <div className="sheet-backdrop" onClick={onClose}>
      <div
        className="sheet-panel sheet-panel--ticket"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="sheet-panel__header">
          <div>
            <strong>异常工单</strong>
            <p>真实接口：POST /api/ticket</p>
          </div>
          <button type="button" className="icon-button" onClick={onClose}>
            <X size={20} />
          </button>
        </div>
        <form
          className="sheet-form"
          onSubmit={(event) => {
            event.preventDefault();
            const formData = new FormData(event.currentTarget);
            onSubmit({
              order_id: String(formData.get('order_id') || ''),
              waybill_id: String(formData.get('waybill_id') || ''),
              reason: String(formData.get('reason') || '其他') as TicketReason,
              detail: String(formData.get('detail') || ''),
            });
          }}
        >
          <label>
            <span>order_id</span>
            <input defaultValue={defaultOrderId} name="order_id" placeholder="ORDER_1001" />
          </label>
          <label>
            <span>waybill_id</span>
            <input
              defaultValue={defaultWaybillId}
              name="waybill_id"
              placeholder="WB123456"
            />
          </label>
          <label>
            <span>reason</span>
            <select defaultValue="其他" name="reason">
              {ticket_reason_options.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>detail</span>
            <textarea name="detail" placeholder="请描述触发工单的上下文" rows={4} />
          </label>
          <button type="submit" className="primary-button">
            提交工单
          </button>
        </form>
      </div>
    </div>
  );
}
