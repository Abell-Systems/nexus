import React, { useState } from 'react';
import type { DimensionStatus } from '../domain/status';
import { StatusBadge } from './StatusBadge';
import { CheckItem } from './CheckItem';

export interface DimensionCardProps {
  name: string;
  dimension: DimensionStatus;
}

export const DimensionCard: React.FC<DimensionCardProps> = ({ name, dimension }) => {
  const [isExpanded, setIsExpanded] = useState<boolean>(true);

  const formattedName = name
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');

  const hasChecks = dimension.checks.length > 0;
  const metricsEntries = dimension.metrics ? Object.entries(dimension.metrics) : [];

  return (
    <div className={`dimension-card ${dimension.status.toLowerCase()}`}>
      <div className="dimension-header">
        <div className="dimension-title-group">
          <h3 className="dimension-title">{formattedName}</h3>
          <span className="dimension-raw-key"><code>{name}</code></span>
        </div>
        <div className="dimension-badges">
          <span className={`requirement-badge ${dimension.requirement_level}`}>
            {dimension.requirement_level.toUpperCase()}
          </span>
          <StatusBadge status={dimension.status} size="md" />
        </div>
      </div>

      <div className="dimension-provenance">
        <span className="provenance-label">Evidence:</span>
        <code className="provenance-source">{dimension.evidence_source}</code>
        <span
          className={`evidence-status ${dimension.evidence_available ? 'available' : 'absent'}`}
        >
          {dimension.evidence_available ? '● Available' : '○ Absent'}
        </span>
      </div>

      {dimension.message && (
        <p className="dimension-message">{dimension.message}</p>
      )}

      {metricsEntries.length > 0 && (
        <div className="dimension-metrics-grid">
          {metricsEntries.map(([metricKey, metricValue]) => (
            <div key={metricKey} className="metric-pill">
              <span className="metric-name">{metricKey}</span>
              <span className="metric-val">{String(metricValue)}</span>
            </div>
          ))}
        </div>
      )}

      {hasChecks && (
        <div className="dimension-checks-section">
          <div className="checks-header-row">
            <span className="checks-count">
              Checks ({dimension.checks.length})
            </span>
            <button
              type="button"
              className="toggle-checks-btn"
              onClick={() => setIsExpanded((prev) => !prev)}
            >
              {isExpanded ? 'Collapse' : 'Expand'}
            </button>
          </div>
          {isExpanded && (
            <div className="checks-list">
              {dimension.checks.map((check, idx) => (
                <CheckItem key={`${check.name}-${idx}`} check={check} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
