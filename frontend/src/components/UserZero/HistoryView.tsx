import { useEffect, useState } from "react";
import { listAnalyzeJobs } from "../../api/client";
import type { JobSummary } from "../../types/patent";
import { BrandHeader } from "../shared/BrandHeader";
import styles from "./HistoryView.module.css";

interface HistoryViewProps {
  onOpenJob: (jobId: string) => void;
  onBack: () => void;
}

function formatDate(iso: string | null): string {
  if (!iso) return "Unknown time";
  return new Date(iso).toLocaleString();
}

function statusLabel(status: JobSummary["status"]): string {
  if (status === "done") return "Completed";
  if (status === "error") return "Failed";
  return "Running";
}

export function HistoryView({ onOpenJob, onBack }: HistoryViewProps) {
  const [jobs, setJobs] = useState<JobSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    listAnalyzeJobs()
      .then((res) => {
        if (isMounted) setJobs(res);
      })
      .catch((err) => {
        if (isMounted) setError(err instanceof Error ? err.message : "Failed to load past analyses.");
      });
    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <BrandHeader />
        <div className={styles.titleRow}>
          <h1 className={styles.title}>Past analyses</h1>
          <button type="button" className={styles.backBtn} onClick={onBack}>
            ← New analysis
          </button>
        </div>
      </header>

      {error && <p className={styles.error}>{error}</p>}

      {!error && jobs === null && <p className={styles.empty}>Loading past analyses…</p>}

      {jobs && jobs.length === 0 && (
        <p className={styles.empty}>No analyses yet. Run one from the landing page.</p>
      )}

      {jobs && jobs.length > 0 && (
        <ul className={styles.list}>
          {jobs.map((job) => (
            <li key={job.job_id} className={styles.item}>
              <button
                type="button"
                className={styles.itemBtn}
                onClick={() => onOpenJob(job.job_id)}
                disabled={job.status === "running"}
              >
                <div className={styles.itemMain}>
                  <span className={styles.itemDomain}>{job.domain || job.query || "Untitled analysis"}</span>
                  <span className={styles.itemQuery}>{job.query}</span>
                </div>
                <div className={styles.itemMeta}>
                  <span className={`${styles.statusBadge} ${styles[`status_${job.status}`]}`}>
                    {statusLabel(job.status)}
                  </span>
                  {job.status === "done" && (
                    <span className={styles.candidateCount}>{job.candidate_count} candidate(s)</span>
                  )}
                  <span className={styles.itemDate}>{formatDate(job.created_at)}</span>
                </div>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
