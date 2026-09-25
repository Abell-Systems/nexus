# ADR 0032: Phase-2 Corpus Expansion Acquisition, Structured Temporal Evidence, and Offline Validation

**Status:** Accepted  
**Date:** 2026-09-11  
**Scope:** Formalizes the operational acquisition architecture for Milestone #101b, defines the structured `PublicationDateEvidence` contract and closed evidence taxonomy, establishes strict separation between unverifiable dates and out-of-window dates, enforces immutable raw storage, decouples candidate mapping from offline policy validation, and establishes formal partition invariants.

---

## 1. Context & Problem Statement

ADR 0031 established the binding acquisition and sampling frame contract for Phase-2 demand corpus expansion towards $N_{\mathrm{power}} = N_{\mathrm{eligible, independent}} \ge 60$ observations, defining authorized sources (InnoGet, EEN/POD), geographic strata (`spain`, `international_european`), and candidate exclusion criteria.

To transition from the contract definition (Milestone #101a) to empirical data acquisition (Milestone #101b) without compromising scientific validity, five critical operational challenges must be resolved:

1. **Date Provenance Divergence:** Primary sources record dates differently. EEN/POD listings encode publication dates deterministically in the POD reference (e.g. `TRES20250806011` $\to$ `2025-08-06`), whereas InnoGet detail pages prominently display proposal deadlines (`Deadline at DD/MM/YYYY`) and may omit an explicit public posting timestamp. Substituting a deadline or crawler access timestamp for $t_{\mathrm{demand}}$ would introduce unacceptable temporal confounding.
2. **Conflating Uncertainty with Negation:** Treating candidates with missing or unverifiable publication dates as `OUT_OF_TEMPORAL_WINDOW` commits a methodological error: failing to prove that a solicitation falls within `[2020-01-01, 2025-12-31]` does not prove it falls outside that window.
3. **Conflating Operational Failures with Scientific Policy Decisions:** A malformed HTML payload, network timeout, or crawler DOM breakage is an operational acquisition error, not a scientific candidate rejection under pre-registered eligibility criteria.
4. **Offline Reproducibility:** Reviewers and CI gates must be able to audit and reproduce candidate parsing and policy validation deterministically without performing live web scraping or relying on internet connectivity.
5. **Separation of Acquisition Yield from Statistical Sufficiency:** PR #101b must not prematurely declare $N_{\mathrm{power}} \ge 60$ simply by counting accepted candidates. Statistical observation units must remain subject to the multidimensional independence audit in Milestone #102 (organization, sector, technology family, and duplicate industrial problem).

---

## 2. Decision & Architectural Contracts

### 2.1 Structured Temporal Evidence (`PublicationDateEvidence`)
Publication date provenance is modeled explicitly in the domain layer (`backend/src/main/domain/models/corpus_expansion.py`) as a structured, immutable evidence object:

```python
class PublicationDateEvidenceType(StrEnum):
    POD_REFERENCE = "pod_reference"
    EXPLICIT_METADATA = "explicit_metadata"
    HISTORICAL_FEED = "historical_feed"
    UNVERIFIABLE = "unverifiable"

class PublicationDateEvidence(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    publication_date: date | None = None
    evidence_type: PublicationDateEvidenceType
    evidence_field: str = Field(..., min_length=1)
    evidence_value: str = Field(..., min_length=1)
```

**Normative Invariant:**
`publication_date` MUST represent the authentic original public publication or creation date of the solicitation. Acquisition timestamps, crawler execution times, access dates, cache snapshots, syndication republishing times, or application deadlines (`deadline_raw`) MUST NEVER be substituted for $t_{\mathrm{demand}}$.

When a valid publication date cannot be independently verified from primary evidence:
- `publication_date` evaluates strictly to `None`.
- `evidence_type` evaluates to `PublicationDateEvidenceType.UNVERIFIABLE`.
- `evidence_field` and `evidence_value` preserve the observed raw field and string (e.g. observed deadline text) so that auditors have complete visibility into why the date was unresolvable.

### 2.2 Rejection Taxonomy: `UNVERIFIABLE_PUBLICATION_DATE` vs `OUT_OF_TEMPORAL_WINDOW`
The candidate rejection taxonomy is expanded with an explicit, distinct code:
```python
class CandidateRejectionReason(StrEnum):
    ...
    OUT_OF_TEMPORAL_WINDOW = "OUT_OF_TEMPORAL_WINDOW"
    UNVERIFIABLE_PUBLICATION_DATE = "UNVERIFIABLE_PUBLICATION_DATE"
    ...
```

The policy validator (`validate_demand_candidate`) applies the temporal criterion in mutually exclusive branches:
1. **Unverifiable Date:**
   If `candidate.publication_date is None`:
   $\longrightarrow$ append `CandidateRejectionReason.UNVERIFIABLE_PUBLICATION_DATE`.
2. **Verifiable Date Outside Range:**
   If `candidate.publication_date is not None`:
   $\longrightarrow$ if `candidate.publication_date < min_date` or `candidate.publication_date > max_date`:
   $\longrightarrow$ append `CandidateRejectionReason.OUT_OF_TEMPORAL_WINDOW`.
3. **Verifiable Date Inside Range:**
   Temporal criterion passes cleanly.

### 2.3 Operational Immutability of Raw Storage
Harvesters store raw unparsed payloads directly to disk under:
`data/raw/phase2_candidates/{source_id}/{record_id}.{html|json}`
accompanied by a sidecar `<record_id>.meta.json` containing the source URL, UTC acquisition timestamp, harvester version, HTTP status, and payload SHA-256 hash.

**Immutability Guarantee:**
If `<record_id>.<ext>` already exists with a matching SHA-256 hash, re-download is skipped. If existing content differs, the harvester halts with a fatal `PayloadCollisionError`. Payloads are never silently modified or overwritten.

### 2.4 Decoupled Three-Tier Pipeline
The pipeline enforces strict separation of concerns:
1. **Harvester Tier (`experiments/phase2/harvesters/`):** Network-bound, polite crawl (1.0–1.5s pacing), zero outcome filtering, zero scientific selection. Emits raw files and logs operational network failures to `acquisition_errors.json`.
2. **Mapper Tier (`experiments/phase2/mappers/`):** Pure offline parser. Transforms raw payloads into `DemandCandidateContractRecord` with structured `PublicationDateEvidence`. Emits parsing/DOM failures to `mapping_errors.json`.
3. **Validator Tier (`backend/src/main/application/corpus/expansion_policy_validator.py`):** Pure offline, deterministic policy evaluator against `corpus_expansion_policy_v1.json`.

### 2.5 Formal Partition Invariants
The offline validation process guarantees mathematical disjunction and complete accounting:
$$\text{candidates\_mapped} = \text{candidates\_accepted} \cup \text{candidates\_rejected}$$
$$\text{candidates\_accepted} \cap \text{candidates\_rejected} = \emptyset$$

Every mapped candidate receives exactly one terminal policy disposition:
- `candidates_accepted.json`: 0 rejection reasons.
- `candidates_rejected.json`: $\ge 1$ typed rejection reasons from `CandidateRejectionReason` with verbatim evidence excerpts.

All output datasets are accompanied by cryptographically verifiable `.sha256` sidecars.

### 2.6 Acquisition Sufficiency vs Confirmatory Power Target
Milestone #101b establishes the eligible candidate pool (`candidates_accepted.json`). However, $N_{\mathrm{accepted}}$ does not equal $N_{\mathrm{power}}$. Milestone #101b satisfies its acquisition goal when the volume of accepted candidates provides an empirically plausible margin to achieve $N_{\mathrm{power}} = N_{\mathrm{eligible, independent}} \ge 60$ following the multidimensional independence audit in Milestone #102. If Milestone #102 demonstrates that $N_{\mathrm{power}} < 60$, expansion continues before benchmark freeze.

---

## 3. Non-Goals & Invariants

1. **No Evaluator/Matching Engine Changes:** PR #101b contains zero modifications to matching models, embedding tables, rankers, or runner scripts.
2. **No Fallback Date Inference:** No heuristic date estimation (e.g. subtracting an assumed 6 months from a deadline) is permitted. Missing publication date evidence evaluates strictly to `UNVERIFIABLE_PUBLICATION_DATE`.
3. **No Outcome-Dependent Selection:** No candidate is filtered, accepted, or excluded based on retrieved patents, semantic similarity scores, or perceived difficulty.

---

## 4. Consequences

### Positive
- Prevents temporal confounding by ensuring $t_{\mathrm{demand}}$ is grounded strictly in authentic primary publication evidence.
- Preserves epistemological accuracy: unverified dates are categorized as evidence insufficiency rather than false negative out-of-window claims.
- Decouples live web harvesting from 100% offline, deterministic policy validation and CI auditing.
- Preserves raw immutable payloads and cryptographic sidecars for complete external auditability.

### Negative
- Demands from platforms that do not expose authentic publication dates (e.g. InnoGet listings exposing only deadlines) cannot enter the eligible corpus $N_{\mathrm{power}}$ and are rejected with `UNVERIFIABLE_PUBLICATION_DATE`.
- Increases candidate harvesting volume requirements to offset date-unverifiable rejections.
