import { useEffect, useState, useCallback } from "react";
import { getAnalyzeStatus, startAnalyze } from "../api/client";
import type { JobStatusResponse } from "../types/patent";

export type ViewState = "landing" | "executing" | "results" | "error" | "history";

export function useAnalyzeJob() {
  const [view, setView] = useState<ViewState>("landing");
  const [domain, setDomain] = useState<string>("");
  const [query, setQuery] = useState<string>("");
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<JobStatusResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [errorType, setErrorType] = useState<JobStatusResponse["error_type"] | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);

  const startAnalysis = useCallback(async (searchDomain: string, searchQuery: string) => {
    setIsLoading(true);
    setDomain(searchDomain);
    setQuery(searchQuery);
    setErrorMessage(null);
    setErrorType(null);

    try {
      const res = await startAnalyze(searchDomain, searchQuery);
      setJobId(res.job_id);
      setJobStatus({
        job_id: res.job_id,
        status: res.status as "running" | "done" | "error",
        stage: res.stage,
      });
      setView("executing");
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : "We couldn't start the analysis. Please try again.");
      setView("error");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (view !== "executing" || !jobId) return;
    let isMounted = true;

    const poll = async () => {
      try {
        const res = await getAnalyzeStatus(jobId);
        if (!isMounted) return;
        setJobStatus(res);

        if (res.status === "done") {
          setView("results");
        } else if (res.status === "error") {
          setErrorMessage(res.error || res.detail || "The analysis could not be completed.");
          setErrorType(res.error_type ?? null);
          setView("error");
        }
      } catch (err) {
        if (!isMounted) return;
        setErrorMessage(err instanceof Error ? err.message : "The analysis could not be completed.");
        setView("error");
      }
    };

    poll();
    const intervalId = setInterval(poll, 2000);
    return () => {
      isMounted = false;
      clearInterval(intervalId);
    };
  }, [view, jobId]);

  const reset = useCallback(() => {
    setView("landing");
    setJobId(null);
    setJobStatus(null);
    setErrorMessage(null);
    setErrorType(null);
  }, []);

  const retry = useCallback(() => {
    if (domain) void startAnalysis(domain, query);
    else reset();
  }, [domain, query, startAnalysis, reset]);

  const openHistory = useCallback(() => {
    setErrorMessage(null);
    setErrorType(null);
    setView("history");
  }, []);

  const openJob = useCallback(async (id: string) => {
    setErrorMessage(null);
    setErrorType(null);
    setIsLoading(true);
    try {
      const res = await getAnalyzeStatus(id);
      setJobId(id);
      setDomain(res.domain || "");
      setQuery(res.query || "");
      setJobStatus(res);

      if (res.status === "done") {
        setView("results");
      } else if (res.status === "error") {
        setErrorMessage(res.error || res.detail || "Job failed");
        setErrorType(res.error_type ?? null);
        setView("error");
      } else {
        setView("executing");
      }
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : "Couldn't load that analysis.");
      setView("error");
    } finally {
      setIsLoading(false);
    }
  }, []);

  return {
    view,
    setView,
    domain,
    query,
    jobId,
    jobStatus,
    errorMessage,
    errorType,
    isLoading,
    startAnalysis,
    reset,
    retry,
    openHistory,
    openJob,
  };
}
