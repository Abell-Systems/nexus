import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { useProjectStatus } from '../../src/application/useProjectStatus';
import * as httpClient from '../../src/infrastructure/httpClient';
import type { ProjectStatus } from '../../src/domain/status';
import { ContractValidationError } from '../../src/domain/status';

describe('useProjectStatus (Application Hook)', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  const mockProjectStatus: ProjectStatus = {
    schema_version: '1.0.0',
    commit_sha: '1234567890abcdef',
    evaluated_at: '2026-09-09T10:00:00.000Z',
    overall_status: 'PASS',
    aggregation_rule: 'All required dimensions verified and passed.',
    summary: 'Nexus status verified.',
    dimensions: {
      backend_testing: {
        status: 'PASS',
        requirement_level: 'required',
        evidence_source: 'backend/test',
        evidence_available: true,
        checks: [
          { name: 'unit_tests', status: 'PASS' },
        ],
      },
      temporal_eligibility: {
        status: 'SKIPPED',
        requirement_level: 'optional',
        evidence_source: 'adrs/0022',
        evidence_available: true,
        checks: [],
      },
      external_auditing: {
        status: 'UNVERIFIED',
        requirement_level: 'optional',
        evidence_source: 'sonarcloud',
        evidence_available: false,
        checks: [],
      },
    },
  };

  it('initializes in loading state and resolves data on success', async () => {
    const fetchSpy = vi.spyOn(httpClient, 'fetchProjectStatus').mockResolvedValueOnce(mockProjectStatus);

    const { result } = renderHook(() => useProjectStatus('./project_status.json'));

    expect(result.current.state).toBe('loading');
    expect(result.current.data).toBeNull();
    expect(result.current.error).toBeNull();

    await waitFor(() => expect(result.current.state).toBe('success'));

    expect(result.current.data).toEqual(mockProjectStatus);
    expect(result.current.error).toBeNull();
    expect(fetchSpy).toHaveBeenCalledWith('./project_status.json');

    // Verify epistemic statuses are preserved faithfully without modification
    expect(result.current.data?.overall_status).toBe('PASS');
    expect(result.current.data?.dimensions.temporal_eligibility.status).toBe('SKIPPED');
    expect(result.current.data?.dimensions.external_auditing.status).toBe('UNVERIFIED');
  });

  it('transitions to error state when fetch fails', async () => {
    const fetchError = new httpClient.ProjectStatusFetchError('HTTP 404: Not Found', 404);
    vi.spyOn(httpClient, 'fetchProjectStatus').mockRejectedValueOnce(fetchError);

    const { result } = renderHook(() => useProjectStatus());

    await waitFor(() => expect(result.current.state).toBe('error'));

    expect(result.current.state).toBe('error');
    expect(result.current.data).toBeNull();
    expect(result.current.error).toBe(fetchError);
  });

  it('transitions to error state when contract validation fails', async () => {
    const validationError = new ContractValidationError('Missing commit_sha');
    vi.spyOn(httpClient, 'fetchProjectStatus').mockRejectedValueOnce(validationError);

    const { result } = renderHook(() => useProjectStatus());

    await waitFor(() => expect(result.current.state).toBe('error'));

    expect(result.current.state).toBe('error');
    expect(result.current.data).toBeNull();
    expect(result.current.error).toBe(validationError);
  });

  it('triggers a reload when reload() is called', async () => {
    const fetchSpy = vi
      .spyOn(httpClient, 'fetchProjectStatus')
      .mockResolvedValue(mockProjectStatus);

    const { result } = renderHook(() => useProjectStatus());

    await waitFor(() => expect(result.current.state).toBe('success'));
    expect(fetchSpy).toHaveBeenCalledTimes(1);

    await act(async () => {
      result.current.reload();
    });

    await waitFor(() => expect(fetchSpy).toHaveBeenCalledTimes(2));
    expect(result.current.state).toBe('success');
  });
});
