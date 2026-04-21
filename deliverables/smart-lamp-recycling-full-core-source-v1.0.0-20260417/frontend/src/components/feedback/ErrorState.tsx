import type { ReactNode } from 'react';

type ErrorStateProps = {
  title: string;
  description: string;
  action?: ReactNode;
};

export function ErrorState({ title, description, action }: ErrorStateProps) {
  return (
    <section className="feedback-card feedback-card--error">
      <div className="feedback-card__icon" aria-hidden="true">
        !
      </div>
      <h2>{title}</h2>
      <p>{description}</p>
      {action}
    </section>
  );
}
