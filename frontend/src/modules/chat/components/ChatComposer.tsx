import { Camera, ImagePlus, Mic, Plus, SendHorizonal } from 'lucide-react';

type ChatComposerProps = {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  onOpenActions: () => void;
  onVoiceAction: () => void;
  isListening: boolean;
  onPickImage: () => void;
  onCaptureImage: () => void;
  uploadBusy?: boolean;
};

export function ChatComposer({
  value,
  onChange,
  onSubmit,
  onOpenActions,
  onVoiceAction,
  isListening,
  onPickImage,
  onCaptureImage,
  uploadBusy = false,
}: ChatComposerProps) {
  const hasValue = value.trim().length > 0;

  return (
    <div className="composer-wrap">
      <div className="composer-card">
        <textarea
          aria-label="消息输入框"
          className="composer-input"
          placeholder="发消息或按住说话"
          rows={1}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter' && !event.shiftKey) {
              event.preventDefault();
              onSubmit();
            }
          }}
        />
        <div className="composer-actions">
          <div className="composer-chips">
            <button
              type="button"
              className="composer-chip"
              onClick={onCaptureImage}
              disabled={uploadBusy}
            >
              <Camera size={18} />
              <span>{uploadBusy ? '上传中...' : '拍照识别'}</span>
            </button>
            <button
              type="button"
              className="composer-chip"
              onClick={onPickImage}
              disabled={uploadBusy}
            >
              <ImagePlus size={18} />
              <span>相册上传</span>
            </button>
          </div>
          <div className="composer-ops">
            <button
              type="button"
              className="composer-circle"
              aria-label="打开业务操作"
              onClick={onOpenActions}
            >
              <Plus size={24} />
            </button>
            <button
              type="button"
              className={`composer-circle composer-circle--primary ${hasValue ? '' : 'composer-circle--ghost'} ${isListening && !hasValue ? 'composer-circle--listening' : ''}`}
              aria-label={hasValue ? '发送消息' : isListening ? '停止语音识别' : '开始语音识别'}
              onClick={hasValue ? onSubmit : onVoiceAction}
            >
              {hasValue ? <SendHorizonal size={22} /> : <Mic size={23} />}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
