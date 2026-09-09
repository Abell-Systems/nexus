import React from 'react';
import type { ProjectStatus } from '../domain/status';

export interface ReproducibilityViewProps {
  status: ProjectStatus;
}

export const ReproducibilityView: React.FC<ReproducibilityViewProps> = ({ status }) => {
  const formattedDate = new Date(status.evaluated_at).toUTCString();

  return (
    <section className="view-section reproducibility-view" aria-label="Reproducibility">
      <h2 className="section-title">Which project state was evaluated?</h2>
      <dl className="reproducibility-grid">
        <div className="repro-item">
          <dt>Evaluated commit</dt>
          <dd><code>{status.commit_sha}</code></dd>
        </div>
        <div className="repro-item">
          <dt>Evaluated at</dt>
          <dd title={status.evaluated_at}>{formattedDate}</dd>
        </div>
        <div className="repro-item">
          <dt>Project Status contract version</dt>
          <dd><code>v{status.schema_version}</code></dd>
        </div>
        <div className="repro-item">
          <dt>Source contract</dt>
          <dd><code>project_status.json</code> (canonical, machine-readable)</dd>
        </div>
      </dl>
      <p className="repro-note">
        Dataset identity, manifest hashes and temporal-integrity checks are independently
        verified as part of the <code>scientific_integrity</code> dimension — see the
        Engineering view for the full evidence trail. This identifies the project state that
        was audited, not a scientific-result execution — that identifier
        (<code>execution_id</code>) is defined in ADR 0025 and is not yet published.
      </p>
    </section>
  );
};
