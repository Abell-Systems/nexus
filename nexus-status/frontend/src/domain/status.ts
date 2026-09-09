/**
 * Project Status Contract v1 Domain Model (ADR 0022, ADR 0023, ADR 0024).
 *
 * Pure domain model representing the canonical Project Status Contract.
 * Invariants:
 * 1. Symmetrical 5-state vocabulary (PASS, FAIL, UNVERIFIED, SKIPPED, N/A).
 * 2. Immutable, read-only representation of evaluated evidence.
 * 3. Epistemic restraint: No re-calculation, override, or synthetic generation
 *    of overall_status. The overall verdict is authored exclusively by Nexus core.
 * 4. Zero runtime UI or framework dependencies (pure TypeScript).
 */

export const CANONICAL_STATUSES = [
  'PASS',
  'FAIL',
  'UNVERIFIED',
  'SKIPPED',
  'N/A',
] as const;

export type StatusValue = (typeof CANONICAL_STATUSES)[number];

export const REQUIREMENT_LEVELS = ['required', 'optional'] as const;

export type RequirementLevel = (typeof REQUIREMENT_LEVELS)[number];

export class ContractValidationError extends Error {
  constructor(message: string) {
    super(`ContractValidationError: ${message}`);
    this.name = 'ContractValidationError';
  }
}

export interface CheckResult {
  readonly name: string;
  readonly status: StatusValue;
  readonly value?: unknown;
  readonly threshold?: unknown;
  readonly detail?: string;
}

export interface DimensionStatus {
  readonly status: StatusValue;
  readonly requirement_level: RequirementLevel;
  readonly evidence_source: string;
  readonly evidence_available: boolean;
  readonly message?: string;
  readonly metrics?: Readonly<Record<string, unknown>>;
  readonly checks: readonly CheckResult[];
}

export interface ProjectStatus {
  readonly schema_version: string;
  readonly commit_sha: string;
  readonly evaluated_at: string;
  readonly overall_status: StatusValue;
  readonly aggregation_rule: string;
  readonly summary: string;
  readonly dimensions: Readonly<Record<string, DimensionStatus>>;
}

export function isStatusValue(value: unknown): value is StatusValue {
  return (
    typeof value === 'string' &&
    (CANONICAL_STATUSES as readonly string[]).includes(value)
  );
}

export function isRequirementLevel(value: unknown): value is RequirementLevel {
  return (
    typeof value === 'string' &&
    (REQUIREMENT_LEVELS as readonly string[]).includes(value)
  );
}

function validateCheck(rawCheck: unknown, index: number, dimensionKey: string): CheckResult {
  if (typeof rawCheck !== 'object' || rawCheck === null) {
    throw new ContractValidationError(
      `Dimension '${dimensionKey}' check at index ${index} must be an object.`
    );
  }
  const check = rawCheck as Record<string, unknown>;

  if (typeof check.name !== 'string' || check.name.trim() === '') {
    throw new ContractValidationError(
      `Dimension '${dimensionKey}' check at index ${index} must have a non-empty string name.`
    );
  }

  if (!isStatusValue(check.status)) {
    throw new ContractValidationError(
      `Dimension '${dimensionKey}' check '${check.name}' has invalid status '${String(check.status)}'. ` +
        `Must be one of: ${CANONICAL_STATUSES.join(', ')}`
    );
  }

  return {
    name: check.name,
    status: check.status,
    ...(check.value !== undefined ? { value: check.value } : {}),
    ...(check.threshold !== undefined ? { threshold: check.threshold } : {}),
    ...(typeof check.detail === 'string' ? { detail: check.detail } : {}),
  };
}

function validateDimension(rawDim: unknown, key: string): DimensionStatus {
  if (typeof rawDim !== 'object' || rawDim === null) {
    throw new ContractValidationError(`Dimension '${key}' must be an object.`);
  }
  const dim = rawDim as Record<string, unknown>;

  if (!isStatusValue(dim.status)) {
    throw new ContractValidationError(
      `Dimension '${key}' has invalid status '${String(dim.status)}'. ` +
        `Must be one of: ${CANONICAL_STATUSES.join(', ')}`
    );
  }

  if (!isRequirementLevel(dim.requirement_level)) {
    throw new ContractValidationError(
      `Dimension '${key}' has invalid requirement_level '${String(dim.requirement_level)}'. ` +
        `Must be one of: ${REQUIREMENT_LEVELS.join(', ')}`
    );
  }

  if (typeof dim.evidence_source !== 'string') {
    throw new ContractValidationError(
      `Dimension '${key}' must have string evidence_source.`
    );
  }

  if (typeof dim.evidence_available !== 'boolean') {
    throw new ContractValidationError(
      `Dimension '${key}' must have boolean evidence_available.`
    );
  }

  const rawChecks = Array.isArray(dim.checks) ? dim.checks : [];
  const validatedChecks = rawChecks.map((c, i) => validateCheck(c, i, key));

  return {
    status: dim.status,
    requirement_level: dim.requirement_level,
    evidence_source: dim.evidence_source,
    evidence_available: dim.evidence_available,
    ...(typeof dim.message === 'string' ? { message: dim.message } : {}),
    ...(typeof dim.metrics === 'object' && dim.metrics !== null
      ? { metrics: dim.metrics as Record<string, unknown> }
      : {}),
    checks: Object.freeze(validatedChecks),
  };
}

/**
 * Parses and validates an untrusted raw payload against the canonical Project Status Contract v1.
 * Throws ContractValidationError if required fields are missing or invalid.
 * Preserves exact status values and dimensions without mutation or synthesis.
 */
export function parseProjectStatus(raw: unknown): ProjectStatus {
  if (typeof raw !== 'object' || raw === null) {
    throw new ContractValidationError('Payload must be a non-null JSON object.');
  }

  const payload = raw as Record<string, unknown>;

  // 1. Schema version
  if (typeof payload.schema_version !== 'string') {
    throw new ContractValidationError('Missing or non-string schema_version.');
  }
  if (!payload.schema_version.startsWith('1.')) {
    throw new ContractValidationError(
      `Unsupported schema_version '${payload.schema_version}'. Expected '1.x.x'.`
    );
  }

  // 2. Commit SHA
  if (typeof payload.commit_sha !== 'string' || payload.commit_sha.trim() === '') {
    throw new ContractValidationError('Missing or empty commit_sha.');
  }

  // 3. Evaluated at (valid ISO timestamp)
  if (typeof payload.evaluated_at !== 'string' || Number.isNaN(Date.parse(payload.evaluated_at))) {
    throw new ContractValidationError(
      `Invalid evaluated_at timestamp: '${String(payload.evaluated_at)}'. Must be ISO-8601.`
    );
  }

  // 4. Overall status (must be strictly one of the 5 canonical statuses)
  if (!isStatusValue(payload.overall_status)) {
    throw new ContractValidationError(
      `Invalid overall_status '${String(payload.overall_status)}'. ` +
        `Must be one of: ${CANONICAL_STATUSES.join(', ')}`
    );
  }

  // 5. Aggregation rule and summary
  if (typeof payload.aggregation_rule !== 'string') {
    throw new ContractValidationError('Missing or non-string aggregation_rule.');
  }
  if (typeof payload.summary !== 'string') {
    throw new ContractValidationError('Missing or non-string summary.');
  }

  // 6. Dimensions
  if (typeof payload.dimensions !== 'object' || payload.dimensions === null || Array.isArray(payload.dimensions)) {
    throw new ContractValidationError('Missing or invalid dimensions object.');
  }

  const rawDimensions = payload.dimensions as Record<string, unknown>;
  const validatedDimensions: Record<string, DimensionStatus> = {};

  for (const [key, dimValue] of Object.entries(rawDimensions)) {
    validatedDimensions[key] = validateDimension(dimValue, key);
  }

  return Object.freeze({
    schema_version: payload.schema_version,
    commit_sha: payload.commit_sha,
    evaluated_at: payload.evaluated_at,
    overall_status: payload.overall_status,
    aggregation_rule: payload.aggregation_rule,
    summary: payload.summary,
    dimensions: Object.freeze(validatedDimensions),
  });
}
