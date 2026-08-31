import { useEffect, useState } from "react";
import { getAnalyzeStatus, startAnalyze } from "./api/client";
import { BrandHeader } from "./components/shared/BrandHeader";
import styles from "./components/UserZero/ErrorView.module.css";
import { ExecutionView } from "./components/UserZero/ExecutionView";
import { HistoryView } from "./components/UserZero/HistoryView";
import { LandingView } from "./components/UserZero/LandingView";
import { ResultsView } from "./components/UserZero/ResultsView";
import type { JobStatusResponse } from "./types/patent";

type ViewState = "landing" | "executing" | "results" | "error" | "history";

export function App() {
  const [view, setView] = useState<ViewState>("landing");
  const [domain, setDomain] = useState<string>("");
  const [query, setQuery] = useState<string>("");
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<JobStatusResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [errorType, setErrorType] = useState<JobStatusResponse["error_type"] | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);

  const handleStartAnalysis = async (searchDomain: string, searchQuery: string) => {
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
  };

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

  const handleReset = () => {
    setView("landing");
    setJobId(null);
    setJobStatus(null);
    setErrorMessage(null);
    setErrorType(null);
  };

  const handleRetry = () => {
    if (domain) void handleStartAnalysis(domain, query);
    else handleReset();
  };

  const handleOpenHistory = () => {
    setErrorMessage(null);
    setErrorType(null);
    setView("history");
  };

  // Reopens a past job's already-computed result -- a single GET against the
  // in-memory job store, no new agent run.
  const handleOpenJob = async (id: string) => {
    try {
      const res = await getAnalyzeStatus(id);
      setJobId(id);
      setJobStatus(res);
      setDomain(res.domain || "");
      setQuery(res.query || "");
      if (res.status === "error") {
        setErrorMessage(res.error || res.detail || "This analysis failed.");
        setErrorType(res.error_type ?? null);
        setView("error");
      } else {
        setView("results");
      }
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : "Couldn't load that analysis.");
      setView("error");
    }
  };

  if (view === "history") {
    return <HistoryView onOpenJob={handleOpenJob} onBack={handleReset} />;
  }

  if (view === "executing") {
    return (
      <ExecutionView
        domain={domain}
        stage={jobStatus?.stage || "queued"}
        progress={jobStatus?.progress}
        events={jobStatus?.events}
        verdicts={jobStatus?.verdicts}
        candidates={jobStatus?.candidates}
      />
    );
  }

  if (view === "results" && jobStatus) {
    return <ResultsView domain={domain} result={jobStatus} onReset={handleReset} />;
  }

  if (view === "error") {
    const isQuotaExhausted = errorType === "quota_exhausted";
    const isPermissionError = errorMessage?.includes("PERMISSION_DENIED") || errorMessage?.includes("aiplatform.endpoints.predict");
    const isUnsupportedDomain = errorMessage?.includes("outside that scope");

    return (
      <main className={styles.container}>
        <header className={styles.header}>
          <BrandHeader domain={domain || undefined} />
          <div className={styles.eyebrow}>ANALYSIS STATUS</div>
          <h1 className={styles.title}>
            {isQuotaExhausted
              ? "AI usage limit reached"
              : isPermissionError
                ? "AI agent needs access"
                : isUnsupportedDomain
                  ? "This domain isn't covered yet"
                  : "We couldn't complete the analysis."}
          </h1>
          <p className={styles.subtitle}>
            {isQuotaExhausted
              ? "Your research request is safe. The model quota is temporarily unavailable."
              : isPermissionError
                ? "The analysis engine is deployed, but its Cloud AI permission is not ready yet."
                : isUnsupportedDomain
                  ? "This demo's patent data is scoped to one technology domain."
                  : "Your opportunity wasn't lost. You can retry the analysis or start a new one."}
          </p>
        </header>

        <section className={styles.card} aria-label="Analysis status">
          <div className={styles.statusRow}>
            <span className={styles.statusDot} />
            <span>{isPermissionError ? "Deployment configuration issue" : isUnsupportedDomain ? "Domain out of scope" : "Analysis interrupted"}</span>
          </div>
          <p className={styles.message}>
            {isPermissionError
              ? "The service account running Cloud Run cannot currently call the configured Gemini model through Vertex AI. The deployment configuration has been corrected; redeploying the service will apply it."
              : isQuotaExhausted
                ? "Please wait a moment and try again."
                : isUnsupportedDomain
                  ? "Try \"Solid-state electrolytes for EV batteries\" — that's the domain this demo has real patent data for."
                  : "The agent returned an unexpected error while processing this opportunity."}
          </p>
          {errorMessage && !isPermissionError && (
            <details className={styles.technical}>
              <summary>Technical details</summary>
              <code>{errorMessage}</code>
            </details>
          )}
        </section>

        <div className={styles.actions}>
          {!isQuotaExhausted && (
            <button type="button" className={styles.primaryBtn} onClick={handleRetry}>Try again</button>
          )}
          <button type="button" className={styles.secondaryBtn} onClick={handleReset}>← Analyze another opportunity</button>
        </div>
      </main>
    );
  }

  return (
    <LandingView
      onStartAnalysis={handleStartAnalysis}
      onOpenHistory={handleOpenHistory}
      isLoading={isLoading}
    />
  );
}

export default App;
