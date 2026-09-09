/**
 * Scientific Results Contract v1 Domain Model (ADR 0025).
 *
 * Pure domain model representing the canonical `scientific_results.json` contract —
 * a sibling artifact to `project_status.json` (ADR 0022/0023), never merged with it:
 * this module carries Nexus's empirical outputs, not its engineering/audit status.
 *
 * Invariants:
 * 1. Mandatory, non-interchangeable track vocabulary: `discovery` (Head A) vs
 *    `verification` (Head B) (ADR 0025 §1). A record's track must match the track of
 *    the execution it references — discovery and verification are never silently mixed.
 * 2. Immutable, read-only representation of published evidence.
 * 3. Epistemic restraint: no scientific value (score, metric, verdict) is
 *    recalculated, derived, or synthesized here — every value is copied verbatim from
 *    the published artifact.
 * 4. Absent optional provenance (dataset_id, policy_id, etc.) is preserved as `null`,
 *    never defaulted or fabricated.
 * 5. Zero runtime UI or framework dependencies (pure TypeScript).
 */

export const TRACK_VALUES = ['discovery', 'verification'] as const;
export type Track = (typeof TRACK_VALUES)[number];

export const CHALLENGE_STATUS_VALUES = ['not_yet_challenged', 'challenged'] as const;
export type ChallengeStatus = (typeof CHALLENGE_STATUS_VALUES)[number];

export const CITATION_RESOLUTION_VALUES = ['resolved', 'unresolved'] as const;
export type CitationResolution = (typeof CITATION_RESOLUTION_VALUES)[number];

export const CITATION_ROLE_VALUES = ['supports', 'challenges'] as const;
export type CitationRole = (typeof CITATION_ROLE_VALUES)[number];

export const SOURCE_PROVENANCE_ROLE_VALUES = ['patents', 'demand'] as const;
export type SourceProvenanceRole = (typeof SOURCE_PROVENANCE_ROLE_VALUES)[number];

export class ScientificResultsValidationError extends Error {
  constructor(message: string) {
    super(`ScientificResultsValidationError: ${message}`);
    this.name = 'ScientificResultsValidationError';
  }
}

export interface DataSourceProvenance {
  readonly role: SourceProvenanceRole;
  readonly kind: string;
}

export interface ScientificResultsExecution {
  readonly execution_id: string;
  readonly track: Track;
  readonly domain: string;
  readonly query: string;
  readonly created_at: string;
  readonly dataset_id: string | null;
  readonly dataset_version: string | null;
  readonly engine_commit: string | null;
  readonly policy_id: string | null;
  readonly policy_version: string | null;
  readonly policy_sha256: string | null;
  readonly source_provenance: readonly DataSourceProvenance[];
}

export interface PatentCluster {
  readonly cluster_id: string;
  readonly label: string;
  readonly representative_patents: readonly string[];
  readonly patent_count: number;
  readonly white_space_score: number;
  readonly is_white_space: boolean;
}

export interface TechnologyClusterObservation {
  readonly cluster: PatentCluster;
  readonly density: number;
  readonly recency: number;
  readonly citation_traction: number;
  readonly citation_coverage: number;
  readonly demand_intensity: number;
  readonly quadrant: string;
  readonly mean_age_years: number;
}

export interface DiscoveryLandscapeRecord {
  readonly execution_id: string;
  readonly query: string;
  readonly clusters: readonly TechnologyClusterObservation[];
  readonly disclaimer: string;
}

export interface InventionCandidate {
  readonly candidate_id: string;
  readonly cluster_id: string;
  readonly title: string;
  readonly description: string;
  readonly claimed_novelty: string;
}

export interface DiscoveryCandidateRecord {
  readonly execution_id: string;
  readonly candidate: InventionCandidate;
  readonly disclaimer: string;
}

export interface EvidenceCitation {
  readonly publication_id: string;
  readonly role: CitationRole;
  readonly resolution: CitationResolution;
  readonly title: string | null;
  readonly publication_date: string | null;
}

export interface AdversarialVerdict {
  readonly candidate_id: string;
  readonly verdict: string;
  readonly rationale: string;
  readonly cited_patents: readonly string[];
}

export interface ScoreCard {
  readonly candidate_id: string;
  readonly novelty: number;
  readonly prior_art_risk: number;
  readonly differentiation: number;
  readonly evidence: number;
  readonly supporting_evidence: readonly string[];
}

export interface DiscoveryVerificationRecord {
  readonly execution_id: string;
  readonly candidate_id: string;
  readonly challenge_status: ChallengeStatus;
  readonly verdict: AdversarialVerdict | null;
  readonly scorecard: ScoreCard | null;
  readonly citations: readonly EvidenceCitation[];
  readonly disclaimer: string;
}

export interface MatchAssessment {
  readonly demand_id: string;
  readonly publication_id: string;
  readonly overall_score: number;
  readonly confidence: string;
  readonly sufficiency: string;
  readonly rationale: string;
  readonly policy_id: string;
  readonly policy_version: string;
  readonly policy_sha256: string;
  readonly fusion_transform_id: string;
}

export interface VerificationMatchRecord {
  readonly execution_id: string;
  readonly assessment: MatchAssessment;
}

export interface ScientificResultsDocument {
  readonly schema_version: string;
  readonly generated_at: string;
  readonly executions: readonly ScientificResultsExecution[];
  readonly landscapes: readonly DiscoveryLandscapeRecord[];
  readonly candidates: readonly DiscoveryCandidateRecord[];
  readonly verifications: readonly DiscoveryVerificationRecord[];
  readonly matches: readonly VerificationMatchRecord[];
}

const ISO_8601_PATTERN = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/;

function isIsoTimestamp(value: unknown): value is string {
  return typeof value === 'string' && ISO_8601_PATTERN.test(value) && !Number.isNaN(Date.parse(value));
}

function isTrack(value: unknown): value is Track {
  return typeof value === 'string' && (TRACK_VALUES as readonly string[]).includes(value);
}

function asRecord(value: unknown, context: string): Record<string, unknown> {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) {
    throw new ScientificResultsValidationError(`${context} must be an object.`);
  }
  return value as Record<string, unknown>;
}

function asArray(value: unknown, context: string): unknown[] {
  if (!Array.isArray(value)) {
    throw new ScientificResultsValidationError(`${context} must be an array.`);
  }
  return value;
}

function requireString(value: unknown, context: string, allowEmpty = false): string {
  if (typeof value !== 'string' || (!allowEmpty && value.trim() === '')) {
    throw new ScientificResultsValidationError(`${context} must be a non-empty string.`);
  }
  return value;
}

function requireNumber(value: unknown, context: string): number {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    throw new ScientificResultsValidationError(`${context} must be a number.`);
  }
  return value;
}

function requireBoolean(value: unknown, context: string): boolean {
  if (typeof value !== 'boolean') {
    throw new ScientificResultsValidationError(`${context} must be a boolean.`);
  }
  return value;
}

function optionalString(value: unknown, context: string): string | null {
  if (value === null || value === undefined) return null;
  if (typeof value !== 'string') {
    throw new ScientificResultsValidationError(`${context} must be a string or null.`);
  }
  return value;
}

function requireStringArray(value: unknown, context: string): readonly string[] {
  return Object.freeze(
    asArray(value, context).map((item, i) => requireString(item, `${context}[${i}]`))
  );
}

function validateDataSourceProvenance(raw: unknown, index: number): DataSourceProvenance {
  const p = asRecord(raw, `source_provenance[${index}]`);
  const role = p.role;
  if (role !== 'patents' && role !== 'demand') {
    throw new ScientificResultsValidationError(
      `source_provenance[${index}].role must be 'patents' or 'demand', got '${String(role)}'.`
    );
  }
  return Object.freeze({
    role,
    kind: requireString(p.kind, `source_provenance[${index}].kind`),
  });
}

function validateExecution(raw: unknown, index: number): ScientificResultsExecution {
  const e = asRecord(raw, `executions[${index}]`);
  const executionId = requireString(e.execution_id, `executions[${index}].execution_id`);

  if (!isTrack(e.track)) {
    throw new ScientificResultsValidationError(
      `executions[${index}].track must be one of: ${TRACK_VALUES.join(', ')}. Got '${String(e.track)}'.`
    );
  }
  if (!isIsoTimestamp(e.created_at)) {
    throw new ScientificResultsValidationError(
      `executions[${index}].created_at must be an ISO-8601 timestamp. Got '${String(e.created_at)}'.`
    );
  }

  const sourceProvenance = e.source_provenance === undefined
    ? []
    : asArray(e.source_provenance, `executions[${index}].source_provenance`).map((sp, i) =>
        validateDataSourceProvenance(sp, i)
      );

  return Object.freeze({
    execution_id: executionId,
    track: e.track,
    domain: requireString(e.domain, `executions[${index}].domain`),
    query: requireString(e.query, `executions[${index}].query`),
    created_at: e.created_at,
    dataset_id: optionalString(e.dataset_id, `executions[${index}].dataset_id`),
    dataset_version: optionalString(e.dataset_version, `executions[${index}].dataset_version`),
    engine_commit: optionalString(e.engine_commit, `executions[${index}].engine_commit`),
    policy_id: optionalString(e.policy_id, `executions[${index}].policy_id`),
    policy_version: optionalString(e.policy_version, `executions[${index}].policy_version`),
    policy_sha256: optionalString(e.policy_sha256, `executions[${index}].policy_sha256`),
    source_provenance: Object.freeze(sourceProvenance),
  });
}

function validatePatentCluster(raw: unknown, context: string): PatentCluster {
  const c = asRecord(raw, context);
  return Object.freeze({
    cluster_id: requireString(c.cluster_id, `${context}.cluster_id`),
    label: requireString(c.label, `${context}.label`),
    representative_patents: requireStringArray(c.representative_patents, `${context}.representative_patents`),
    patent_count: requireNumber(c.patent_count, `${context}.patent_count`),
    white_space_score: requireNumber(c.white_space_score, `${context}.white_space_score`),
    is_white_space: requireBoolean(c.is_white_space, `${context}.is_white_space`),
  });
}

function validateClusterObservation(raw: unknown, index: number, context: string): TechnologyClusterObservation {
  const o = asRecord(raw, `${context}.clusters[${index}]`);
  return Object.freeze({
    cluster: validatePatentCluster(o.cluster, `${context}.clusters[${index}].cluster`),
    density: requireNumber(o.density, `${context}.clusters[${index}].density`),
    recency: requireNumber(o.recency, `${context}.clusters[${index}].recency`),
    citation_traction: requireNumber(o.citation_traction, `${context}.clusters[${index}].citation_traction`),
    citation_coverage: requireNumber(o.citation_coverage, `${context}.clusters[${index}].citation_coverage`),
    demand_intensity: requireNumber(o.demand_intensity, `${context}.clusters[${index}].demand_intensity`),
    quadrant: requireString(o.quadrant, `${context}.clusters[${index}].quadrant`),
    mean_age_years: requireNumber(o.mean_age_years, `${context}.clusters[${index}].mean_age_years`),
  });
}

function validateLandscape(raw: unknown, index: number): DiscoveryLandscapeRecord {
  const context = `landscapes[${index}]`;
  const l = asRecord(raw, context);
  const clusters = asArray(l.clusters ?? [], `${context}.clusters`).map((c, i) =>
    validateClusterObservation(c, i, context)
  );
  return Object.freeze({
    execution_id: requireString(l.execution_id, `${context}.execution_id`),
    query: requireString(l.query, `${context}.query`),
    clusters: Object.freeze(clusters),
    disclaimer: requireString(l.disclaimer, `${context}.disclaimer`),
  });
}

function validateCandidate(raw: unknown, index: number): DiscoveryCandidateRecord {
  const context = `candidates[${index}]`;
  const r = asRecord(raw, context);
  const c = asRecord(r.candidate, `${context}.candidate`);
  return Object.freeze({
    execution_id: requireString(r.execution_id, `${context}.execution_id`),
    candidate: Object.freeze({
      candidate_id: requireString(c.candidate_id, `${context}.candidate.candidate_id`),
      cluster_id: requireString(c.cluster_id, `${context}.candidate.cluster_id`),
      title: requireString(c.title, `${context}.candidate.title`),
      description: requireString(c.description, `${context}.candidate.description`),
      claimed_novelty: requireString(c.claimed_novelty, `${context}.candidate.claimed_novelty`, true),
    }),
    disclaimer: requireString(r.disclaimer, `${context}.disclaimer`),
  });
}

function validateCitation(raw: unknown, index: number, context: string): EvidenceCitation {
  const c = asRecord(raw, `${context}.citations[${index}]`);
  const role = c.role;
  if (role !== 'supports' && role !== 'challenges') {
    throw new ScientificResultsValidationError(
      `${context}.citations[${index}].role must be 'supports' or 'challenges'. Got '${String(role)}'.`
    );
  }
  const resolution = c.resolution;
  if (resolution !== 'resolved' && resolution !== 'unresolved') {
    throw new ScientificResultsValidationError(
      `${context}.citations[${index}].resolution must be 'resolved' or 'unresolved'. Got '${String(resolution)}'.`
    );
  }
  return Object.freeze({
    publication_id: requireString(c.publication_id, `${context}.citations[${index}].publication_id`),
    role,
    resolution,
    title: optionalString(c.title, `${context}.citations[${index}].title`),
    publication_date: optionalString(c.publication_date, `${context}.citations[${index}].publication_date`),
  });
}

function validateVerdict(raw: unknown, context: string): AdversarialVerdict {
  const v = asRecord(raw, context);
  return Object.freeze({
    candidate_id: requireString(v.candidate_id, `${context}.candidate_id`),
    verdict: requireString(v.verdict, `${context}.verdict`),
    rationale: requireString(v.rationale, `${context}.rationale`, true),
    cited_patents: requireStringArray(v.cited_patents, `${context}.cited_patents`),
  });
}

function validateScoreCard(raw: unknown, context: string): ScoreCard {
  const s = asRecord(raw, context);
  return Object.freeze({
    candidate_id: requireString(s.candidate_id, `${context}.candidate_id`),
    novelty: requireNumber(s.novelty, `${context}.novelty`),
    prior_art_risk: requireNumber(s.prior_art_risk, `${context}.prior_art_risk`),
    differentiation: requireNumber(s.differentiation, `${context}.differentiation`),
    evidence: requireNumber(s.evidence, `${context}.evidence`),
    supporting_evidence: requireStringArray(s.supporting_evidence, `${context}.supporting_evidence`),
  });
}

function validateVerification(raw: unknown, index: number): DiscoveryVerificationRecord {
  const context = `verifications[${index}]`;
  const r = asRecord(raw, context);
  const challengeStatus = r.challenge_status;
  if (!(CHALLENGE_STATUS_VALUES as readonly string[]).includes(challengeStatus as string)) {
    throw new ScientificResultsValidationError(
      `${context}.challenge_status must be one of: ${CHALLENGE_STATUS_VALUES.join(', ')}. Got '${String(challengeStatus)}'.`
    );
  }
  const citations = asArray(r.citations ?? [], `${context}.citations`).map((c, i) =>
    validateCitation(c, i, context)
  );
  return Object.freeze({
    execution_id: requireString(r.execution_id, `${context}.execution_id`),
    candidate_id: requireString(r.candidate_id, `${context}.candidate_id`),
    challenge_status: challengeStatus as ChallengeStatus,
    verdict: r.verdict == null ? null : validateVerdict(r.verdict, `${context}.verdict`),
    scorecard: r.scorecard == null ? null : validateScoreCard(r.scorecard, `${context}.scorecard`),
    citations: Object.freeze(citations),
    disclaimer: requireString(r.disclaimer, `${context}.disclaimer`),
  });
}

function validateMatch(raw: unknown, index: number): VerificationMatchRecord {
  const context = `matches[${index}]`;
  const r = asRecord(raw, context);
  const a = asRecord(r.assessment, `${context}.assessment`);
  return Object.freeze({
    execution_id: requireString(r.execution_id, `${context}.execution_id`),
    assessment: Object.freeze({
      demand_id: requireString(a.demand_id, `${context}.assessment.demand_id`),
      publication_id: requireString(a.publication_id, `${context}.assessment.publication_id`),
      overall_score: requireNumber(a.overall_score, `${context}.assessment.overall_score`),
      confidence: requireString(a.confidence, `${context}.assessment.confidence`),
      sufficiency: requireString(a.sufficiency, `${context}.assessment.sufficiency`),
      rationale: requireString(a.rationale, `${context}.assessment.rationale`, true),
      policy_id: requireString(a.policy_id, `${context}.assessment.policy_id`),
      policy_version: requireString(a.policy_version, `${context}.assessment.policy_version`),
      policy_sha256: requireString(a.policy_sha256, `${context}.assessment.policy_sha256`),
      fusion_transform_id: requireString(a.fusion_transform_id, `${context}.assessment.fusion_transform_id`),
    }),
  });
}

/**
 * Parses and validates an untrusted raw payload against the Scientific Results
 * Contract v1 (ADR 0025). Throws ScientificResultsValidationError on any structural
 * or referential-integrity violation — never silently downgrades a corrupt/invalid
 * payload into an empty result set.
 *
 * Referential integrity (ADR 0025 §1): every landscape/candidate/verification record
 * must reference a listed execution whose track is `discovery`; every match record
 * must reference a listed execution whose track is `verification`. This is the
 * mechanism that makes "discovery and verification cannot be mixed" structural on
 * the read side, mirroring the same invariant already enforced at publish time by
 * `ScientificResultsDocument` (backend/src/main/domain/models/scientific_results.py).
 */
export function parseScientificResults(raw: unknown): ScientificResultsDocument {
  const payload = asRecord(raw, 'Payload');

  const schemaVersion = requireString(payload.schema_version, 'schema_version');
  const generatedAt = payload.generated_at;
  if (!isIsoTimestamp(generatedAt)) {
    throw new ScientificResultsValidationError(
      `Invalid generated_at timestamp: '${String(generatedAt)}'. Must be ISO-8601.`
    );
  }

  const executions = asArray(payload.executions ?? [], 'executions').map((e, i) => validateExecution(e, i));
  const executionsById = new Map<string, ScientificResultsExecution>();
  for (const execution of executions) {
    if (executionsById.has(execution.execution_id)) {
      throw new ScientificResultsValidationError(`Duplicate execution_id in executions: '${execution.execution_id}'.`);
    }
    executionsById.set(execution.execution_id, execution);
  }

  function requireTrack(executionId: string, requiredTrack: Track, recordKind: string): void {
    const execution = executionsById.get(executionId);
    if (!execution) {
      throw new ScientificResultsValidationError(`${recordKind} references unknown execution_id '${executionId}'.`);
    }
    if (execution.track !== requiredTrack) {
      throw new ScientificResultsValidationError(
        `${recordKind} references execution_id '${executionId}' with track='${execution.track}', ` +
          `but a ${recordKind} record requires track='${requiredTrack}' — discovery and verification cannot be mixed (ADR 0025 §1).`
      );
    }
  }

  const landscapes = asArray(payload.landscapes ?? [], 'landscapes').map((l, i) => validateLandscape(l, i));
  landscapes.forEach((l) => requireTrack(l.execution_id, 'discovery', 'landscape'));

  const candidates = asArray(payload.candidates ?? [], 'candidates').map((c, i) => validateCandidate(c, i));
  candidates.forEach((c) => requireTrack(c.execution_id, 'discovery', 'candidate'));

  const verifications = asArray(payload.verifications ?? [], 'verifications').map((v, i) => validateVerification(v, i));
  verifications.forEach((v) => requireTrack(v.execution_id, 'discovery', 'verification'));

  const matches = asArray(payload.matches ?? [], 'matches').map((m, i) => validateMatch(m, i));
  matches.forEach((m) => requireTrack(m.execution_id, 'verification', 'match'));

  return Object.freeze({
    schema_version: schemaVersion,
    generated_at: generatedAt,
    executions: Object.freeze(executions),
    landscapes: Object.freeze(landscapes),
    candidates: Object.freeze(candidates),
    verifications: Object.freeze(verifications),
    matches: Object.freeze(matches),
  }) as ScientificResultsDocument;
}
