import type {
  AdversarialVerdict,
  AgentEventItem,
  InventionCandidate,
  JobProgress,
  PipelineStage,
} from "../../types/patent";
import { BrandHeader } from "../shared/BrandHeader";
import { AgentActivityFeed } from "./AgentActivityFeed";
import styles from "./ExecutionView.module.css";

interface ExecutionViewProps {
  domain: string;
  stage: PipelineStage;
  progress?: JobProgress;
  events?: AgentEventItem[];
  verdicts?: AdversarialVerdict[];
  candidates?: InventionCandidate[];
}

export function ExecutionView({
  domain,
  stage,
  progress,
  events = [],
  verdicts = [],
  candidates = [],
}: ExecutionViewProps) {
  const stagesList = [
    {
      id: "researching",
      label: "Research patent landscape",
      metric: progress?.patentsAnalyzed ? `${progress.patentsAnalyzed.toLocaleString()} patents` : null,
    },
    {
      id: "clustering",
      label: "Find white-space",
      metric: progress?.clustersFound ? `${progress.clustersFound} opportunities` : null,
    },
    {
      id: "inventing",
      label: "Generate inventions",
      metric: progress?.candidatesGenerated ? `${progress.candidatesGenerated} candidates` : null,
    },
    {
      id: "adversarial",
      label: "Prior-art challenge",
      metric:
        progress?.candidatesRejected !== undefined || progress?.candidatesSurvived !== undefined
          ? `${progress?.candidatesRejected ?? 0} rejected / ${progress?.candidatesRevised ?? 0} revised / ${progress?.candidatesSurvived ?? 0} survived`
          : null,
    },
    {
      id: "governor",
      label: "Final assessment",
      metric: stage === "governor" || stage === "done" ? "Scores & evidence" : null,
    },
  ];

  const stageOrder: PipelineStage[] = [
    "queued",
    "researching",
    "clustering",
    "inventing",
    "adversarial",
    "governor",
    "done",
  ];

  const currentIdx = stageOrder.indexOf(stage);

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <BrandHeader />
        <h2 className={styles.domainTitle}>{domain}</h2>
      </header>

      <div className={styles.notice}>
        <p>The agent is trying to disprove its own inventions before recommending them.</p>
      </div>

      <div className={styles.pipeline}>
        {stagesList.map((st) => {
          const stIdx = stageOrder.indexOf(st.id as PipelineStage);
          let stateClass = styles.pending;
          let icon = "○";

          if (stIdx < currentIdx || stage === "done") {
            stateClass = styles.completed;
            icon = "✓";
          } else if (stIdx === currentIdx) {
            stateClass = styles.active;
            icon = "●";
          }

          return (
            <div key={st.id} className={`${styles.stepRow} ${stateClass}`}>
              <span className={styles.icon}>{icon}</span>
              <span className={styles.label}>{st.label}</span>
              <span className={styles.metric}>{st.metric || ""}</span>
            </div>
          );
        })}
      </div>

      {/* Task 3 — Self-Adversarial Loop Visualization */}
      {(verdicts.length > 0 || stage === "adversarial" || stage === "governor" || stage === "done") && (
        <div className={styles.adversarialBox}>
          <div className={styles.adversarialHeader}>
            <h3 className={styles.adversarialTitle}>INVENTION VALIDATION</h3>
            {candidates.length > 0 && (
              <span className={styles.candidateLabel}>
                Candidate #{candidates[0].candidate_id}: {candidates[0].title}
              </span>
            )}
            <div className={styles.killBanner}>
              ⚔ The agent is trying to kill its own invention.
            </div>
          </div>

          <div className={styles.attackFlow}>
            {verdicts.length === 0 ? (
              <div className={styles.attackStep}>
                <div className={styles.attackHeader}>
                  <span className={styles.attackTitle}>Attack #1</span>
                  <span className={styles.attackStatusPending}>In progress...</span>
                </div>
                <div className={styles.attackDetail}>Evaluating claims against patent landscape prior art.</div>
              </div>
            ) : (
              verdicts.map((v, idx) => {
                const vStr = (v.verdict || "").toLowerCase();
                const isRejected = vStr === "rejected";
                const isRevised = vStr === "revised" || vStr === "revise";

                let statusText = `✓ Survived`;
                let statusClass = styles.attackStatusSurvived;

                if (isRejected) {
                  statusText = `❌ Rejected`;
                  statusClass = styles.attackStatusRejected;
                } else if (isRevised) {
                  statusText = `↻ Revised`;
                  statusClass = styles.attackStatusRevised;
                }

                return (
                  <div key={`${v.candidate_id}-${idx}`}>
                    {idx > 0 && <div className={styles.arrowDown}>↓</div>}
                    <div className={styles.attackStep}>
                      <div className={styles.attackHeader}>
                        <span className={styles.attackTitle}>
                          Attack #{idx + 1} (Candidate #{v.candidate_id})
                        </span>
                        <span className={statusClass}>{statusText}</span>
                      </div>
                      {v.cited_patents && v.cited_patents.length > 0 && (
                        <div className={styles.citedPatents}>
                          Prior art: {v.cited_patents.join(", ")}
                        </div>
                      )}
                      {v.rationale && <div className={styles.attackDetail}>{v.rationale}</div>}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      )}

      {/* Task 2 — Activity Feed */}
      <AgentActivityFeed events={events} isLive={stage !== "done" && stage !== "error"} />
    </div>
  );
}

