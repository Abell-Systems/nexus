import React from 'react';
import type { CheckResult } from '../domain/status';
import { StatusBadge } from './StatusBadge';

export interface CheckItemProps {
  check: CheckResult;
}

export const CheckItem: React.FC<CheckItemProps> = ({ check }) => {
  return (
    <div className="check-item">
      <div className="check-header">
        <span className="check-name">{check.name}</span>
        <StatusBadge status={check.status} size="sm" />
      </div>
      {(check.value !== undefined || check.threshold !== undefined) && (
        <div className="check-metrics">
          {check.value !== undefined && (
            <span className="check-metric-val">
              <strong>Value:</strong> {String(check.value)}
            </span>
          )}
          {check.threshold !== undefined && (
            <span className="check-metric-threshold">
              <strong>Threshold:</strong> {String(check.threshold)}
            </span>
          )}
        </div>
      )}
      {check.detail && <p className="check-detail">{check.detail}</p>}
    </div>
  );
};
