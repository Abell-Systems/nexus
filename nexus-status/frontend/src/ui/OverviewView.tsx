import React from 'react';
import type { ProjectStatus } from '../domain/status';
import { StatusBadge } from './StatusBadge';

export interface OverviewViewProps {
  status: ProjectStatus;
  onOpenEngineering: () => void;
}

const STEPS: ReadonlyArray<{ verb: string; text: string }> = [
  { verb: 'Observes', text: 'Demand and technology landscapes' },
  { verb: 'Identifies', text: 'Areas with potentially limited technological coverage' },
  { verb: 'Synthesizes', text: 'Candidate technological solutions' },
  { verb: 'Challenges', text: 'Candidates against prior art' },
  { verb: 'Verifies', text: 'Results using traceable evidence' },
];

export const OverviewView: React.FC<OverviewViewProps> = ({ status, onOpenEngineering }) => {
  return (
    <section className="view-section overview-view" aria-label="Scientific Overview">
      <div className="hero-block">
        <div className="hero-eyebrow">Autonomous technology discovery and scientific verification</div>
        <p className="hero-description">
          Nexus combines technology demand, patent landscapes and scientific evidence to
          identify potentially underexplored technological spaces and subject candidate
          inventions to adversarial prior-art verification.
        </p>
      </div>

      <div className="what-nexus-does">
        <h2 className="section-title">What Nexus does</h2>
        <ol className="pipeline-steps">
          {STEPS.map((step, idx) => (
            <li key={step.verb} className="pipeline-step">
              <span className="pipeline-step-index">{idx + 1}</span>
              <div>
                <div className="pipeline-step-verb">{step.verb}</div>
                <div className="pipeline-step-text">{step.text}</div>
              </div>
            </li>
          ))}
        </ol>
      </div>

      <div className="scientific-engineering-split">
        <h2 className="section-title">Scientific vs. engineering</h2>
        <p>
          This workspace separates <strong>scientific results</strong> (what Nexus observed,
          proposed and verified) from <strong>engineering health</strong> (whether the system
          producing those results is itself under quality control). The two are related but
          distinct — engineering status does not constitute a scientific result.
        </p>
        <button type="button" className="link-button" onClick={onOpenEngineering}>
          View engineering status
          {' '}
          <StatusBadge status={status.overall_status} size="sm" testId="overview-engineering-badge" />
        </button>
      </div>
    </section>
  );
};
