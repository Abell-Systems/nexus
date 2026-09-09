import React from 'react';
import type { ProjectStatus } from '../domain/status';
import { StatusBadge } from './StatusBadge';
import { DimensionCard } from './DimensionCard';

export interface EngineeringViewProps {
  status: ProjectStatus;
}

export const EngineeringView: React.FC<EngineeringViewProps> = ({ status }) => {
  const dimensionEntries = Object.entries(status.dimensions);

  return (
    <section className="view-section engineering-view" aria-label="Engineering">
      <p className="engineering-intro">
        The system producing the scientific results is itself subject to engineering
        quality controls. These are technical health signals, not scientific results.
      </p>

      <div className="verdict-banner">
        <div className="verdict-main">
          <span className="verdict-label">Overall Engineering Status:</span>
          <StatusBadge status={status.overall_status} size="lg" testId="overall-status-badge" />
        </div>
      </div>

      <div className="summary-banner">
        <p className="summary-text">{status.summary}</p>
        <p className="aggregation-rule">
          <strong>Aggregation rule:</strong> {status.aggregation_rule}
        </p>
      </div>

      <div className="dimensions-section" aria-label="Engineering Dimensions">
        <div className="section-title-row">
          <h2 className="section-title">Engineering Dimensions</h2>
          <span className="dimension-count-badge">
            {dimensionEntries.length} Dimensions Monitored
          </span>
        </div>

        <div className="dimensions-grid">
          {dimensionEntries.map(([dimKey, dimStatus]) => (
            <DimensionCard key={dimKey} name={dimKey} dimension={dimStatus} />
          ))}
        </div>
      </div>
    </section>
  );
};
