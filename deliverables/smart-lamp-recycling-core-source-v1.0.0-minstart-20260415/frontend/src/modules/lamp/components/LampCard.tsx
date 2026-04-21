import { ArrowUpRight, Lightbulb, PlusCircle } from 'lucide-react';
import type { LampInfo } from '../../../types/api';

type LampCardProps = {
  lamp: LampInfo;
  onJoinContext: (lamp: LampInfo) => void;
  onContinueAsk: (prompt: string) => void;
};

export function LampCard({
  lamp,
  onJoinContext,
  onContinueAsk,
}: LampCardProps) {
  return (
    <article className="biz-card biz-card--lamp">
      <div className="biz-card__head">
        <span className="biz-card__icon">
          <Lightbulb size={19} />
        </span>
        <div>
          <strong>{lamp.name}</strong>
          <p>灯具推荐</p>
        </div>
      </div>
      <p className="biz-card__body">{lamp.description}</p>
      <div className="biz-card__actions">
        <button
          type="button"
          className="secondary-pill"
          onClick={() => onJoinContext(lamp)}
        >
          <PlusCircle size={16} />
          加入对话上下文
        </button>
        <button
          type="button"
          className="secondary-pill"
          onClick={() => onContinueAsk(`围绕 ${lamp.name} 继续推荐`)}
        >
          <ArrowUpRight size={16} />
          继续追问
        </button>
      </div>
    </article>
  );
}
