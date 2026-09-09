import { describe, it, expect } from 'vitest';
import {
  TRACK_VALUES,
  parseScientificResults,
  ScientificResultsValidationError,
} from '../../src/domain/scientificResults';

function baseDocument(overrides: Record<string, unknown> = {}) {
  return {
    schema_version: '0.1.0',
    generated_at: '2026-09-09T11:26:54.982691Z',
    executions: [],
    landscapes: [],
    candidates: [],
    verifications: [],
    matches: [],
    ...overrides,
  };
}

function discoveryExecution(overrides: Record<string, unknown> = {}) {
  return {
    execution_id: 'exec-0001',
    track: 'discovery',
    domain: 'solid_state_battery',
    query: 'solid electrolyte',
    created_at: '2026-09-09T11:26:54.982691Z',
    dataset_id: null,
    dataset_version: null,
    engine_commit: null,
    policy_id: null,
    policy_version: null,
    policy_sha256: null,
    source_provenance: [
      { role: 'patents', kind: 'mock' },
      { role: 'demand', kind: 'MockDemandDataSource' },
    ],
    ...overrides,
  };
}

function verificationExecution(overrides: Record<string, unknown> = {}) {
  return discoveryExecution({ execution_id: 'exec-verify-0001', track: 'verification', ...overrides });
}

const DISCLAIMER = 'Nexus generated/discovered this output; not scientifically verified evidence.';

function clusterObservation() {
  return {
    cluster: {
      cluster_id: 'H01M',
      label: 'Solid State Battery - H01M',
      representative_patents: ['US-11223001-B2'],
      patent_count: 3,
      white_space_score: 0.4608,
      is_white_space: false,
    },
    density: 1.0,
    recency: 0.7,
    citation_traction: 0.4722,
    citation_coverage: 1.0,
    demand_intensity: 1.0,
    quadrant: 'Quadrant II (Co-developed / Saturated)',
    mean_age_years: 6.0,
  };
}

describe('Scientific Results Contract v1 Domain Model (ADR 0025)', () => {
  describe('Track vocabulary', () => {
    it('defines exactly the two canonical tracks', () => {
      expect(TRACK_VALUES).toEqual(['discovery', 'verification']);
    });
  });

  describe('Top-level envelope', () => {
    it('parses a minimal, empty valid document', () => {
      const doc = parseScientificResults(baseDocument());
      expect(doc.schema_version).toBe('0.1.0');
      expect(doc.executions).toEqual([]);
      expect(doc.landscapes).toEqual([]);
    });

    it('rejects a payload missing schema_version', () => {
      const { schema_version, ...rest } = baseDocument();
      expect(() => parseScientificResults(rest)).toThrow(ScientificResultsValidationError);
    });

    it('rejects a payload with an invalid generated_at timestamp', () => {
      expect(() => parseScientificResults(baseDocument({ generated_at: 'not-a-date' }))).toThrow(
        ScientificResultsValidationError
      );
    });

    it('rejects a non-object payload', () => {
      expect(() => parseScientificResults('not-a-document')).toThrow(ScientificResultsValidationError);
      expect(() => parseScientificResults(null)).toThrow(ScientificResultsValidationError);
      expect(() => parseScientificResults(42)).toThrow(ScientificResultsValidationError);
    });
  });

  describe('Executions', () => {
    it('parses a valid discovery execution including source_provenance', () => {
      const doc = parseScientificResults(baseDocument({ executions: [discoveryExecution()] }));
      expect(doc.executions[0].track).toBe('discovery');
      expect(doc.executions[0].source_provenance).toEqual([
        { role: 'patents', kind: 'mock' },
        { role: 'demand', kind: 'MockDemandDataSource' },
      ]);
    });

    it('preserves absent dataset/policy provenance as null, never fabricating a value', () => {
      const doc = parseScientificResults(baseDocument({ executions: [discoveryExecution()] }));
      expect(doc.executions[0].dataset_id).toBeNull();
      expect(doc.executions[0].policy_version).toBeNull();
    });

    it('rejects an execution with an invalid track value', () => {
      const exec = discoveryExecution({ track: 'synthesis' });
      expect(() => parseScientificResults(baseDocument({ executions: [exec] }))).toThrow(
        ScientificResultsValidationError
      );
    });

    it('rejects an execution with a non-ISO created_at', () => {
      const exec = discoveryExecution({ created_at: 'yesterday' });
      expect(() => parseScientificResults(baseDocument({ executions: [exec] }))).toThrow(
        ScientificResultsValidationError
      );
    });

    it('rejects duplicate execution_id values', () => {
      const exec = discoveryExecution();
      expect(() => parseScientificResults(baseDocument({ executions: [exec, exec] }))).toThrow(
        /Duplicate execution_id/
      );
    });
  });

  describe('Discovery/verification track separation (ADR 0025 §1)', () => {
    it('accepts a landscape record referencing a discovery execution', () => {
      const doc = parseScientificResults(
        baseDocument({
          executions: [discoveryExecution()],
          landscapes: [
            { execution_id: 'exec-0001', query: 'solid electrolyte', clusters: [clusterObservation()], disclaimer: DISCLAIMER },
          ],
        })
      );
      expect(doc.landscapes[0].clusters[0].cluster.cluster_id).toBe('H01M');
    });

    it('rejects a landscape record referencing a verification execution', () => {
      expect(() =>
        parseScientificResults(
          baseDocument({
            executions: [verificationExecution()],
            landscapes: [
              { execution_id: 'exec-verify-0001', query: 'q', clusters: [], disclaimer: DISCLAIMER },
            ],
          })
        )
      ).toThrow(/discovery and verification cannot be mixed/);
    });

    it('rejects a record referencing an unknown execution_id', () => {
      expect(() =>
        parseScientificResults(
          baseDocument({
            landscapes: [{ execution_id: 'does-not-exist', query: 'q', clusters: [], disclaimer: DISCLAIMER }],
          })
        )
      ).toThrow(/unknown execution_id/);
    });

    it('accepts a match record referencing a verification execution', () => {
      const doc = parseScientificResults(
        baseDocument({
          executions: [verificationExecution()],
          matches: [
            {
              execution_id: 'exec-verify-0001',
              assessment: {
                demand_id: 'INNOGET-0001',
                publication_id: 'EXAMPLE-PATENT-0001',
                overall_score: 0.72,
                confidence: 'moderate',
                sufficiency: 'sufficient',
                rationale: 'Shared CPC classification.',
                policy_id: 'default-matching-policy',
                policy_version: '1.0.0',
                policy_sha256: 'a'.repeat(64),
                fusion_transform_id: 'adr0016-fusion-v1',
              },
            },
          ],
        })
      );
      expect(doc.matches[0].assessment.publication_id).toBe('EXAMPLE-PATENT-0001');
    });

    it('rejects a match record referencing a discovery execution', () => {
      expect(() =>
        parseScientificResults(
          baseDocument({
            executions: [discoveryExecution()],
            matches: [
              {
                execution_id: 'exec-0001',
                assessment: {
                  demand_id: 'd', publication_id: 'p', overall_score: 0.1, confidence: 'weak',
                  sufficiency: 'partial', rationale: 'r', policy_id: 'p', policy_version: '1',
                  policy_sha256: 'a'.repeat(64), fusion_transform_id: 't',
                },
              },
            ],
          })
        )
      ).toThrow(/discovery and verification cannot be mixed/);
    });
  });

  describe('Discovery candidates and verifications', () => {
    it('parses a valid candidate record', () => {
      const doc = parseScientificResults(
        baseDocument({
          executions: [discoveryExecution()],
          candidates: [
            {
              execution_id: 'exec-0001',
              candidate: {
                candidate_id: 'cand-0001',
                cluster_id: 'H01M',
                title: 'Composite electrolyte membrane',
                description: 'A layered membrane design.',
                claimed_novelty: '',
              },
              disclaimer: DISCLAIMER,
            },
          ],
        })
      );
      expect(doc.candidates[0].candidate.candidate_id).toBe('cand-0001');
    });

    it('parses a not_yet_challenged verification with no verdict or citations', () => {
      const doc = parseScientificResults(
        baseDocument({
          executions: [discoveryExecution()],
          verifications: [
            {
              execution_id: 'exec-0001',
              candidate_id: 'cand-0001',
              challenge_status: 'not_yet_challenged',
              verdict: null,
              scorecard: null,
              citations: [],
              disclaimer: DISCLAIMER,
            },
          ],
        })
      );
      expect(doc.verifications[0].challenge_status).toBe('not_yet_challenged');
      expect(doc.verifications[0].verdict).toBeNull();
    });

    it('rejects a verification with an invalid challenge_status', () => {
      expect(() =>
        parseScientificResults(
          baseDocument({
            executions: [discoveryExecution()],
            verifications: [
              {
                execution_id: 'exec-0001',
                candidate_id: 'cand-0001',
                challenge_status: 'maybe',
                citations: [],
                disclaimer: DISCLAIMER,
              },
            ],
          })
        )
      ).toThrow(ScientificResultsValidationError);
    });

    it('parses a resolved citation and rejects an unresolved one carrying resolved metadata mismatched shape gracefully', () => {
      const doc = parseScientificResults(
        baseDocument({
          executions: [discoveryExecution()],
          verifications: [
            {
              execution_id: 'exec-0001',
              candidate_id: 'cand-0001',
              challenge_status: 'challenged',
              verdict: {
                candidate_id: 'cand-0001',
                verdict: 'survives',
                rationale: 'No anticipating prior art found.',
                cited_patents: ['EXAMPLE-PATENT-0001'],
              },
              scorecard: null,
              citations: [
                { publication_id: 'EXAMPLE-PATENT-0001', role: 'challenges', resolution: 'unresolved', title: null, publication_date: null },
              ],
              disclaimer: DISCLAIMER,
            },
          ],
        })
      );
      expect(doc.verifications[0].citations[0].resolution).toBe('unresolved');
      expect(doc.verifications[0].citations[0].title).toBeNull();
    });
  });

  describe('Real committed snapshot (repo root scientific_results.json)', () => {
    it('parses the actual published artifact end to end', async () => {
      const fs = await import('node:fs');
      const path = await import('node:path');
      const rootPath = path.resolve(__dirname, '../../../../scientific_results.json');
      const raw = JSON.parse(fs.readFileSync(rootPath, 'utf-8'));

      const doc = parseScientificResults(raw);
      expect(doc.executions[0].track).toBe('discovery');
      expect(doc.landscapes[0].clusters.length).toBeGreaterThan(0);
      expect(doc.candidates).toEqual([]);
      expect(doc.matches).toEqual([]);
    });
  });
});
