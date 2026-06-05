import { QRCodeSVG } from 'qrcode.react';
import { QrCode, Smartphone } from 'lucide-react';
import { formatFen } from '../../modules/payment/utils';

type QRCodePayProps = {
  codeUrl: string;
  orderId: string;
  amount: number;
  currency?: string;
  tradeType?: 'NATIVE' | 'H5';
};

export function QRCodePay({
  codeUrl,
  orderId,
  amount,
  currency = 'CNY',
  tradeType = 'NATIVE',
}: QRCodePayProps) {
  const paymentMethodLabel = tradeType === 'H5' ? 'WeChat H5 Link' : 'WeChat Native QR';

  return (
    <section className="payment-card qr-pay-card">
      <div className="payment-card__header">
        <span className="payment-card__icon">
          <QrCode size={18} />
        </span>
        <div>
          <strong>微信扫码支付</strong>
          <p>{orderId}</p>
        </div>
      </div>

      <div className="qr-pay-card__canvas">
        <QRCodeSVG value={codeUrl} size={188} bgColor="#ffffff" fgColor="#111111" />
      </div>

      <div className="payment-meta-grid">
        <div>
          <span>支付金额</span>
          <strong>{formatFen(amount, currency)}</strong>
        </div>
        <div>
          <span>支付方式</span>
          <strong>{paymentMethodLabel}</strong>
        </div>
      </div>

      <div className="payment-inline-tip">
        <Smartphone size={16} />
        <span>请使用微信扫一扫完成支付，状态会自动刷新。</span>
      </div>
    </section>
  );
}
