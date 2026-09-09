import React, { useState } from 'react';
import { useProjectStatus } from '../application/useProjectStatus';
import { Header } from './Header';
import { TabNav, type ViewId } from './TabNav';
import { OverviewView } from './OverviewView';
import { MethodologyView } from './MethodologyView';
import { ReproducibilityView } from './ReproducibilityView';
import { LimitationsView } from './LimitationsView';
import { EngineeringView } from './EngineeringView';
import { NotAvailableView } from './NotAvailableView';
import './styles.css';

export interface ScientificDashboardProps {
  statusUrl?: string;
}

const NOT_AVAILABLE_COPY: Record<'landscape' | 'opportunities' | 'candidates' | 'evidence', {
  title: string;
  question: string;
  explanation: string;
}> = {
  landscape: {
    title: 'Landscape',
    question: 'What technology space is Nexus analysing?',
    explanation:
      'The current canonical project status contract does not yet expose technology, ' +
      'cluster or domain data. This view will populate once Nexus publishes structured ' +
      'landscape results.',
  },
  opportunities: {
    title: 'Opportunities',
    question: 'Where are the technological gaps?',
    explanation:
      'The current canonical project status contract does not yet expose opportunity ' +
      'records (demand, patent density, white-space score). This view will populate once ' +
      'Nexus publishes structured opportunity results.',
  },
  candidates: {
    title: 'Candidates',
    question: 'What does Nexus propose?',
    explanation:
      'The current canonical project status contract does not yet expose candidate ' +
      'invention records or their verification outcomes. This view will populate once ' +
      'Nexus publishes structured candidate results.',
  },
  evidence: {
    title: 'Evidence',
    question: 'Why should I believe it?',
    explanation:
      'The current canonical project status contract does not yet expose per-candidate ' +
      'supporting evidence or adversarial verification traces. This view will populate ' +
      'once Nexus publishes a structured evidence chain.',
  },
};

export const ScientificDashboard: React.FC<ScientificDashboardProps> = ({
  statusUrl = './project_status.json',
}) => {
  const { state, data, error, reload } = useProjectStatus(statusUrl);
  const [activeView, setActiveView] = useState<ViewId>('overview');

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

  return (
    <main className="dashboard-container">
      <Header onReload={reload} />
      <TabNav active={activeView} onChange={setActiveView} />

      {activeView === 'overview' && (
        <OverviewView status={data} onOpenEngineering={() => setActiveView('engineering')} />
      )}
      {activeView === 'landscape' && <NotAvailableView {...NOT_AVAILABLE_COPY.landscape} />}
      {activeView === 'opportunities' && <NotAvailableView {...NOT_AVAILABLE_COPY.opportunities} />}
      {activeView === 'candidates' && <NotAvailableView {...NOT_AVAILABLE_COPY.candidates} />}
      {activeView === 'evidence' && <NotAvailableView {...NOT_AVAILABLE_COPY.evidence} />}
      {activeView === 'methodology' && <MethodologyView />}
      {activeView === 'reproducibility' && <ReproducibilityView status={data} />}
      {activeView === 'limitations' && <LimitationsView />}
      {activeView === 'engineering' && <EngineeringView status={data} />}
    </main>
  );
};
