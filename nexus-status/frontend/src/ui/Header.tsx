import React from 'react';

export interface HeaderProps {
  onReload: () => void;
}

export const Header: React.FC<HeaderProps> = ({ onReload }) => {
  return (
    <header className="dashboard-header">
      <div className="header-top-row">
        <div>
          <div className="system-identity">Abell Nexus</div>
          <h1 className="header-title">Nexus Scientific Verification</h1>
          <p className="header-subtitle">
            A scientific verification workspace for understanding and auditing the
            evidence produced by Nexus.
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
    </header>
  );
};
