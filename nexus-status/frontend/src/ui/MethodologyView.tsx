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
    <section className="view-section methodology-view" aria-label="Methodology">
      <h2 className="section-title">How Nexus works</h2>
      <p className="section-question">
        This is the intended methodology pipeline. It describes how Nexus is designed to
        move from demand signals to a verified result — see the Engineering view for
        whether the implementing system currently passes its own quality gates.
      </p>
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
