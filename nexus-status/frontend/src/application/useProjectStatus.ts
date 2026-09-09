import { useState, useEffect, useCallback } from 'react';
import type { ProjectStatus } from '../domain/status';
import { fetchProjectStatus } from '../infrastructure/httpClient';

export type StatusLoadingState = 'loading' | 'success' | 'error';

export interface UseProjectStatusResult {
  state: StatusLoadingState;
  data: ProjectStatus | null;
  error: Error | null;
  reload: () => void;
}

/**
 * Application hook for loading and observing the canonical Project Status Contract.
 *
 * Epistemic Invariant:
 * This hook NEVER calculates, alters, or overrides the overall or dimension statuses.
 * It is an unmediated ingest pipeline for the verdict authored by the Nexus core.
 */
export function useProjectStatus(url: string = './project_status.json'): UseProjectStatusResult {
  const [state, setState] = useState<StatusLoadingState>('loading');
  const [data, setData] = useState<ProjectStatus | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [reloadTrigger, setReloadTrigger] = useState<number>(0);

  const reload = useCallback(() => {
    setReloadTrigger((prev) => prev + 1);
  }, []);

  useEffect(() => {
    let isMounted = true;
    setState('loading');
    setError(null);

    fetchProjectStatus(url)
      .then((statusPayload) => {
        if (isMounted) {
          setData(statusPayload);
          setError(null);
          setState('success');
        }
      })
      .catch((err: unknown) => {
        if (isMounted) {
          const resolvedError = err instanceof Error ? err : new Error(String(err));
          setError(resolvedError);
          setData(null);
          setState('error');
        }
      });

    return () => {
      isMounted = false;
    };
  }, [url, reloadTrigger]);

  return { state, data, error, reload };
}
