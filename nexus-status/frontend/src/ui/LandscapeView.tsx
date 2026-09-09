import React from 'react';
import type { UseScientificResultsResult } from '../application/useScientificResults';
import type { DiscoveryLandscapeRecord, ScientificResultsDocument, ScientificResultsExecution } from '../domain/scientificResults';

export interface LandscapeViewProps {
  result: UseScientificResultsResult;
}

function findExecution(
  document: ScientificResultsDocument,
  executionId: string
): ScientificResultsExecution | undefined {
  return document.executions.find((e) => e.execution_id === executionId);
}

const LandscapeExecutionCard: React.FC<{
  landscape: DiscoveryLandscapeRecord;
  execution: ScientificResultsExecution | undefined;
}> = ({ landscape, execution }) => {
  return (
    <div className="landscape-execution-card">
      <div className="landscape-execution-meta">
        <div className="meta-item">
          <span className="meta-label">Domain</span>
          <span className="meta-value">{execution?.domain ?? 'unknown'}</span>
        </div>
        <div className="meta-item">
          <span className="meta-label">Query</span>
          <span className="meta-value">{landscape.query}</span>
        </div>
        <div className="meta-item">
          <span className="meta-label">Execution</span>
          <code className="meta-value">{landscape.execution_id}</code>
        </div>
        {execution && (
          <div className="meta-item">
            <span className="meta-label">Created at</span>
            <span className="meta-value" title={execution.created_at}>{execution.created_at}</span>
          </div>
        )}
      </div>

      {execution && execution.source_provenance.length > 0 && (
        <div className="datasource-provenance">
          <span className="provenance-label">Data source:</span>
          {execution.source_provenance.map((p) => (
            <span key={p.role} className="provenance-pill">
              {p.role}: <code>{p.kind}</code>
            </span>
          ))}
        </div>
      )}

      <div className="methodology-notice" data-testid="landscape-discovery-disclaimer">
        <span className="methodology-notice-badge">Discovery · model-generated</span>
        <p>{landscape.disclaimer}</p>
      </div>

      <div className="cluster-grid">
        {landscape.clusters.map((observation) => (
          <div key={observation.cluster.cluster_id} className="cluster-card">
            <div className="cluster-card-header">
              <h3 className="cluster-title">{observation.cluster.label}</h3>
              <span className={`white-space-badge ${observation.cluster.is_white_space ? 'is-white-space' : ''}`}>
                {observation.cluster.is_white_space ? 'White space' : 'Not white space'}
              </span>
            </div>

            <div className="dimension-metrics-grid">
              <div className="metric-pill">
                <span className="metric-name">patent_count</span>
                <span className="metric-val">{observation.cluster.patent_count}</span>
              </div>
              <div className="metric-pill">
                <span className="metric-name">white_space_score</span>
                <span className="metric-val">{observation.cluster.white_space_score}</span>
              </div>
              <div className="metric-pill">
                <span className="metric-name">density</span>
                <span className="metric-val">{observation.density}</span>
              </div>
              <div className="metric-pill">
                <span className="metric-name">recency</span>
                <span className="metric-val">{observation.recency}</span>
              </div>
              <div className="metric-pill">
                <span className="metric-name">citation_traction</span>
                <span className="metric-val">{observation.citation_traction}</span>
              </div>
              <div className="metric-pill">
                <span className="metric-name">citation_coverage</span>
                <span className="metric-val">{observation.citation_coverage}</span>
              </div>
              <div className="metric-pill">
                <span className="metric-name">demand_intensity</span>
                <span className="metric-val">{observation.demand_intensity}</span>
              </div>
              <div className="metric-pill">
                <span className="metric-name">mean_age_years</span>
                <span className="metric-val">{observation.mean_age_years}</span>
              </div>
            </div>

            <p className="cluster-quadrant">
              <strong>Quadrant:</strong> {observation.quadrant}
            </p>

            {observation.cluster.representative_patents.length > 0 && (
              <div className="representative-patents">
                <span className="meta-label">Representative patents</span>
                <ul>
                  {observation.cluster.representative_patents.map((patentId) => (
                    <li key={patentId}><code>{patentId}</code></li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export const LandscapeView: React.FC<LandscapeViewProps> = ({ result }) => {
  const { state, data, error, reload } = result;

  return (
    <section className="view-section landscape-view" aria-label="Landscape">
      <h2 className="section-title">Landscape</h2>
      <p className="section-question">What technology space is Nexus analysing?</p>

      {state === 'loading' && (
        <div className="status-centered-box loading-box" data-testid="landscape-loading">
          <div className="spinner" aria-hidden="true" />
          <h3>Loading scientific results...</h3>
          <p>Fetching and validating the canonical scientific results contract.</p>
        </div>
      )}

      {state === 'error' && (
        <div className="status-centered-box error-box" data-testid="landscape-error">
          <div className="error-icon" aria-hidden="true">✕</div>
          <h3>Scientific results unavailable</h3>
          <p className="error-message">
            {error?.message || 'Failed to ingest the scientific results contract.'}
          </p>
          <button type="button" className="retry-button" onClick={reload}>
            ↻ Retry Loading
          </button>
        </div>
      )}

      {state === 'success' && data && data.landscapes.length === 0 && (
        <div className="not-available-box" data-testid="landscape-empty">
          <span className="not-available-badge">No landscape execution published yet</span>
          <p>
            The scientific results contract loaded successfully but does not yet contain a
            published landscape execution.
          </p>
        </div>
      )}

      {state === 'success' && data && data.landscapes.length > 0 && (
        <div className="landscape-executions">
          {data.landscapes.map((landscape) => (
            <LandscapeExecutionCard
              key={landscape.execution_id}
              landscape={landscape}
              execution={findExecution(data, landscape.execution_id)}
            />
          ))}
        </div>
      )}
    </section>
  );
};
