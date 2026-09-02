import { BrandHeader } from "./components/shared/BrandHeader";
import styles from "./components/UserZero/ErrorView.module.css";
import { ExecutionView } from "./components/UserZero/ExecutionView";
import { HistoryView } from "./components/UserZero/HistoryView";
import { LandingView } from "./components/UserZero/LandingView";
import { ResultsView } from "./components/UserZero/ResultsView";
import { useAnalyzeJob } from "./application/useAnalyzeJob";

export function App() {
  const {
    view,
    domain,
    jobStatus,
    errorMessage,
    errorType,
    isLoading,
    startAnalysis,
    reset,
    retry,
    openHistory,
    openJob,
  } = useAnalyzeJob();

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 flex flex-col font-sans">
      <BrandHeader domain={domain} />

      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8 flex flex-col justify-center">
        {view === "landing" && (
          <LandingView
            onStartAnalysis={startAnalysis}
            onOpenHistory={openHistory}
            isLoading={isLoading}
          />
        )}

        {view === "executing" && (
          <ExecutionView
            domain={domain}
            stage={jobStatus?.stage || "researching"}
            progress={jobStatus?.progress}
            events={jobStatus?.events}
            verdicts={jobStatus?.verdicts}
            candidates={jobStatus?.candidates}
          />
        )}

        {view === "results" && jobStatus && (
          <ResultsView
            domain={domain}
            result={jobStatus}
            onReset={reset}
          />
        )}

        {view === "history" && (
          <HistoryView
            onOpenJob={openJob}
            onBack={reset}
          />
        )}

        {view === "error" && (
          <div className={styles.errorContainer}>
            <div className={styles.errorCard}>
              <h2 className={styles.errorTitle}>Analysis Notice</h2>
              <p className={styles.errorMessage}>{errorMessage}</p>
              {errorType && (
                <span className={styles.errorBadge}>Type: {errorType}</span>
              )}
              <div className={styles.actions}>
                <button className={styles.retryButton} onClick={retry}>
                  Try Again
                </button>
                <button className={styles.backButton} onClick={reset}>
                  Back to Search
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
