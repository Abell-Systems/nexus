import { useState } from "react";
import type { AdversarialVerdict, JobStatusResponse, ScoreCard } from "../../types/patent";
import { BrandHeader } from "../shared/BrandHeader";
import { CausalChain } from "./CausalChain";
import styles from "./ResultsView.module.css";

function formatScore(score?: number | null): string {
  if (score === undefined || score === null || Number.isNaN(score)) return "N/A";
  if (score <= 1) return `${Math.round(score * 100)}%`;
  return `${Math.round(score)}%`;
}

function getPatentUrl(pubNumber: string): string {
  const clean = pubNumber.replace(/[^A-Za-z0-9]/g, "");
  return `https://patents.google.com/patent/${clean}/en`;
}

// One human-readable sentence for the executive summary, before any
// chemistry/patent terminology -- prefers the scorecard's assessment over
// the raw candidate description since it already reads as a verdict.
function firstSentence(text: string, maxLen = 180): string {
  const sentence = text.split(/(?<=[.!?])\s/)[0] || text;
  if (sentence.length <= maxLen) return sentence;
  const truncated = sentence.slice(0, maxLen);
  const lastSpace = truncated.lastIndexOf(" ");
  return `${truncated.slice(0, lastSpace > 0 ? lastSpace : maxLen)}…`;
}

export interface ResultsViewProps {
  domain?: string;
  result: JobStatusResponse;
  onReset?: () => void;
}

export function ResultsView({ domain, result, onReset }: ResultsViewProps) {
  const [showCausalChain, setShowCausalChain] = useState(false);
  const [showDetails, setShowDetails] = useState(false);

  const candidates = result.candidates || [];
  const verdicts = result.verdicts || [];
  const scorecards = result.scorecards || [];
  const clusters = result.clusters || [];

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

  // Filter candidates prioritizing surviving ones
  const survivingCandidates = candidates.filter((c) => {
    const v = verdicts.find((verdict) => verdict.candidate_id === c.candidate_id);
    const sc = scorecards.find((scorecard) => scorecard.candidate_id === c.candidate_id);
    return isCandidateSurvived(v, sc);
  });

  const displayCandidates = survivingCandidates.length > 0 ? survivingCandidates : candidates;

  const [selectedCandidateId, setSelectedCandidateId] = useState<string>(
    displayCandidates[0]?.candidate_id || ""
  );

  const currentCandidate =
    candidates.find((c) => c.candidate_id === selectedCandidateId) ||
    displayCandidates[0];

  const currentCluster =
    clusters.find((cl) => cl.cluster_id === currentCandidate?.cluster_id) ||
    clusters[0];

  const currentVerdict = verdicts.find(
    (v) => v.candidate_id === currentCandidate?.candidate_id
  );

  const currentScorecard = scorecards.find(
    (sc) => sc.candidate_id === currentCandidate?.candidate_id
  );

  const isSurvived = isCandidateSurvived(currentVerdict, currentScorecard);

  // Consolidate challenging patents across verdict cited_patents and scorecard supporting_evidence
  const citedPatentsFromVerdict = currentVerdict?.cited_patents || [];
  const supportingEvidenceFromScorecard = currentScorecard?.supporting_evidence || [];

  const extractedPatentsFromEvidence = supportingEvidenceFromScorecard
    .map((item) => {
      const match = item.match(/\b(US-[A-Za-z0-9-]+)\b/);
      return match ? match[1] : item.trim();
    })
    .filter((item) => item.length > 0 && item.startsWith("US-"));

  const effectiveChallengingPatents = Array.from(
    new Set([...citedPatentsFromVerdict, ...extractedPatentsFromEvidence])
  );

  if (!currentCandidate) {
    return (
      <div className={styles.container}>
        <header className={styles.header}>
          <BrandHeader />
          {domain && <h2 className={styles.domainTitle}>{domain}</h2>}
          <h1 className={styles.title}>Analysis Completed</h1>
        </header>
        <div className={styles.emptyCard}>
          <p className={styles.emptyMessage}>
            No candidate inventions survived the prior-art challenge for this query.
          </p>
          {onReset && (
            <button type="button" className={styles.primaryBtn} onClick={onReset}>
              Analyze another opportunity
            </button>
          )}
        </div>
      </div>
    );
  }

  // Calculate prior art risk level
  const priorArtRiskVal = currentScorecard?.prior_art_risk;
  const isLowRisk = priorArtRiskVal !== undefined && (priorArtRiskVal <= 0.35 || (priorArtRiskVal <= 35 && priorArtRiskVal > 1));

  const hasValidWhiteSpaceScore =
    currentCluster?.white_space_score !== undefined &&
    currentCluster?.white_space_score !== null &&
    !Number.isNaN(currentCluster.white_space_score);

  const whyItMatters = firstSentence(
    currentScorecard?.summary || currentCandidate.claimed_novelty || currentCandidate.description
  );

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <BrandHeader />
        {domain && <div className={styles.domainBadge}>{domain}</div>}
      </header>

      {/* Executive summary -- conclusion first, technical detail on demand */}
      <section className={styles.heroCard} aria-label="Result summary">
        <span className={isSurvived ? styles.survivesBadge : styles.rejectedBadge}>
          {isSurvived ? "🟢 Survived prior-art review" : "❌ Rejected on prior art"}
        </span>
        <h1 className={styles.heroTitle}>{currentCandidate.title}</h1>

        <div className={styles.heroStats}>
          <div className={styles.heroStat}>
            <span className={styles.heroStatValue}>
              {formatScore(currentCluster?.white_space_score)}
            </span>
            <span className={styles.heroStatLabel}>Opportunity score</span>
          </div>
          <div className={styles.heroStat}>
            <span className={styles.heroStatValue}>
              {formatScore(currentScorecard?.evidence)}
            </span>
            <span className={styles.heroStatLabel}>Confidence</span>
          </div>
        </div>

        <div className={styles.whyItMatters}>
          <span className={styles.whyItMattersLabel}>Why it matters</span>
          <p className={styles.whyItMattersText}>{whyItMatters}</p>
        </div>

        <button
          type="button"
          className={styles.viewEvidenceBtn}
          onClick={() => setShowDetails(true)}
        >
          View evidence
        </button>
      </section>

      {displayCandidates.length > 1 && (
        <div className={styles.candidateSelector}>
          <span className={styles.selectorLabel}>
            {survivingCandidates.length > 0 ? "Surviving candidates:" : "Evaluated candidates:"}
          </span>
          <div className={styles.candidatePills}>
            {displayCandidates.map((cand, idx) => (
              <button
                key={cand.candidate_id}
                type="button"
                className={`${styles.candidatePill} ${
                  cand.candidate_id === currentCandidate.candidate_id
                    ? styles.candidatePillActive
                    : ""
                }`}
                onClick={() => setSelectedCandidateId(cand.candidate_id)}
              >
                Candidate {idx + 1}: {cand.title.slice(0, 30)}…
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Technical detail -- collapsed by default; the hero card above is the product */}
      <div className={styles.drilldownSection}>
        <button
          type="button"
          className={`${styles.drilldownToggleBtn} ${showDetails ? styles.drilldownActive : ""}`}
          onClick={() => setShowDetails((prev) => !prev)}
          aria-expanded={showDetails}
        >
          <span className={styles.toggleIcon}>{showDetails ? "▲" : "▸"}</span>
          <span>{showDetails ? "Hide details" : "Details"}</span>
        </button>

        {showDetails && (
      <section className={styles.decisionCard} aria-label="Decision card summary">
        {/* 1. What is proposed? */}
        <div className={styles.sectionBlock}>
          <div className={styles.questionHeader}>
            <span className={styles.questionNumber}>1</span>
            <h3 className={styles.questionTitle}>What is proposed?</h3>
          </div>
          <div className={styles.answerContent}>
            <h2 className={styles.candidateHeading}>{currentCandidate.title}</h2>
            <p className={styles.candidateDescription}>
              {currentCandidate.description}
            </p>
            {currentCandidate.claimed_novelty && (
              <div className={styles.highlightBadge}>
                <span className={styles.badgePrefix}>Core Claimed Novelty:</span>{" "}
                {currentCandidate.claimed_novelty}
              </div>
            )}
          </div>
        </div>

        {/* 2. Why this opportunity? */}
        <div className={styles.sectionBlock}>
          <div className={styles.questionHeader}>
            <span className={styles.questionNumber}>2</span>
            <h3 className={styles.questionTitle}>Why this opportunity?</h3>
          </div>
          <div className={styles.answerContent}>
            <div className={styles.opportunityRow}>
              <div className={styles.opportunityInfo}>
                <span className={styles.opportunityLabel}>
                  {currentCluster?.label || "Target Cluster"}
                </span>
                <p className={styles.opportunityDesc}>
                  {hasValidWhiteSpaceScore
                    ? "Under-served white-space area in the surveyed patent landscape with low prior-art saturation and unaddressed demand signals."
                    : "Technology cluster analyzed in surveyed landscape; white-space metrics unavailable for this calculation."}
                </p>
              </div>
              <div className={styles.scoreBadgeBox}>
                <span className={styles.scoreBadgeLabel}>White-Space Score</span>
                <span className={styles.scoreBadgeValue}>
                  {formatScore(currentCluster?.white_space_score)}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* 3. What challenged it? */}
        <div className={styles.sectionBlock}>
          <div className={styles.questionHeader}>
            <span className={styles.questionNumber}>3</span>
            <h3 className={styles.questionTitle}>What challenged it?</h3>
          </div>
          <div className={styles.answerContent}>
            <p className={styles.challengeIntro}>
              The adversarial examiner challenged the candidate against closest prior-art citations:
            </p>
            {effectiveChallengingPatents.length > 0 ? (
              <div className={styles.patentList}>
                {effectiveChallengingPatents.map((pat) => (
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
            ) : (
              <p className={styles.emptyNote}>Evidence unavailable for this step.</p>
            )}
            {currentVerdict?.rationale && (
              <div className={styles.quoteBox}>
                <span className={styles.quoteLabel}>Adversarial Objection:</span>
                <p className={styles.quoteText}>{currentVerdict.rationale}</p>
              </div>
            )}
          </div>
        </div>

        {/* 4. Why did it survive? / Evaluation Outcome */}
        <div className={styles.sectionBlock}>
          <div className={styles.questionHeader}>
            <span className={styles.questionNumber}>4</span>
            <h3 className={styles.questionTitle}>
              {isSurvived ? "Why did it survive?" : "Evaluation Outcome"}
            </h3>
          </div>
          <div className={styles.answerContent}>
            <div className={styles.survivalStatusRow}>
              {isSurvived ? (
                <span className={styles.survivesBadge}>✓ Survived Adversarial Review</span>
              ) : (
                <span className={styles.rejectedBadge}>
                  ❌ Rejected — Did Not Survive Adversarial Review
                </span>
              )}
            </div>
            <p className={styles.differentiationText}>
              {isSurvived
                ? currentCandidate.claimed_novelty ||
                  "Clear functional differentiation from cited prior art establishes strong novelty and freedom-to-operate potential."
                : currentScorecard?.summary ||
                  currentVerdict?.rationale ||
                  "The proposed invention was directly anticipated by pre-existing patents in the landscape, preventing patentability recommendation."}
            </p>
          </div>
        </div>

        {/* 5. Evidence & Final Assessment */}
        <div className={styles.sectionBlock}>
          <div className={styles.questionHeader}>
            <span className={styles.questionNumber}>5</span>
            <h3 className={styles.questionTitle}>Evidence & Final Assessment</h3>
          </div>
          <div className={styles.answerContent}>
            {/* Scores Grid */}
            <div className={styles.scoresGrid}>
              <div className={styles.scoreMetricCard}>
                <span className={styles.scoreMetricLabel}>Novelty</span>
                <span className={styles.scoreMetricValue}>
                  {formatScore(currentScorecard?.novelty)}
                </span>
                <div className={styles.progressBar}>
                  <div
                    className={styles.progressFill}
                    style={{
                      width: formatScore(currentScorecard?.novelty),
                    }}
                  />
                </div>
              </div>

              <div className={styles.scoreMetricCard}>
                <span className={styles.scoreMetricLabel}>Prior-Art Risk</span>
                <div className={styles.riskValueRow}>
                  <span className={styles.scoreMetricValue}>
                    {formatScore(currentScorecard?.prior_art_risk)}
                  </span>
                  <span
                    className={`${styles.riskBadge} ${
                      isLowRisk ? styles.lowRiskBadge : styles.medRiskBadge
                    }`}
                  >
                    {isLowRisk ? "Low risk" : "Moderate risk"}
                  </span>
                </div>
                <div className={styles.progressBar}>
                  <div
                    className={`${styles.progressFill} ${styles.riskProgressFill}`}
                    style={{
                      width: formatScore(currentScorecard?.prior_art_risk),
                    }}
                  />
                </div>
              </div>

              <div className={styles.scoreMetricCard}>
                <span className={styles.scoreMetricLabel}>Differentiation</span>
                <span className={styles.scoreMetricValue}>
                  {formatScore(currentScorecard?.differentiation)}
                </span>
                <div className={styles.progressBar}>
                  <div
                    className={styles.progressFill}
                    style={{
                      width: formatScore(currentScorecard?.differentiation),
                    }}
                  />
                </div>
              </div>

              <div className={styles.scoreMetricCard}>
                <span className={styles.scoreMetricLabel}>Evidence</span>
                <span className={styles.scoreMetricValue}>
                  {formatScore(currentScorecard?.evidence)}
                </span>
                <div className={styles.progressBar}>
                  <div
                    className={styles.progressFill}
                    style={{
                      width: formatScore(currentScorecard?.evidence),
                    }}
                  />
                </div>
              </div>
            </div>

            {currentScorecard?.summary && (
              <div className={styles.summaryBox}>
                <span className={styles.summaryLabel}>Final Assessment:</span>
                <p className={styles.summaryText}>{currentScorecard.summary}</p>
              </div>
            )}

            {currentScorecard?.supporting_evidence &&
              currentScorecard.supporting_evidence.length > 0 && (
                <div className={styles.evidenceSection}>
                  <span className={styles.evidenceLabel}>Supporting Citations:</span>
                  <ul className={styles.evidenceList}>
                    {currentScorecard.supporting_evidence.map((ev, idx) => (
                      <li key={idx} className={styles.evidenceItem}>
                        {ev}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
          </div>
        </div>
      </section>
        )}
      </div>

      {/* Drill-down button & Causal Chain */}
      <div className={styles.drilldownSection}>
        <button
          type="button"
          className={`${styles.drilldownToggleBtn} ${
            showCausalChain ? styles.drilldownActive : ""
          }`}
          onClick={() => setShowCausalChain((prev) => !prev)}
          aria-expanded={showCausalChain}
        >
          <span className={styles.toggleIcon}>{showCausalChain ? "▲" : "▸"}</span>
          <span>
            {showCausalChain
              ? "Hide"
              : "How the agent reached this result"}
          </span>
        </button>

        {showCausalChain && (
          <div className={styles.causalChainWrapper}>
            <CausalChain
              cluster={currentCluster}
              candidate={currentCandidate}
              verdict={currentVerdict}
              scorecard={currentScorecard}
            />
          </div>
        )}
      </div>

      {onReset && (
        <footer className={styles.footerActions}>
          <button type="button" className={styles.resetBtn} onClick={onReset}>
            ← Analyze another opportunity
          </button>
        </footer>
      )}
    </div>
  );
}
