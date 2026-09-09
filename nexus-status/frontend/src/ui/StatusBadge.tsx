import React from 'react';
import type { StatusValue } from '../domain/status';

export interface StatusBadgeProps {
  status: StatusValue;
  size?: 'sm' | 'md' | 'lg';
  testId?: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  size = 'md',
  testId = 'status-badge',
}) => {
  const sizeClasses = {
    sm: 'status-badge-sm',
    md: 'status-badge-md',
    lg: 'status-badge-lg',
  }[size];

  const statusClass = `status-${status.toLowerCase().replace(/[^a-z0-9]/g, '-')}`;

  return (
    <span
      data-testid={testId}
      className={`status-badge ${statusClass} ${sizeClasses}`}
      title={`Epistemic Status: ${status}`}
    >
      <span className="status-dot" aria-hidden="true" />
      {status}
    </span>
  );
};
