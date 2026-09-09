import React from 'react';
import type { ProjectStatus } from '../domain/status';
import { StatusBadge } from './StatusBadge';

export interface HeaderProps {
  status: ProjectStatus;
  onReload: () => void;
}

export const Header: React.FC<HeaderProps> = ({ status, onReload }) => {
  const shortSha = status.commit_sha.slice(0, 12);
  const formattedDate = new Date(status.evaluated_at).toUTCString();

  return (
    <header className="dashboard-header">
      <div className="header-top-row">
        <div>
          <div className="system-identity">Abell Nexus · Epistemic Observability</div>
          <h1 className="header-title">Nexus Scientific Verification</h1>
          <p className="header-subtitle">
            Autonomous scientific audit & empirical integrity dashboard (ADR 0022 · ADR 0024)
          </p>
        </div>
        <div className="header-actions">
          <button
            type="button"
            className="reload-button"
            onClick={onReload}
            title="Re-fetch status contract"
          >
            ↻ Refresh
          </button>
        </div>
      </div>

      <div className="verdict-banner">
        <div className="verdict-main">
          <span className="verdict-label">Overall Project Status:</span>
          <StatusBadge
            status={status.overall_status}
            size="lg"
            testId="overall-status-badge"
          />
        </div>
        <div className="verdict-meta">
          <div className="meta-item">
            <span className="meta-label">Evaluated Commit:</span>
            <code className="meta-value sha">{shortSha}</code>
          </div>
          <div className="meta-item">
            <span className="meta-label">Evaluated At:</span>
            <span className="meta-value date" title={status.evaluated_at}>
              {formattedDate}
            </span>
          </div>
          <div className="meta-item">
            <span className="meta-label">Contract Schema:</span>
            <code className="meta-value">v{status.schema_version}</code>
          </div>
        </div>
      </div>

      <div className="summary-banner">
        <p className="summary-text">{status.summary}</p>
        <p className="aggregation-rule">
          <strong>Aggregation rule:</strong> {status.aggregation_rule}
        </p>
      </div>
    </header>
  );
};
