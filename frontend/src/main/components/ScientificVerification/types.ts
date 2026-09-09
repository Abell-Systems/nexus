/**
 * Data contracts for Scientific Verification.
 * Conforms to ADR 0022 and docs/schemas/project-status-v1.json.
 */

export type StatusValue = "PASS" | "FAIL" | "SKIPPED" | "UNVERIFIED" | "N/A";
export type RequirementLevel = "required" | "optional";

export interface CheckResult {
  name: string;
  status: StatusValue;
  value?: number | string | null;
  threshold?: number | string | null;
  detail?: string | null;
  reason?: string | null;
  policy_ref?: string | null;
}

export interface DimensionResult {
  status: StatusValue;
  requirement_level: RequirementLevel;
  evidence_source: string;
  evidence_available: boolean;
  message?: string;
  metrics?: Record<string, number>;
  checks: CheckResult[];
}

export interface ProjectStatusPayload {
  schema_version: string;
  commit_sha: string;
  evaluated_at: string;
  overall_status: StatusValue;
  aggregation_rule: string;
  summary?: string;
  dimensions: Record<string, DimensionResult>;
}

export interface MilestoneItem {
  id: string;
  title: string;
  description: string;
  dimension_key?: string; // Optional linkage to project_status.json dimension
  phase: string;
}

export interface EpistemicBoundaries {
  demonstrated: string[];
  not_yet_demonstrated: string[];
  next_scientific_step: {
    title: string;
    description: string;
    target_milestone: string;
  };
}

export interface ScientificContext {
  project_overview: {
    title: string;
    tagline: string;
    description: string;
    protocol_url: string;
    repository_url: string;
  };
  milestones: MilestoneItem[];
  epistemic_boundaries: EpistemicBoundaries;
}

export interface PillarViewModel {
  name: string;
  status: StatusValue;
  summary: string;
  checks: CheckResult[];
  hasAcceptedExceptions?: boolean;
}

export interface VerificationViewModel {
  provenance: {
    commitSha: string;
    evaluatedAt: string;
    datasetId?: string;
  };
  overallStatus: StatusValue;
  isVerified: boolean;
  pillars: {
    dataIntegrity: PillarViewModel;
    protocol: PillarViewModel;
    reproducibility: PillarViewModel;
  };
  conclusion: string;
  rawPayload: ProjectStatusPayload;
  context: ScientificContext;
}
