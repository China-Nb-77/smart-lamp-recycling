import { AlertCircle, CheckCircle2, LoaderCircle, Wallet } from 'lucide-react';

type PaymentStatusProps = {
  kind: 'processing' | 'success' | 'failure';
  title: string;
  description: string;
  detail?: string;
};

export function PaymentStatus({
  kind,
  title,
  description,
  detail,
}: PaymentStatusProps) {
  const iconMap = {
    processing: <LoaderCircle size={26} className="payment-status__spin" />,
    success: <CheckCircle2 size={26} />,
    failure: <AlertCircle size={26} />,
  } as const;

  return (
    <section className={`payment-status payment-status--${kind}`}>
      <div className="payment-status__badge">
        {iconMap[kind] || <Wallet size={26} />}
      </div>
      <strong>{title}</strong>
      <p>{description}</p>
      {detail ? <small>{detail}</small> : null}
    </section>
  );
}
