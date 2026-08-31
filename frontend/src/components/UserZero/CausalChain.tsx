import { useState } from "react";
import type {
  AdversarialVerdict,
  InventionCandidate,
  PatentCluster,
  ScoreCard,
} from "../../types/patent";
import styles from "./ResultsView.module.css";

export interface CausalChainProps {
  cluster?: PatentCluster;
  candidate?: InventionCandidate;
  verdict?: AdversarialVerdict;
  scorecard?: ScoreCard;
}

function formatScore(score?: number | null): string {
  if (score === undefined || score === null || Number.isNaN(score)) return "N/A";
  if (score <= 1) return `${Math.round(score * 100)}%`;
  return `${Math.round(score)}%`;
}

function getPatentUrl(pubNumber: string): string {
  const clean = pubNumber.replace(/[^A-Za-z0-9]/g, "");
  return `https://patents.google.com/patent/${clean}/en`;
}

export type NodeId =
  | "OPPORTUNITY"
  | "PRIOR ART"
  | "PRIOR-ART CHALLENGE"
  | "REVISION"
  | "SURVIVAL"
  | "EVIDENCE";

interface ChainNodeDef {
  id: NodeId;
  label: string;
  shortSummary: string;
}

function isCandidateSurvived(
  verdict?: AdversarialVerdict,
  scorecard?: ScoreCard
): boolean {
  if (!verdict) return false;
  const vStr = (verdict.verdict || "").toLowerCase();
  if (vStr !== "survives") return false;
  const summary = (scorecard?.summary || "").toLowerCase();
  if (
    summary.includes("directly anticipated") ||
    summary.includes("no room for novelty") ||
    summary.includes("cannot be recommended")
  ) {
    return false;
  }
  return true;
}

export function CausalChain({ cluster, candidate, verdict, scorecard }: CausalChainProps) {
  const [activeNode, setActiveNode] = useState<NodeId | "ALL">("OPPORTUNITY");

  const isSurvived = isCandidateSurvived(verdict, scorecard);

  // Consolidate challenging patents across verdict cited_patents and scorecard supporting_evidence
  const citedPatentsFromVerdict = verdict?.cited_patents || [];
  const supportingEvidenceFromScorecard = scorecard?.supporting_evidence || [];

  const extractedPatentsFromEvidence = supportingEvidenceFromScorecard
    .map((item) => {
      const match = item.match(/\b(US-[A-Za-z0-9-]+)\b/);
      return match ? match[1] : item.trim();
    })
    .filter((item) => item.length > 0 && item.startsWith("US-"));

  const effectiveChallengingPatents = Array.from(
    new Set([...citedPatentsFromVerdict, ...extractedPatentsFromEvidence])
  );

  const hasValidWhiteSpaceScore =
    cluster?.white_space_score !== undefined &&
    cluster?.white_space_score !== null &&
    !Number.isNaN(cluster.white_space_score);

  const nodes: ChainNodeDef[] = [
    {
      id: "OPPORTUNITY",
      label: "OPPORTUNITY",
      shortSummary: cluster?.label
        ? `${cluster.label} (${hasValidWhiteSpaceScore ? `Score: ${formatScore(cluster.white_space_score)}` : "Score: N/A"})`
        : "Identified White Space",
    },
    {
      id: "PRIOR ART",
      label: "PRIOR ART",
      shortSummary: cluster?.representative_patents?.length
        ? `${cluster.representative_patents.length} representative patents`
        : "Surveyed Prior Art",
    },
    {
      id: "PRIOR-ART CHALLENGE",
      label: "PRIOR-ART CHALLENGE",
      shortSummary: effectiveChallengingPatents.length
        ? `${effectiveChallengingPatents.length} challenging patents cited`
        : "Adversarial Objections",
    },
    {
      id: "REVISION",
      label: "REVISION",
      shortSummary: candidate?.claimed_novelty
        ? "Narrowed novelty claims"
        : "Claim Adaptation",
    },
    {
      id: "SURVIVAL",
      label: "SURVIVAL",
      shortSummary: isSurvived
        ? "Survives prior-art challenge"
        : "Failed prior-art challenge",
    },
    {
      id: "EVIDENCE",
      label: "EVIDENCE",
      shortSummary:
        scorecard?.evidence !== undefined
          ? `Confidence ${formatScore(scorecard.evidence)}`
          : "Supporting Citations",
    },
  ];

  function renderPatentList(patents: string[] | undefined, emptyText: string) {
    if (!patents || patents.length === 0) {
      return <p className={styles.emptyNote}>{emptyText}</p>;
    }
    return (
      <div className={styles.patentList}>
        {patents.map((pat) => (
          <a
            key={pat}
            href={getPatentUrl(pat)}
            target="_blank"
            rel="noopener noreferrer"
            className={styles.patentBadge}
            title={`View ${pat} on Google Patents`}
          >
            <span>{pat}</span>
            <span className={styles.externalIcon}>↗</span>
          </a>
        ))}
      </div>
    );
  }

  function renderNodeCard(nodeId: NodeId) {
    switch (nodeId) {
      case "OPPORTUNITY":
        return (
          <div key="OPPORTUNITY" className={styles.nodeCard}>
            <div className={styles.nodeCardHeader}>
              <span className={styles.nodeTag}>1. OPPORTUNITY</span>
              <h4 className={styles.nodeCardTitle}>
                {cluster?.label || "Target Cluster"}
              </h4>
              <p style={{ fontSize: "0.8rem", color: "#94a3b8", margin: "0.25rem 0 0 0" }}>
                Question: Why does this opportunity exist? (¿Por qué existe esta oportunidad?)
              </p>
            </div>
            <div className={styles.nodeCardBody}>
              {cluster ? (
                <>
                  <div className={styles.metaRow}>
                    <div className={styles.metaItem}>
                      <span className={styles.metaLabel}>White-Space Score</span>
                      <span className={styles.metaValueHighlight}>
                        {formatScore(cluster.white_space_score)}
                      </span>
                    </div>
                    <div className={styles.metaItem}>
                      <span className={styles.metaLabel}>Cluster Density</span>
                      <span className={styles.metaValue}>
                        {cluster.patent_count !== undefined
                          ? `${cluster.patent_count} patents analyzed`
                          : "Uncrowded area"}
                      </span>
                    </div>
                    <div className={styles.metaItem}>
                      <span className={styles.metaLabel}>Opportunity Status</span>
                      <span className={styles.metaValue}>
                        {hasValidWhiteSpaceScore
                          ? "High-potential white space"
                          : "White-space unvalidated (Evidence unavailable)"}
                      </span>
                    </div>
                  </div>
                  <p className={styles.nodeText}>
                    {hasValidWhiteSpaceScore
                      ? "The agent identified an under-explored technology boundary with low prior-art saturation and favorable white-space differentiation potential."
                      : "The agent surveyed baseline patents in this cluster; quantitative white-space score is unavailable."}
                  </p>
                </>
              ) : (
                <p className={styles.emptyNote}>Evidence unavailable for this step.</p>
              )}
            </div>
          </div>
        );

      case "PRIOR ART":
        return (
          <div key="PRIOR ART" className={styles.nodeCard}>
            <div className={styles.nodeCardHeader}>
              <span className={styles.nodeTag}>2. PRIOR ART</span>
              <h4 className={styles.nodeCardTitle}>Baseline Landscape Patents</h4>
              <p style={{ fontSize: "0.8rem", color: "#94a3b8", margin: "0.25rem 0 0 0" }}>
                Question: What prior art did the agent survey? (¿Qué conocía el agente?)
              </p>
            </div>
            <div className={styles.nodeCardBody}>
              <p className={styles.nodeText}>
                Representative patents establishing the existing technology baseline in this cluster:
              </p>
              {renderPatentList(
                cluster?.representative_patents,
                "Evidence unavailable for this step.",
              )}
            </div>
          </div>
        );

      case "PRIOR-ART CHALLENGE":
        return (
          <div key="PRIOR-ART CHALLENGE" className={styles.nodeCard}>
            <div className={styles.nodeCardHeader}>
              <span className={`${styles.nodeTag} ${styles.challengeTag}`}>
                3. PRIOR-ART CHALLENGE
              </span>
              <h4 className={styles.nodeCardTitle}>Adversarial Invalidation Attack</h4>
              <p style={{ fontSize: "0.8rem", color: "#94a3b8", margin: "0.25rem 0 0 0" }}>
                Question: What did the agent attempt to attack? (¿Qué intentó destruir?)
              </p>
            </div>
            <div className={styles.nodeCardBody}>
              <p className={styles.nodeText}>
                The adversarial examiner challenged the candidate against prior-art citations to test novelty and obviousness:
              </p>
              {renderPatentList(
                effectiveChallengingPatents.length > 0
                  ? effectiveChallengingPatents
                  : cluster?.representative_patents?.slice(0, 2),
                "Evidence unavailable for this step.",
              )}
              {verdict?.rationale ? (
                <div className={styles.quoteBox}>
                  <span className={styles.quoteLabel}>Examiner Objection:</span>
                  <p className={styles.quoteText}>{verdict.rationale}</p>
                </div>
              ) : (
                <p className={styles.emptyNote}>Evidence unavailable for this step.</p>
              )}
            </div>
          </div>
        );

      case "REVISION":
        return (
          <div key="REVISION" className={styles.nodeCard}>
            <div className={styles.nodeCardHeader}>
              <span className={styles.nodeTag}>4. REVISION</span>
              <h4 className={styles.nodeCardTitle}>Claim Adaptation & Narrowing</h4>
              <p style={{ fontSize: "0.8rem", color: "#94a3b8", margin: "0.25rem 0 0 0" }}>
                Question: What claims were revised? (¿Qué cambió?)
              </p>
            </div>
            <div className={styles.nodeCardBody}>
              <p className={styles.nodeText}>
                The candidate claims were refined to differentiate specifically over the cited prior-art mechanisms:
              </p>
              {candidate?.claimed_novelty ? (
                <div className={styles.calloutBox}>
                  <span className={styles.calloutLabel}>Claimed Novelty:</span>
                  <p className={styles.calloutText}>{candidate.claimed_novelty}</p>
                </div>
              ) : (
                <p className={styles.emptyNote}>Evidence unavailable for this step.</p>
              )}
            </div>
          </div>
        );

      case "SURVIVAL":
        return (
          <div key="SURVIVAL" className={styles.nodeCard}>
            <div className={styles.nodeCardHeader}>
              <span
                className={`${styles.nodeTag} ${
                  isSurvived ? styles.survivalTag : styles.challengeTag
                }`}
              >
                5. SURVIVAL
              </span>
              <h4 className={styles.nodeCardTitle}>
                {isSurvived
                  ? "Survives Prior-Art Challenge"
                  : "Rejected — Anticipated by Prior Art"}
              </h4>
              <p style={{ fontSize: "0.8rem", color: "#94a3b8", margin: "0.25rem 0 0 0" }}>
                Question: Why did this invention survive? (¿Por qué pasó?)
              </p>
            </div>
            <div className={styles.nodeCardBody}>
              <p className={styles.nodeText}>
                {isSurvived
                  ? "Differentiation rationale confirming the candidate successfully overcame the adversarial challenge:"
                  : "Adversarial evaluation determined that the candidate is directly anticipated by pre-existing patents in the landscape:"}
              </p>
              {isSurvived ? (
                candidate?.claimed_novelty || verdict?.rationale ? (
                  <div className={styles.quoteBox}>
                    <span className={styles.quoteLabel}>Differentiation Rationale:</span>
                    <p className={styles.quoteText}>
                      {candidate?.claimed_novelty || verdict?.rationale}
                    </p>
                  </div>
                ) : (
                  <p className={styles.emptyNote}>Evidence unavailable for this step.</p>
                )
              ) : (
                <div className={styles.quoteBox} style={{ borderColor: "#ef4444" }}>
                  <span className={styles.quoteLabel} style={{ color: "#ef4444" }}>
                    Rejection Finding:
                  </span>
                  <p className={styles.quoteText}>
                    {scorecard?.summary ||
                      verdict?.rationale ||
                      "The candidate claims were anticipated by prior art publications and cannot be recommended."}
                  </p>
                </div>
              )}
            </div>
          </div>
        );

      case "EVIDENCE":
        return (
          <div key="EVIDENCE" className={styles.nodeCard}>
            <div className={styles.nodeCardHeader}>
              <span className={styles.nodeTag}>6. EVIDENCE</span>
              <h4 className={styles.nodeCardTitle}>
                Supporting Citations & Assessment Scores
              </h4>
              <p style={{ fontSize: "0.8rem", color: "#94a3b8", margin: "0.25rem 0 0 0" }}>
                Question: What evidence proves this score? (¿Qué lo demuestra?)
              </p>
            </div>
            <div className={styles.nodeCardBody}>
              {scorecard ? (
                <>
                  {scorecard.summary && (
                    <div className={styles.summaryBox}>
                      <span className={styles.summaryLabel}>Final Assessment:</span>
                      <p className={styles.summaryText}>{scorecard.summary}</p>
                    </div>
                  )}
                  {scorecard.supporting_evidence && scorecard.supporting_evidence.length > 0 && (
                    <div className={styles.evidenceSection}>
                      <span className={styles.metaLabel}>Supporting Evidence Citations:</span>
                      <ul className={styles.evidenceList}>
                        {scorecard.supporting_evidence.map((item, idx) => (
                          <li key={idx} className={styles.evidenceItem}>
                            {item}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  <div className={styles.scoresRow}>
                    <div className={styles.scorePill}>
                      <span className={styles.scorePillLabel}>Novelty</span>
                      <span className={styles.scorePillVal}>
                        {formatScore(scorecard.novelty)}
                      </span>
                    </div>
                    <div className={styles.scorePill}>
                      <span className={styles.scorePillLabel}>Prior-Art Risk</span>
                      <span className={styles.scorePillVal}>
                        {formatScore(scorecard.prior_art_risk)}
                      </span>
                    </div>
                    <div className={styles.scorePill}>
                      <span className={styles.scorePillLabel}>Differentiation</span>
                      <span className={styles.scorePillVal}>
                        {formatScore(scorecard.differentiation)}
                      </span>
                    </div>
                    <div className={styles.scorePill}>
                      <span className={styles.scorePillLabel}>Evidence</span>
                      <span className={styles.scorePillVal}>
                        {formatScore(scorecard.evidence)}
                      </span>
                    </div>
                  </div>
                </>
              ) : (
                <p className={styles.emptyNote}>Evidence unavailable for this step.</p>
              )}
            </div>
          </div>
        );
    }
  }

  return (
    <div className={styles.causalChainContainer}>
      <div className={styles.chainControls}>
        <span className={styles.chainTitle}>Causal Chain Trace</span>
        <button
          type="button"
          className={styles.viewAllBtn}
          onClick={() =>
            setActiveNode((prev) => (prev === "ALL" ? "OPPORTUNITY" : "ALL"))
          }
        >
          {activeNode === "ALL" ? "Show step by step" : "Expand all 6 steps"}
        </button>
      </div>

      <nav className={styles.pipelineNav} aria-label="Causal chain pipeline">
        {nodes.map((node, idx) => {
          const isSelected = activeNode === node.id || activeNode === "ALL";
          return (
            <div key={node.id} className={styles.pipelineStepWrapper}>
              <button
                type="button"
                className={`${styles.stepButton} ${
                  isSelected ? styles.stepButtonActive : ""
                }`}
                onClick={() => setActiveNode(node.id)}
                aria-current={activeNode === node.id ? "step" : undefined}
              >
                <span className={styles.stepNum}>{idx + 1}</span>
                <div className={styles.stepInfo}>
                  <span className={styles.stepLabel}>{node.label}</span>
                  <span className={styles.stepSummary}>{node.shortSummary}</span>
                </div>
              </button>
              {idx < nodes.length - 1 && (
                <span className={styles.stepArrow} aria-hidden="true">
                  ➔
                </span>
              )}
            </div>
          );
        })}
      </nav>

      <div className={styles.chainDetails}>
        {activeNode === "ALL"
          ? nodes.map((n) => renderNodeCard(n.id))
          : renderNodeCard(activeNode)}
      </div>
    </div>
  );
}
