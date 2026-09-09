import React from 'react';

export interface NotAvailableViewProps {
  title: string;
  question: string;
  explanation: string;
}

export const NotAvailableView: React.FC<NotAvailableViewProps> = ({
  title,
  question,
  explanation,
}) => {
  return (
    <section className="view-section not-available-view" aria-label={title}>
      <h2 className="section-title">{title}</h2>
      <p className="section-question">{question}</p>
      <div className="not-available-box">
        <span className="not-available-badge">Not yet available</span>
        <p>{explanation}</p>
      </div>
    </section>
  );
};
