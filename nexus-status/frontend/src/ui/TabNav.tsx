import React from 'react';

export type ViewId =
  | 'overview'
  | 'landscape'
  | 'opportunities'
  | 'candidates'
  | 'evidence'
  | 'methodology'
  | 'reproducibility'
  | 'limitations'
  | 'engineering';

export interface TabDefinition {
  id: ViewId;
  label: string;
  group: 'scientific' | 'engineering';
}

export const TABS: readonly TabDefinition[] = [
  { id: 'overview', label: 'Overview', group: 'scientific' },
  { id: 'landscape', label: 'Landscape', group: 'scientific' },
  { id: 'opportunities', label: 'Opportunities', group: 'scientific' },
  { id: 'candidates', label: 'Candidates', group: 'scientific' },
  { id: 'evidence', label: 'Evidence', group: 'scientific' },
  { id: 'methodology', label: 'Methodology', group: 'scientific' },
  { id: 'reproducibility', label: 'Reproducibility', group: 'scientific' },
  { id: 'limitations', label: 'Limitations', group: 'scientific' },
  { id: 'engineering', label: 'Engineering', group: 'engineering' },
];

export interface TabNavProps {
  active: ViewId;
  onChange: (id: ViewId) => void;
}

export const TabNav: React.FC<TabNavProps> = ({ active, onChange }) => {
  return (
    <nav className="tab-nav" aria-label="Dashboard sections">
      {TABS.map((tab) => (
        <button
          key={tab.id}
          type="button"
          className={`tab-button tab-group-${tab.group} ${active === tab.id ? 'active' : ''}`}
          aria-current={active === tab.id ? 'page' : undefined}
          onClick={() => onChange(tab.id)}
        >
          {tab.label}
        </button>
      ))}
    </nav>
  );
};
