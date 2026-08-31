import type { AgentEventItem } from "../../types/patent";
import styles from "./AgentActivityFeed.module.css";

interface AgentActivityFeedProps {
  events?: AgentEventItem[];
  isLive?: boolean;
}

export function AgentActivityFeed({ events = [], isLive = false }: AgentActivityFeedProps) {
  if (!events || events.length === 0) {
    return (
      <div className={styles.container}>
        <div className={styles.header}>
          <h3 className={styles.title}>AGENT ACTIVITY FEED</h3>
          {isLive && (
            <div className={styles.liveIndicator}>
              <span className={styles.dot} />
              <span>LIVE</span>
            </div>
          )}
        </div>
        <p className={styles.emptyState}>
          {isLive ? "Waiting for the agent's first move…" : "No activity recorded for this run."}
        </p>
      </div>
    );
  }

  function getEventStyle(type: string) {
    switch (type) {
      case "candidate_challenged":
        return { icon: "⚔", className: styles.iconChallenge };
      case "candidate_rejected":
        return { icon: "❌", className: styles.iconRejected };
      case "candidate_revised":
        return { icon: "↻", className: styles.iconRevised };
      case "candidate_survived":
      case "research_completed":
      case "landscape_clustered":
      case "candidate_generated":
      case "assessment_completed":
        return { icon: "✓", className: styles.iconSurvived };
      default:
        return { icon: "●", className: styles.iconDefault };
    }
  }

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h3 className={styles.title}>AGENT ACTIVITY FEED</h3>
        {isLive && (
          <div className={styles.liveIndicator}>
            <span className={styles.dot} />
            <span>LIVE AGENT TELEMETRY</span>
          </div>
        )}
      </div>

      <div className={styles.feedList}>
        {events.map((evt, idx) => {
          if (!evt || typeof evt !== "object") return null;
          const { icon, className } = getEventStyle(evt.type || "");
          const formattedTime = evt.timestamp
            ? new Date(evt.timestamp).toLocaleTimeString()
            : null;

          return (
            <div key={`${evt.type}-${idx}`} className={styles.feedItem}>
              <span className={`${styles.icon} ${className}`}>{icon}</span>
              <div className={styles.content}>
                <div className={styles.message}>
                  {evt.message || "Activity logged."}
                </div>
                {formattedTime && (
                  <div className={styles.timestamp}>{formattedTime}</div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
