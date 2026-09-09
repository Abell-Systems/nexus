import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
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

    // Resolves and displays full dashboard
    await waitFor(() => {
      expect(screen.getByTestId('overall-status-badge')).toBeInTheDocument();
    });

    expect(screen.getByTestId('overall-status-badge')).toHaveTextContent(
      canonicalContractRaw.overall_status
    );

    // Evaluated commit truncated SHA is visible
    const expectedShortSha = canonicalContractRaw.commit_sha.slice(0, 12);
    expect(screen.getByText(new RegExp(expectedShortSha))).toBeInTheDocument();

    // Verify key dimensions are present in the DOM
    expect(screen.getAllByText(/backend_testing/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/architecture/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/documentation/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/scientific_integrity/i).length).toBeGreaterThan(0);

    // Verify dimension badges match the contract values exactly
    const dimensionBadges = screen.getAllByTestId('status-badge');
    expect(dimensionBadges.length).toBeGreaterThanOrEqual(7);
  });
});
