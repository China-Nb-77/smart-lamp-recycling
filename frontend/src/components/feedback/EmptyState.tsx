import type { ReactNode } from 'react';

type EmptyStateProps = {
  title: string;
  description: string;
  action?: ReactNode;
};

export function EmptyState({ title, description, action }: EmptyStateProps) {
  return (
    <section className="feedback-card">
      <div className="feedback-card__icon" aria-hidden="true">
        ·
      </div>
      <h2>{title}</h2>
      <p>{description}</p>
      {action}
    </section>
  );
}
