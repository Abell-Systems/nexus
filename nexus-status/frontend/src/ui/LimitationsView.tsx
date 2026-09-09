import React from 'react';

const NON_CLAIMS: readonly string[] = [
  'Prove patentability of any candidate invention.',
  'Replace a professional prior-art search.',
  'Prove commercial viability of a candidate or opportunity.',
  'Prove causal relationships merely from detected associations.',
];

export const LimitationsView: React.FC = () => {
  return (
    <section className="view-section limitations-view" aria-label="Limitations">
      <h2 className="section-title">What Nexus does not claim</h2>
      <ul className="limitations-list">
        {NON_CLAIMS.map((claim) => (
          <li key={claim}>{claim}</li>
        ))}
      </ul>
      <div className="model-vs-evidence-box">
        <p>
          <strong>Model output</strong> is a candidate or opportunity produced by the Nexus
          pipeline. <strong>Scientifically verified evidence</strong> is the traceable,
          citable material (patents, publications, adversarial checks) that supports or
          challenges it. Nexus keeps these two distinct throughout this workspace.
        </p>
      </div>
    </section>
  );
};
