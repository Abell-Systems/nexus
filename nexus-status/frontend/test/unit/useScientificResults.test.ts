import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { useScientificResults } from '../../src/application/useScientificResults';
import * as httpClient from '../../src/infrastructure/scientificResultsHttpClient';
import type { ScientificResultsDocument } from '../../src/domain/scientificResults';
import { ScientificResultsValidationError } from '../../src/domain/scientificResults';

describe('useScientificResults (Application Hook)', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  const mockDocument: ScientificResultsDocument = {
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
    landscapes: [],
    candidates: [],
    verifications: [],
    matches: [],
  };

  it('initializes in loading state and resolves data on success', async () => {
    const fetchSpy = vi
      .spyOn(httpClient, 'fetchScientificResults')
      .mockResolvedValueOnce(mockDocument);

    const { result } = renderHook(() => useScientificResults('./scientific_results.json'));

    expect(result.current.state).toBe('loading');
    expect(result.current.data).toBeNull();
    expect(result.current.error).toBeNull();

    await waitFor(() => expect(result.current.state).toBe('success'));

    expect(result.current.data).toEqual(mockDocument);
    expect(result.current.error).toBeNull();
    expect(fetchSpy).toHaveBeenCalledWith('./scientific_results.json');

    // The hook must preserve the track distinction faithfully, not merge or infer it.
    expect(result.current.data?.executions[0].track).toBe('discovery');
  });

  it('transitions to an explicit error state when the artifact is missing (404), not an empty success', async () => {
    const fetchError = new httpClient.ScientificResultsFetchError('HTTP 404: Not Found', 404);
    vi.spyOn(httpClient, 'fetchScientificResults').mockRejectedValueOnce(fetchError);

    const { result } = renderHook(() => useScientificResults());

    await waitFor(() => expect(result.current.state).toBe('error'));

    expect(result.current.state).toBe('error');
    expect(result.current.data).toBeNull();
    expect(result.current.error).toBe(fetchError);
  });

  it('transitions to an explicit error state when the artifact violates the contract', async () => {
    const validationError = new ScientificResultsValidationError('Missing schema_version');
    vi.spyOn(httpClient, 'fetchScientificResults').mockRejectedValueOnce(validationError);

    const { result } = renderHook(() => useScientificResults());

    await waitFor(() => expect(result.current.state).toBe('error'));

    expect(result.current.state).toBe('error');
    expect(result.current.data).toBeNull();
    expect(result.current.error).toBe(validationError);
  });

  it('triggers a reload when reload() is called', async () => {
    const fetchSpy = vi
      .spyOn(httpClient, 'fetchScientificResults')
      .mockResolvedValue(mockDocument);

    const { result } = renderHook(() => useScientificResults());

    await waitFor(() => expect(result.current.state).toBe('success'));
    expect(fetchSpy).toHaveBeenCalledTimes(1);

    await act(async () => {
      result.current.reload();
    });

    await waitFor(() => expect(fetchSpy).toHaveBeenCalledTimes(2));
    expect(result.current.state).toBe('success');
  });
});
