import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ScientificDashboard } from '../../src/ui/ScientificDashboard';
import * as applicationHook from '../../src/application/useProjectStatus';
import * as scientificResultsHook from '../../src/application/useScientificResults';
import type { ProjectStatus } from '../../src/domain/status';
import type { ScientificResultsDocument } from '../../src/domain/scientificResults';

describe('ScientificDashboard UI', () => {
  const mockScientificResults: ScientificResultsDocument = {
    schema_version: '0.1.0',
    generated_at: '2026-09-09T11:26:54.982691Z',
    executions: [
      {
        execution_id: 'exec-0001',
        track: 'discovery',
        domain: 'solid_state_battery',
        query: 'solid electrolyte',
        created_at: '2026-09-09T11:26:54.982691Z',
        dataset_id: null,
        dataset_version: null,
        engine_commit: null,
        policy_id: null,
        policy_version: null,
        policy_sha256: null,
        source_provenance: [{ role: 'patents', kind: 'mock' }],
      },
    ],
    landscapes: [
      {
        execution_id: 'exec-0001',
        query: 'solid electrolyte',
        clusters: [
          {
            cluster: {
              cluster_id: 'H01M',
              label: 'Solid State Battery - H01M',
              representative_patents: ['US-11223001-B2'],
              patent_count: 3,
              white_space_score: 0.4608,
              is_white_space: false,
            },
            density: 1.0,
            recency: 0.7,
            citation_traction: 0.4722,
            citation_coverage: 1.0,
            demand_intensity: 1.0,
            quadrant: 'Quadrant II (Co-developed / Saturated)',
            mean_age_years: 6.0,
          },
        ],
        disclaimer: 'Nexus generated/discovered this output; not scientifically verified evidence.',
      },
    ],
    candidates: [],
    verifications: [],
    matches: [],
  };

  beforeEach(() => {
    vi.restoreAllMocks();
    // Default: scientific results load successfully. Tests that care about
    // Landscape's own loading/error/empty states override this explicitly.
    vi.spyOn(scientificResultsHook, 'useScientificResults').mockReturnValue({
      state: 'success',
      data: mockScientificResults,
      error: null,
      reload: vi.fn(),
    });
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

  it('marks Opportunities, Candidates and Evidence as not yet available', () => {
    vi.spyOn(applicationHook, 'useProjectStatus').mockReturnValue({
      state: 'success',
      data: mockSuccessStatus,
      error: null,
      reload: vi.fn(),
    });

    render(<ScientificDashboard />);

    for (const label of ['Opportunities', 'Candidates', 'Evidence']) {
      fireEvent.click(screen.getByRole('button', { name: label }));
      expect(screen.getAllByText(/not yet available/i).length).toBeGreaterThan(0);
    }
  });

  it('renders real published landscape data on the Landscape tab, not a not-available stub', () => {
    vi.spyOn(applicationHook, 'useProjectStatus').mockReturnValue({
      state: 'success',
      data: mockSuccessStatus,
      error: null,
      reload: vi.fn(),
    });

    render(<ScientificDashboard />);
    fireEvent.click(screen.getByRole('button', { name: 'Landscape' }));

    expect(screen.queryByText(/not yet available/i)).not.toBeInTheDocument();
    expect(screen.getByText('solid electrolyte')).toBeInTheDocument();
    expect(screen.getByText('Solid State Battery - H01M')).toBeInTheDocument();
    expect(screen.getByTestId('landscape-discovery-disclaimer')).toHaveTextContent(
      /not scientifically verified evidence/i
    );
  });

  it('shows Landscape\'s own error state without hiding the rest of a healthy dashboard', () => {
    vi.spyOn(applicationHook, 'useProjectStatus').mockReturnValue({
      state: 'success',
      data: mockSuccessStatus,
      error: null,
      reload: vi.fn(),
    });
    const scientificReload = vi.fn();
    vi.spyOn(scientificResultsHook, 'useScientificResults').mockReturnValue({
      state: 'error',
      data: null,
      error: new Error('HTTP 404: Not Found'),
      reload: scientificReload,
    });

    render(<ScientificDashboard />);

    // Overview (project_status-backed) still renders normally — one failing
    // artifact does not take down the whole dashboard.
    expect(screen.getByText(/what nexus does/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Landscape' }));
    expect(screen.getByTestId('landscape-error')).toBeInTheDocument();
    expect(screen.getByText(/HTTP 404: Not Found/i)).toBeInTheDocument();

    fireEvent.click(screen.getByTestId('landscape-error').querySelector('button')!);
    expect(scientificReload).toHaveBeenCalledTimes(1);
  });

  it('shows Landscape\'s own loading state independent of project_status', () => {
    vi.spyOn(applicationHook, 'useProjectStatus').mockReturnValue({
      state: 'success',
      data: mockSuccessStatus,
      error: null,
      reload: vi.fn(),
    });
    vi.spyOn(scientificResultsHook, 'useScientificResults').mockReturnValue({
      state: 'loading',
      data: null,
      error: null,
      reload: vi.fn(),
    });

    render(<ScientificDashboard />);
    fireEvent.click(screen.getByRole('button', { name: 'Landscape' }));
    expect(screen.getByTestId('landscape-loading')).toBeInTheDocument();
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
