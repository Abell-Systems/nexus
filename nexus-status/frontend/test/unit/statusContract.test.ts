import fs from 'node:fs';
import path from 'node:path';
import { describe, it, expect } from 'vitest';
import {
  CANONICAL_STATUSES,
  parseProjectStatus,
  isStatusValue,
  ContractValidationError,
  type ProjectStatus,
} from '../../src/domain/status';

describe('Project Status Contract v1 Domain Model', () => {
  describe('Canonical 5-State Vocabulary (ADR 0022)', () => {
    it('defines exactly the five canonical statuses with symmetrical semantics', () => {
      expect(CANONICAL_STATUSES).toEqual([
        'PASS',
        'FAIL',
        'UNVERIFIED',
        'SKIPPED',
        'N/A',
      ]);
    });

    it('identifies valid status values via isStatusValue guard', () => {
      expect(isStatusValue('PASS')).toBe(true);
      expect(isStatusValue('FAIL')).toBe(true);
      expect(isStatusValue('UNVERIFIED')).toBe(true);
      expect(isStatusValue('SKIPPED')).toBe(true);
      expect(isStatusValue('N/A')).toBe(true);

      expect(isStatusValue('UNKNOWN')).toBe(false);
      expect(isStatusValue('SUCCESS')).toBe(false);
      expect(isStatusValue('pass')).toBe(false);
      expect(isStatusValue('')).toBe(false);
      expect(isStatusValue(null)).toBe(false);
      expect(isStatusValue(1)).toBe(false);
    });
  });

  describe('Contract Parsing and Invariants', () => {
    const validMinimalPayload = {
      schema_version: '1.0.0',
      commit_sha: '0123456789abcdef0123456789abcdef01234567',
      evaluated_at: '2026-09-09T08:00:00.000000+00:00',
      overall_status: 'PASS',
      aggregation_rule: 'All required dimensions verified and passed.',
      summary: 'Nexus Project Status evaluates to PASS.',
      dimensions: {
        backend_testing: {
          status: 'PASS',
          requirement_level: 'required',
          evidence_source: 'pytest-results.xml',
          evidence_available: true,
          message: '505 passed',
          metrics: { total: 505, passed: 505 },
          checks: [
            {
              name: 'pytest_all_passed',
              status: 'PASS',
              value: 505,
              detail: '505 passed in test suite',
            },
          ],
        },
      },
    };

    it('accepts a fully compliant canonical contract payload', () => {
      const status: ProjectStatus = parseProjectStatus(validMinimalPayload);

      expect(status.schema_version).toBe('1.0.0');
      expect(status.commit_sha).toBe('0123456789abcdef0123456789abcdef01234567');
      expect(status.evaluated_at).toBe('2026-09-09T08:00:00.000000+00:00');
      expect(status.overall_status).toBe('PASS');
      expect(status.aggregation_rule).toBe('All required dimensions verified and passed.');
      expect(status.summary).toBe('Nexus Project Status evaluates to PASS.');
      expect(status.dimensions.backend_testing).toBeDefined();
      expect(status.dimensions.backend_testing.status).toBe('PASS');
      expect(status.dimensions.backend_testing.evidence_source).toBe('pytest-results.xml');
      expect(status.dimensions.backend_testing.evidence_available).toBe(true);
      expect(status.dimensions.backend_testing.checks).toHaveLength(1);
    });

    it('preserves exact epistemic status values without recalculation or mutation', () => {
      const payloadWithDiverseStatuses = {
        ...validMinimalPayload,
        overall_status: 'UNVERIFIED',
        dimensions: {
          science_dimension: {
            status: 'SKIPPED',
            requirement_level: 'required',
            evidence_source: 'audit_dataset_identity.py',
            evidence_available: true,
            checks: [
              {
                name: 'temporal_eligibility',
                status: 'SKIPPED',
                detail: 'Frozen exception policy applied under ADR 0019',
              },
            ],
          },
          external_audit: {
            status: 'UNVERIFIED',
            requirement_level: 'optional',
            evidence_source: 'sonar_cloud',
            evidence_available: false,
            checks: [],
          },
          failing_dimension: {
            status: 'FAIL',
            requirement_level: 'required',
            evidence_source: 'ruff',
            evidence_available: true,
            checks: [
              {
                name: 'lint_errors',
                status: 'FAIL',
                value: 3,
                detail: '3 lint errors found',
              },
            ],
          },
          not_applicable_dim: {
            status: 'N/A',
            requirement_level: 'optional',
            evidence_source: 'adk_provider',
            evidence_available: false,
            checks: [],
          },
        },
      };

      const parsed = parseProjectStatus(payloadWithDiverseStatuses);

      // Epistemic invariant: SKIPPED remains SKIPPED, UNVERIFIED remains UNVERIFIED, FAIL remains FAIL
      expect(parsed.overall_status).toBe('UNVERIFIED');
      expect(parsed.dimensions.science_dimension.status).toBe('SKIPPED');
      expect(parsed.dimensions.external_audit.status).toBe('UNVERIFIED');
      expect(parsed.dimensions.failing_dimension.status).toBe('FAIL');
      expect(parsed.dimensions.not_applicable_dim.status).toBe('N/A');

      // Epistemic invariant: provenance and check details are preserved exactly
      expect(parsed.dimensions.science_dimension.checks[0].status).toBe('SKIPPED');
      expect(parsed.dimensions.science_dimension.checks[0].detail).toBe(
        'Frozen exception policy applied under ADR 0019'
      );
      expect(parsed.dimensions.failing_dimension.checks[0].value).toBe(3);
    });

    it('preserves unknown or future dimensions without fabricating domain meaning', () => {
      const payloadWithFutureDimension = {
        ...validMinimalPayload,
        dimensions: {
          ...validMinimalPayload.dimensions,
          future_quantum_integrity: {
            status: 'PASS',
            requirement_level: 'optional',
            evidence_source: 'quantum_sim.xml',
            evidence_available: true,
            message: 'All qubits aligned',
            checks: [],
          },
        },
      };

      const parsed = parseProjectStatus(payloadWithFutureDimension);
      expect(parsed.dimensions.future_quantum_integrity).toBeDefined();
      expect(parsed.dimensions.future_quantum_integrity.status).toBe('PASS');
      expect(parsed.dimensions.future_quantum_integrity.evidence_source).toBe('quantum_sim.xml');
      expect(parsed.dimensions.future_quantum_integrity.message).toBe('All qubits aligned');
    });

    it('rejects payloads with missing mandatory root fields', () => {
      expect(() => parseProjectStatus(null)).toThrow(ContractValidationError);
      expect(() => parseProjectStatus({})).toThrow(ContractValidationError);
      expect(() =>
        parseProjectStatus({ ...validMinimalPayload, schema_version: undefined })
      ).toThrow(ContractValidationError);
      expect(() =>
        parseProjectStatus({ ...validMinimalPayload, commit_sha: '' })
      ).toThrow(ContractValidationError);
      expect(() =>
        parseProjectStatus({ ...validMinimalPayload, evaluated_at: 'not-a-date' })
      ).toThrow(ContractValidationError);
      expect(() =>
        parseProjectStatus({ ...validMinimalPayload, dimensions: null })
      ).toThrow(ContractValidationError);
    });

    it('rejects unsupported schema versions', () => {
      expect(() =>
        parseProjectStatus({ ...validMinimalPayload, schema_version: '2.0.0' })
      ).toThrow(ContractValidationError);
      expect(() =>
        parseProjectStatus({ ...validMinimalPayload, schema_version: '0.9.0' })
      ).toThrow(ContractValidationError);
    });

    it('rejects payloads with unknown overall status', () => {
      expect(() =>
        parseProjectStatus({
          ...validMinimalPayload,
          overall_status: 'SUCCESS',
        })
      ).toThrow(ContractValidationError);

      expect(() =>
        parseProjectStatus({
          ...validMinimalPayload,
          overall_status: 'UNKNOWN',
        })
      ).toThrow(ContractValidationError);
    });

    it('rejects dimensions with invalid status or requirement level', () => {
      expect(() =>
        parseProjectStatus({
          ...validMinimalPayload,
          dimensions: {
            test_dim: {
              ...validMinimalPayload.dimensions.backend_testing,
              status: 'INVALID_STATUS',
            },
          },
        })
      ).toThrow(ContractValidationError);

      expect(() =>
        parseProjectStatus({
          ...validMinimalPayload,
          dimensions: {
            test_dim: {
              ...validMinimalPayload.dimensions.backend_testing,
              requirement_level: 'mandatory', // must be 'required' | 'optional'
            },
          },
        })
      ).toThrow(ContractValidationError);
    });

    it('rejects checks with invalid status or missing name', () => {
      expect(() =>
        parseProjectStatus({
          ...validMinimalPayload,
          dimensions: {
            test_dim: {
              ...validMinimalPayload.dimensions.backend_testing,
              checks: [{ name: '', status: 'PASS' }],
            },
          },
        })
      ).toThrow(ContractValidationError);

      expect(() =>
        parseProjectStatus({
          ...validMinimalPayload,
          dimensions: {
            test_dim: {
              ...validMinimalPayload.dimensions.backend_testing,
              checks: [{ name: 'check1', status: 'GREEN' }],
            },
          },
        })
      ).toThrow(ContractValidationError);

      expect(() =>
        parseProjectStatus({
          ...validMinimalPayload,
          dimensions: {
            test_dim: {
              ...validMinimalPayload.dimensions.backend_testing,
              checks: 'not-an-array' as unknown as [],
            },
          },
        })
      ).toThrow(ContractValidationError);
    });

    it('rejects evaluated_at timestamps that are not strictly ISO-8601', () => {
      expect(() =>
        parseProjectStatus({
          ...validMinimalPayload,
          evaluated_at: '2026/09/09 10:00:00', // parseable by Date.parse but NOT ISO-8601
        })
      ).toThrow(ContractValidationError);
    });

    it('successfully parses the actual repository project_status.json contract', () => {
      const rootContractPath = path.resolve(__dirname, '../../../../project_status.json');
      expect(fs.existsSync(rootContractPath)).toBe(true);
      const raw = JSON.parse(fs.readFileSync(rootContractPath, 'utf-8'));
      const parsed = parseProjectStatus(raw);
      expect(parsed.schema_version).toBe('1.0.0');
      expect(parsed.overall_status).toBe('PASS');
      expect(Object.keys(parsed.dimensions).length).toBeGreaterThanOrEqual(7);
      expect(parsed.dimensions.backend_testing.status).toBe('PASS');
      expect(parsed.dimensions.architecture.status).toBe('PASS');
      expect(parsed.dimensions.documentation.status).toBe('PASS');
      expect(parsed.dimensions.scientific_integrity.status).toBe('PASS');
    });
  });
});
