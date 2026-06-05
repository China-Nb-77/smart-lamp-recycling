import { Copy, ExternalLink, QrCode } from 'lucide-react';
import { QRCodeSVG } from 'qrcode.react';
import type { GenerateQrResponse } from '../../../types/api';

type QrCardProps = {
  order_id: string;
  qr: GenerateQrResponse;
  onOpenOrder: (orderId: string, qrToken: string) => void;
  onCopy: (value: string) => void;
};

export function QrCard({ order_id, qr, onOpenOrder, onCopy }: QrCardProps) {
  const hasQrToken = Boolean(qr.qr_token);

  return (
    <article className="biz-card biz-card--order">
      <div className="biz-card__head">
        <span className="biz-card__icon">
          <QrCode size={19} />
        </span>
        <div>
          <strong>电子订单二维码</strong>
          <p>{order_id}</p>
        </div>
      </div>
      <div className="qr-card">
        <div className="qr-card__meta">
          <span>qr_token</span>
          <strong>{qr.qr_token || '--'}</strong>
          <span>expire_at</span>
          <strong>{qr.expire_at}</strong>
        </div>
        <div className="qr-card__visual">
          <QRCodeSVG
            value={qr.qr_url}
            size={92}
            bgColor="transparent"
            fgColor="#111111"
          />
        </div>
      </div>
      <div className="biz-card__actions">
        <button
          type="button"
          className="secondary-pill"
          onClick={() => {
            if (hasQrToken) {
              onOpenOrder(order_id, qr.qr_token);
            }
          }}
          disabled={!hasQrToken}
        >
          <ExternalLink size={16} />
          打开电子订单
        </button>
        <button
          type="button"
          className="secondary-pill"
          onClick={() => onCopy(qr.qr_url)}
        >
          <Copy size={16} />
          复制二维码链接
        </button>
      </div>
    </article>
  );
}
