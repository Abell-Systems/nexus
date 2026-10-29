// Mirrors build_topic_result (backend application/whitespace/topic_map.py), schema "topic-map/1".
export interface TopicMapResult {
  schema: string;
  configuration: {
    id: string;
    parameters: {
      schema: string;
      definition_id: string;
      applicant_rules_id: string;
      min_observed: number;
      min_expected: number;
      max_ratio: number;
      unit: string;
    };
  };
  corpus: { source_id: string; files: Record<string, string> };
  names_reviewed: boolean;
  unreviewed: string[];
  topic: { key: string; name: string; noun: string; joined: string };
  total_documents: number;
  corpus_documents: number;
  // sorted years with corpus units; 2010 is absent
  years: number[];
  // share is a PERCENT (0-100)
  trend: { year: number; documents: number; share: number; ep_documents: number }[];
  // FRACTION (0-1), 0 when the topic has no units
  ep_share: number;
  // by_year is aligned with years; null when nobody was active in the last two years
  top_applicant_recent: { name: string; by_year: number[] } | null;
  subareas: { key: string; name: string; description: string; documents: number; series: number[] }[];
  neighbours: { subclass: string; name: string; documents: number }[];
  rare: { subclass: string; name: string; observed: number; expected: number; ratio: number }[];
  applicants: { name: string; documents: number; originals: string[] }[];
}
