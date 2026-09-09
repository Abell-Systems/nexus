import React from 'react';
import { useProjectStatus } from '../application/useProjectStatus';
import { Header } from './Header';
import { DimensionCard } from './DimensionCard';
import './styles.css';

export interface ScientificDashboardProps {
  statusUrl?: string;
}

export const ScientificDashboard: React.FC<ScientificDashboardProps> = ({
  statusUrl = './project_status.json',
}) => {
  const { state, data, error, reload } = useProjectStatus(statusUrl);

  if (state === 'loading') {
    return (
      <main className="dashboard-container">
        <div className="status-centered-box loading-box">
          <div className="spinner" aria-hidden="true" />
          <h2>Loading Scientific Verification...</h2>
          <p>Fetching and validating canonical project status contract.</p>
        </div>
      </main>
    );
  }

  if (state === 'error' || !data) {
    return (
      <main className="dashboard-container">
        <div className="status-centered-box error-box">
          <div className="error-icon" aria-hidden="true">✕</div>
          <h2>Verification Status Unavailable</h2>
          <p className="error-message">
            {error?.message || 'Failed to ingest canonical project status.'}
          </p>
          <button
            type="button"
            className="retry-button"
            onClick={reload}
          >
            ↻ Retry Loading
          </button>
        </div>
      </main>
    );
  }

  const dimensionEntries = Object.entries(data.dimensions);

  return (
    <main className="dashboard-container">
      <Header status={data} onReload={reload} />

      <section className="dimensions-section" aria-label="Scientific Dimensions">
        <div className="section-title-row">
          <h2 className="section-title">Scientific & Engineering Dimensions</h2>
          <span className="dimension-count-badge">
            {dimensionEntries.length} Dimensions Monitored
          </span>
        </div>

        <div className="dimensions-grid">
          {dimensionEntries.map(([dimKey, dimStatus]) => (
            <DimensionCard
              key={dimKey}
              name={dimKey}
              dimension={dimStatus}
            />
          ))}
        </div>
      </section>
    </main>
  );
};
