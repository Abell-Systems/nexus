// Hand-authored mirror of backend/patent_agent/tools/schemas.py — keep in sync.

export interface PatentRecord {
  publication_number: string;
  title: string;
  abstract: string;
  assignee: string[];
  inventors: string[];
  filing_date: string;
  publication_date: string;
  priority_date: string | null;
  country_code: string;
  cpc_codes: string[];
  family_id: string | null;
  citation_count: number;
  similarity_score: number | null;
}

export interface PatentCluster {
  cluster_id: string;
  label: string;
  representative_patents: string[];
  patent_count: number;
  white_space_score: number;
  is_white_space: boolean;
}

export interface InventionCandidate {
  candidate_id: string;
  cluster_id: string;
  title: string;
  description: string;
  claimed_novelty: string;
}

export interface AdversarialVerdict {
  candidate_id: string;
  verdict: "survives" | "rejected";
  rationale: string;
  cited_patents: string[];
}

export interface DemandSignal {
  source: string;
  id: string;
  title: string;
  description: string;
  cpc_prefix: string | null;
  posted_date: string;
  url: string;
}

export interface ScoreCardList {
  scorecards: ScoreCard[];
}

export interface ScoreCard {
  candidate_id: string;
  novelty: number;
  prior_art_risk: number;
  differentiation: number;
  evidence: number;
  supporting_evidence: string[];
  summary: string;
}

export type PipelineStage =
  | "queued"
  | "researching"
  | "clustering"
  | "inventing"
  | "adversarial"
  | "governor"
  | "done"
  | "error";

export type AgentEventType =
  | "research_completed"
  | "landscape_clustered"
  | "candidate_generated"
  | "candidate_challenged"
  | "candidate_rejected"
  | "candidate_revised"
  | "candidate_survived"
  | "assessment_completed";

export interface AgentEventItem {
  type: AgentEventType | string;
  timestamp: string;
  message: string;
  candidateId?: string;
  evidence?: unknown;
}

export interface JobProgress {
  patentsAnalyzed?: number;
  clustersFound?: number;
  candidatesGenerated?: number;
  candidatesRejected?: number;
  candidatesRevised?: number;
  candidatesSurvived?: number;
}

export interface JobStatusResponse {
  job_id?: string;
  domain?: string;
  query?: string;
  status: "running" | "done" | "error";
  stage: PipelineStage;
  progress?: JobProgress;
  events?: AgentEventItem[];
  clusters?: PatentCluster[];
  candidates?: InventionCandidate[];
  verdicts?: AdversarialVerdict[];
  scorecards?: ScoreCard[];
  error?: string;
  error_type?: "quota_exhausted" | "timeout" | "unknown";
  detail?: string;
}

export interface JobSummary {
  job_id: string;
  domain: string | null;
  query: string | null;
  status: "running" | "done" | "error";
  stage: PipelineStage;
  created_at: string | null;
  candidate_count: number;
}


