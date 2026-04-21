type LoadingStateProps = {
  label?: string;
};

export function LoadingState({ label = '加载中...' }: LoadingStateProps) {
  return (
    <div className="loading-state" role="status" aria-live="polite">
      <span className="loading-state__dots">
        <i />
        <i />
        <i />
      </span>
      <span>{label}</span>
    </div>
  );
}
