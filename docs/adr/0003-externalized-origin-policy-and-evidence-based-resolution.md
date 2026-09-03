# ADR 0003: Externalized Origin Policy and Evidence-Based Resolution

**Status:** Accepted
**Date:** 2026-09-03
**Scope:** Ingestion pipeline, technology demand acquisition, and jurisdiction classification

## Context

Abell Nexus ingests market demand signals across diverse open innovation channels (initially InnoGet) to evaluate technology demands against domestic intellectual property. Under the Scientific Study Protocol (Section 3.4), an industrial challenge must be verified as originating from or actively involving a Spanish enterprise to enter the primary evaluation cohort.

Previously, early exploratory prototypes suffered from architectural deficiencies:
1. Hardcoded in-code lookup tables (`KNOWN_SPANISH_ORGANIZATIONS`, `EXPLICIT_NON_SPANISH_COUNTRIES`).
2. Conflation of factual DOM extraction with normative jurisdiction policy.
3. Asymmetric negative heuristics (`country != Spain => NON_SPANISH`), erroneously classifying unknown or unverified data as foreign.
4. Spurious Level 3 classifications based on textual corporate suffixes (`S.L.`, `S.A.`) without independent registry verification.
5. In-code fallback policies fabricating default configurations when configuration files were absent.
6. Local non-versioned test fixtures breaking clean checkouts in continuous integration environments.

## Decision

We establish an immutable Clean Architecture separation between **Factual Extraction**, **Declarative Policy**, and **Origin Resolution**:

```text
                  ┌────────────────────────────────────────┐
                  │ config/policies/data/jurisdiction.json │
                  │  (versioned, cryptographic SHA-256)    │
                  └───────────────────┬────────────────────┘
                                      │
Raw HTML Payload                      ▼
       │                      OriginPolicyConfig
       ▼                              │
InnoGetExtractor                      │
 (Factual DOM/meta parsing)           │
       │                              │
       ▼                              │
RawExtractedDemandFields              ▼
       │                    DefaultOriginResolver
       └──────────────────────────────┬──────────────────────────────┐
                                      │                              │
                                      ▼                              ▼
                              OriginAssessment                FieldObservation
                                      │                     (Auditable provenance,
                                      ▼                      VerificationStatus)
                            InnogetHtmlNormalizer
                                      │
                                      ▼
                          DemandNormalizationResult
                       (INCLUDED / EXCLUDED / QUARANTINED)
```

### 1. Externalized, Cryptographically Versioned Policy (`OriginPolicyConfig`)
- All jurisdiction definitions, canonical names, and linguistic aliases are declared in version-controlled JSON (`config/policies/data/jurisdiction_policy.json`).
- Production code contains **zero hardcoded country lists, organization lists, or corporate suffixes**.
- `OriginPolicyConfig` computes a bit-exact SHA-256 digest (`policy_sha256`) over canonical JSON upon loading.
- **Fail-Fast Invariant:** If the configuration file is missing or invalid, system initialization immediately raises an error (`FileNotFoundError` / `ValueError`). No synthetic in-memory policy is fabricated.

### 2. Symmetrical Tripartite Classification (`UNKNOWN != FOREIGN`)
- **Direct Target Match:** Factual country token matches target jurisdiction (`policy.target_jurisdiction`) $\to$ `LEVEL_1_DIRECT_METADATA` ($\to$ `INCLUDED`).
- **Foreign Jurisdiction Match:** Factual country token matches another recognized jurisdiction in policy $\to$ `NON_SPANISH` ($\to$ `EXCLUDED_NON_SPANISH`).
- **Unrecognized / Missing Tokens:** Missing country, corrupted tokens, or unrecognized country names map strictly to `UNVERIFIED` ($\to$ `EXCLUDED_UNVERIFIED_ORIGIN`). Unknown data is never assumed to be foreign.

### 3. Concrete Level Hierarchy and Level 3 Boundary
- **Level 1:** Direct platform metadata explicitly proves target jurisdiction.
- **Level 2:** Sponsoring organization location metadata explicitly proves target jurisdiction (`organization_location_raw`).
- **Level 3:** Independent authoritative registry cross-check (`ExternalRegistryVerifier` protocol). Textual corporate forms (`S.L.`, `S.A.`) alone **never** confer Level 3 status.
- **Scope Boundary:** This PR defines the `ExternalRegistryVerifier` contract and tests it using test doubles. Production integrations with the Spanish Mercantile Registry (RMC) or EU VIES registry are intentionally scheduled for future data platform iterations.

### 4. Unified Provenance via `FieldObservation`
- The system eliminates redundant evidence models. All evidentiary justifications are stored as typed `FieldObservation` records referencing:
  - `entity_id` and `field_name`.
  - `observed_value_json` and `source_authority`.
  - `source_uri`, `retrieval_timestamp`, and `raw_payload_sha256`.
  - `verification_status` (`SOURCE_REPORTED` vs. `INDEPENDENTLY_VERIFIED`).
- Every `OriginAssessment` stamps `policy_id`, `policy_version`, and `policy_sha256`.

### 5. Deterministic, Version-Controlled Test Fixtures
- All test payloads reside canonically under `backend/test/fixtures/` and are tracked directly in Git. Tests must not reference unversioned local paths.

## Consequences

### Positive
- **Reproducibility:** Any historical extraction can be reconstructed bit-for-bit using `raw_payload_sha256` + `policy_sha256` + `extraction_version`.
- **Portability:** Nexus can target alternative jurisdictions (e.g. Germany `DE`, France `FR`) solely by providing an alternative policy JSON without modifying Python code.
- **Auditable Integrity:** Zero synthetic data or speculative heuristics in production pipelines.

### Negative / Trade-offs
- Demands lacking explicit country or location metadata are classified as `UNVERIFIED` and excluded from the domestic cohort until verifiable registry integrations are executed.
