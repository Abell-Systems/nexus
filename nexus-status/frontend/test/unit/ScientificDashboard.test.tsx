import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ScientificDashboard } from '../../src/ui/ScientificDashboard';
import * as applicationHook from '../../src/application/useProjectStatus';
import type { ProjectStatus } from '../../src/domain/status';

describe('ScientificDashboard UI', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  const mockSuccessStatus: ProjectStatus = {
    schema_version: '1.0.0',
    commit_sha: 'd1e2f3a4b5c67890',
    evaluated_at: '2026-09-09T10:15:30.000Z',
    overall_status: 'PASS',
    aggregation_rule: 'All required dimensions verified and passed.',
    summary: 'Nexus scientific invariants fully validated.',
    dimensions: {
      scientific_integrity: {
        status: 'PASS',
        requirement_level: 'required',
        evidence_source: 'docs/paper/results.json',
        evidence_available: true,
        message: 'All scientific hypotheses upheld.',
        metrics: {
          effect_size: 0.85,
          p_value: 0.001,
        },
        checks: [
          {
            name: 'wilcoxon_test',
            status: 'PASS',
            value: '0.001',
            threshold: '<= 0.05',
            detail: 'Statistically significant superiority',
          },
        ],
      },
      sonar_cloud: {
        status: 'UNVERIFIED',
        requirement_level: 'optional',
        evidence_source: 'sonarcloud.io',
        evidence_available: false,
        message: 'External token not provided in local environment',
        checks: [],
      },
      temporal_eligibility: {
        status: 'SKIPPED',
        requirement_level: 'optional',
        evidence_source: 'docs/adr/0022',
        evidence_available: true,
        checks: [],
      },
    },
  };

  it('renders loading indicator when status is loading', () => {
    vi.spyOn(applicationHook, 'useProjectStatus').mockReturnValue({
      state: 'loading',
      data: null,
      error: null,
      reload: vi.fn(),
    });

    render(<ScientificDashboard />);
    expect(screen.getByText(/loading scientific verification/i)).toBeInTheDocument();
  });

  it('renders error state with retry button when fetch or validation fails', () => {
    const reloadMock = vi.fn();
    vi.spyOn(applicationHook, 'useProjectStatus').mockReturnValue({
      state: 'error',
      data: null,
      error: new Error('Failed to load status: HTTP 500 Internal Server Error'),
      reload: reloadMock,
    });

    render(<ScientificDashboard />);
    expect(screen.getByText(/verification status unavailable/i)).toBeInTheDocument();
    expect(screen.getByText(/HTTP 500 Internal Server Error/i)).toBeInTheDocument();

    const retryBtn = screen.getByRole('button', { name: /retry/i });
    fireEvent.click(retryBtn);
    expect(reloadMock).toHaveBeenCalledTimes(1);
  });

  it('renders scientific overview by default without dominant engineering content', () => {
    vi.spyOn(applicationHook, 'useProjectStatus').mockReturnValue({
      state: 'success',
      data: mockSuccessStatus,
      error: null,
      reload: vi.fn(),
    });

    render(<ScientificDashboard />);

    expect(screen.getByText(/nexus scientific verification/i)).toBeInTheDocument();
    expect(screen.getByText(/what nexus does/i)).toBeInTheDocument();
    // Engineering-only content is not shown on the default Overview tab
    expect(screen.queryByText(/scientific_integrity/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/wilcoxon_test/i)).not.toBeInTheDocument();
  });

  it('renders full engineering dashboard on the Engineering tab, preserving all data faithfully', () => {
    vi.spyOn(applicationHook, 'useProjectStatus').mockReturnValue({
      state: 'success',
      data: mockSuccessStatus,
      error: null,
      reload: vi.fn(),
    });

    render(<ScientificDashboard />);
    fireEvent.click(screen.getByRole('button', { name: 'Engineering' }));

    // Overall Verdict
    expect(screen.getByTestId('overall-status-badge')).toHaveTextContent('PASS');
    expect(screen.getByText(/Nexus scientific invariants fully validated/i)).toBeInTheDocument();

    // Dimensions rendered
    expect(screen.getByText(/scientific_integrity/i)).toBeInTheDocument();
    expect(screen.getByText(/sonar_cloud/i)).toBeInTheDocument();
    expect(screen.getByText(/temporal_eligibility/i)).toBeInTheDocument();

    // Evidence & Provenance
    expect(screen.getByText(/docs\/paper\/results\.json/i)).toBeInTheDocument();
    expect(screen.getByText(/All scientific hypotheses upheld/i)).toBeInTheDocument();

    // Check item rendered
    expect(screen.getByText(/wilcoxon_test/i)).toBeInTheDocument();
    expect(screen.getByText(/Statistically significant superiority/i)).toBeInTheDocument();
  });

  it('shows evaluated commit sha on the Reproducibility tab', () => {
    vi.spyOn(applicationHook, 'useProjectStatus').mockReturnValue({
      state: 'success',
      data: mockSuccessStatus,
      error: null,
      reload: vi.fn(),
    });

    render(<ScientificDashboard />);
    fireEvent.click(screen.getByRole('button', { name: 'Reproducibility' }));

    expect(screen.getByText(mockSuccessStatus.commit_sha)).toBeInTheDocument();
  });

  it('marks Landscape, Opportunities, Candidates and Evidence as not yet available', () => {
    vi.spyOn(applicationHook, 'useProjectStatus').mockReturnValue({
      state: 'success',
      data: mockSuccessStatus,
      error: null,
      reload: vi.fn(),
    });

    render(<ScientificDashboard />);

    for (const label of ['Landscape', 'Opportunities', 'Candidates', 'Evidence']) {
      fireEvent.click(screen.getByRole('button', { name: label }));
      expect(screen.getAllByText(/not yet available/i).length).toBeGreaterThan(0);
    }
  });

  it('preserves epistemic statuses UNVERIFIED, SKIPPED, FAIL without recalculation', () => {
    const mixedStatus: ProjectStatus = {
      ...mockSuccessStatus,
      overall_status: 'UNVERIFIED', // Core verdict is UNVERIFIED
      dimensions: {
        ...mockSuccessStatus.dimensions,
        scientific_integrity: {
          ...mockSuccessStatus.dimensions.scientific_integrity,
          status: 'FAIL',
        },
      },
    };

    vi.spyOn(applicationHook, 'useProjectStatus').mockReturnValue({
      state: 'success',
      data: mixedStatus,
      error: null,
      reload: vi.fn(),
    });

    render(<ScientificDashboard />);
    fireEvent.click(screen.getByRole('button', { name: 'Engineering' }));

    // Overall verdict must faithfully reflect UNVERIFIED without recalculation
    expect(screen.getByTestId('overall-status-badge')).toHaveTextContent('UNVERIFIED');

    // Dimension badges
    const badges = screen.getAllByTestId('status-badge');
    const badgeTexts = badges.map((b) => b.textContent?.trim());
    expect(badgeTexts).toContain('FAIL');
    expect(badgeTexts).toContain('UNVERIFIED');
    expect(badgeTexts).toContain('SKIPPED');
  });
});
