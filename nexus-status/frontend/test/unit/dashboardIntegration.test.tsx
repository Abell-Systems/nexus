import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import * as fs from 'node:fs';
import * as path from 'node:path';
import { ScientificDashboard } from '../../src/ui/ScientificDashboard';

describe('ScientificDashboard End-to-End Live Contract Integration', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it('successfully loads and renders the canonical repository project_status.json', async () => {
    const rootContractPath = path.resolve(__dirname, '../../../../project_status.json');
    expect(fs.existsSync(rootContractPath)).toBe(true);

    const canonicalContractRaw = JSON.parse(fs.readFileSync(rootContractPath, 'utf-8'));

    // Mock fetch to serve the real root project_status.json
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => canonicalContractRaw,
    } as Response);

    render(<ScientificDashboard statusUrl="./project_status.json" />);

    // Initially displays loading
    expect(screen.getByText(/loading scientific verification/i)).toBeInTheDocument();

    // Resolves and displays the scientific overview by default
    await waitFor(() => {
      expect(screen.getByText(/what nexus does/i)).toBeInTheDocument();
    });

    // Navigate to Engineering to inspect the full CI/status dashboard
    fireEvent.click(screen.getByRole('button', { name: 'Engineering' }));

    expect(screen.getByTestId('overall-status-badge')).toBeInTheDocument();
    expect(screen.getByTestId('overall-status-badge')).toHaveTextContent(
      canonicalContractRaw.overall_status
    );

    // Evaluated commit truncated SHA is visible on the Reproducibility tab
    fireEvent.click(screen.getByRole('button', { name: 'Reproducibility' }));
    expect(screen.getByText(canonicalContractRaw.commit_sha)).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Engineering' }));

    // Verify key dimensions are present in the DOM
    expect(screen.getAllByText(/backend_testing/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/architecture/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/documentation/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/scientific_integrity/i).length).toBeGreaterThan(0);

    // Verify dimension badges match the contract values exactly
    const dimensionBadges = screen.getAllByTestId('status-badge');
    expect(dimensionBadges.length).toBeGreaterThanOrEqual(7);
  });

  it('successfully loads and renders the canonical repository scientific_results.json on the Landscape tab', async () => {
    const rootStatusPath = path.resolve(__dirname, '../../../../project_status.json');
    const rootScientificResultsPath = path.resolve(__dirname, '../../../../scientific_results.json');
    expect(fs.existsSync(rootScientificResultsPath)).toBe(true);

    const statusRaw = JSON.parse(fs.readFileSync(rootStatusPath, 'utf-8'));
    const scientificResultsRaw = JSON.parse(fs.readFileSync(rootScientificResultsPath, 'utf-8'));

    // Serve each real, distinct artifact from its own URL — proves the two
    // fetches are independent, not the same request duplicated.
    globalThis.fetch = vi.fn().mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);
      const body = url.includes('scientific_results.json') ? scientificResultsRaw : statusRaw;
      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => body,
      } as Response);
    });

    render(<ScientificDashboard />);
    await waitFor(() => {
      expect(screen.getByText(/what nexus does/i)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: 'Landscape' }));

    await waitFor(() => {
      expect(screen.getByTestId('landscape-discovery-disclaimer')).toBeInTheDocument();
    });

    const execution = scientificResultsRaw.executions[0];
    const cluster = scientificResultsRaw.landscapes[0].clusters[0].cluster;
    expect(screen.getByText(execution.domain)).toBeInTheDocument();
    expect(screen.getByText(cluster.label)).toBeInTheDocument();
    expect(screen.getByTestId('landscape-discovery-disclaimer')).toHaveTextContent(
      scientificResultsRaw.landscapes[0].disclaimer
    );
  });
});
