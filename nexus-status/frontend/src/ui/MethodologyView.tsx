import React from 'react';

interface Stage {
  input: string;
  action: string;
  output: string;
}

const STAGES: ReadonlyArray<Stage> = [
  { input: 'Technology demand signals', action: 'Observe demand and technology landscape', output: 'Landscape map' },
  { input: 'Landscape map', action: 'Cross-reference patent and research evidence', output: 'Evidence base' },
  { input: 'Evidence base', action: 'Detect areas of limited technological coverage', output: 'Candidate opportunity' },
  { input: 'Candidate opportunity', action: 'Synthesize a candidate technological solution', output: 'Candidate invention' },
  { input: 'Candidate invention', action: 'Challenge the candidate against prior art (adversarial review)', output: 'Reviewed candidate' },
  { input: 'Reviewed candidate', action: 'Verify surviving claims against traceable evidence', output: 'Verified result' },
];

export const MethodologyView: React.FC = () => {
  return (
    <section className="view-section methodology-view" aria-label="Methodological design">
      <h2 className="section-title">Methodological design</h2>
      <p className="section-question">
        This is the pipeline Nexus is designed to follow — not a record of results Nexus has
        already produced and published.
      </p>
      <div className="methodology-notice" data-testid="methodology-epistemic-notice">
        <span className="methodology-notice-badge">Designed pipeline · not yet executed end-to-end</span>
        <p>
          No stage below is currently backed by a published scientific result. See{' '}
          <strong>Reproducibility</strong> for what is actually evaluated today, and{' '}
          <a
            href="https://github.com/Abell-Systems/nexus/blob/main/docs/adr/0025-scientific-results-publication-and-track-semantics.md"
            target="_blank"
            rel="noopener noreferrer"
          >
            ADR 0025
          </a>{' '}
          for the publication gate that must be met before any stage here is shown against
          real data.
        </p>
      </div>
      <ol className="methodology-stages">
        {STAGES.map((stage, idx) => (
          <li key={stage.action} className="methodology-stage">
            <div className="stage-index">{idx + 1}</div>
            <div className="stage-body">
              <div className="stage-row"><span className="stage-label">Input</span>{stage.input}</div>
              <div className="stage-row stage-action"><span className="stage-label">Nexus does</span>{stage.action}</div>
              <div className="stage-row"><span className="stage-label">Output</span>{stage.output}</div>
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
};
