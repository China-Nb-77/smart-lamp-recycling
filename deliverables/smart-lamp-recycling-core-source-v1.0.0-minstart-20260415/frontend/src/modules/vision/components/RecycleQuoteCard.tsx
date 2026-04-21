import { Camera } from 'lucide-react';
import type { VisionQuoteResponse } from '../../../types/vision';
import { buildVisionImageUrl } from '../../../services/visionApi';
import { getInstallTypeLabel } from '../display';

type RecycleQuoteCardProps = {
  payload: VisionQuoteResponse;
};

export function RecycleQuoteCard({ payload }: RecycleQuoteCardProps) {
  const installType = getInstallTypeLabel(payload.summary.recognized_type);
  const uploadedImageUrl = payload.upload?.stored_path
    ? buildVisionImageUrl(payload.upload.stored_path)
    : '';

  return (
    <article className="biz-card biz-card--vision">
      <div className="biz-card__head">
        <span className="biz-card__icon">
          <Camera size={19} />
        </span>
        <div>
          <strong>旧灯识别完成</strong>
          <p>识别种类：{installType}</p>
        </div>
      </div>

      {uploadedImageUrl ? (
        <div className="vision-hero-image">
          <img
            src={uploadedImageUrl}
            alt="旧灯识别图"
            className="vision-hero-image__img"
          />
        </div>
      ) : null}

      <div className="key-grid key-grid--vision">
        <div>
          <span>回收报价</span>
          <strong>
            {payload.summary.currency} {payload.summary.recycle_quote.toFixed(2)}
          </strong>
        </div>
        <div>
          <span>灯具种类</span>
          <strong>{installType}</strong>
        </div>
      </div>
    </article>
  );
}
