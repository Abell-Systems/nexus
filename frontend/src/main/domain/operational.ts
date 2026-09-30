export interface DemandExample {
  demand_id: string;
  title: string;
  description: string;
  origin_country: string | null;
  posted_date: string | null;
  source_url: string;
}

export interface DemandExamplesResponse {
  demands: DemandExample[];
  notices: string[];
}

export interface AssetResult {
  rank: number;
  publication_id: string;
  title: string;
  ip_type: string;
  country_code: string;
  kind_code: string;
  assignees: string[];
  inventors: string[];
  publication_date: string | null;
  abstract: string;
  abstract_language: string;
  cpc_codes: string[];
  source_links: { google_patents: string; espacenet: string };
}

export interface MatchesResponse {
  demand: { demand_id: string; title: string; description: string; source_url: string };
  assets: AssetResult[];
  meta: {
    retrieval: string;
    eligible_count: number;
    corpus_id: string;
    corpus_parquet_sha256: string;
    embedding_index_sha256: string;
    notices: string[];
  };
}
