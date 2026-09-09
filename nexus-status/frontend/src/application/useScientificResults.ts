import { useState, useEffect, useCallback } from 'react';
import type { ScientificResultsDocument } from '../domain/scientificResults';
import { fetchScientificResults } from '../infrastructure/scientificResultsHttpClient';

export type ScientificResultsLoadingState = 'loading' | 'success' | 'error';

export interface UseScientificResultsResult {
  state: ScientificResultsLoadingState;
  data: ScientificResultsDocument | null;
  error: Error | null;
  reload: () => void;
}

/**
 * Application hook for loading and observing the canonical Scientific Results Contract
 * (ADR 0025).
 *
 * Epistemic Invariant:
 * This hook NEVER calculates, alters, or overrides a published score, metric, or
 * verdict, and never mixes `discovery` and `verification` track data. It is an
 * unmediated ingest pipeline for the evidence published by Nexus core. A missing,
 * corrupt, or contract-violating artifact surfaces as an explicit `error` state — it
 * is never silently downgraded into a `success` state with empty result arrays.
 */
export function useScientificResults(url: string = './scientific_results.json'): UseScientificResultsResult {
  const [state, setState] = useState<ScientificResultsLoadingState>('loading');
  const [data, setData] = useState<ScientificResultsDocument | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [reloadTrigger, setReloadTrigger] = useState<number>(0);

  const reload = useCallback(() => {
    setReloadTrigger((prev) => prev + 1);
  }, []);

  useEffect(() => {
    let isMounted = true;
    setState('loading');
    setError(null);

    fetchScientificResults(url)
      .then((document) => {
        if (isMounted) {
          setData(document);
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
