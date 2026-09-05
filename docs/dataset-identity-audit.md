# Dataset Identity & Temporal Audit — PR #43

**Status:** audit record (not a protocol change, not a dataset change).
**Date:** 2026-09-05
**Script:** `scripts/audit_dataset_identity.py` (stdlib only, read-only).
**Scope:** make the pilot inputs scientifically auditable. No metric, weight, label,
threshold, embedding, transform, or pool-construction change in this PR.

---

## 1. Canonical pair (the single truth)

The sealed evaluation corpus is exactly one triple:

| Artifact | SHA-256 |
|---|---|
| `data/evaluation/dataset_pilot_benchmark.json` | `bf7c501f817f9d6e3f87574f61c003670b008910d76b1d17632ff21451195453` |
| sidecar `.sha256` | same digest, `dataset_pilot_benchmark.json` filename |
| `dataset_pilot_benchmark.manifest.json` → `content_sha256` | same digest; counts `(3, 15, 23)` verified against content |
| `embeddings_pilot_benchmark.json` → `dataset_sha256` | same digest; demand/patent id sets equal to the dataset's; dim 768 |

`EvaluationRunReport.dataset_sha256`, the M1 `dataset_sha256`, and this SHA are the
same string. Any future dataset version gets a new id, a new SHA, and a new artifact —
never an in-place edit (ADR 0006, ADR 0012, ADR 0014).

## 2. Resolved discrepancies

### 2.1 Raw SHA cited in `data_provenance.md` was stale
`docs/data_provenance.md` cited raw baseline `68500f25…` in two places. The file on
disk (`data/raw/oepm_open_data_es.json`) hashes to `2832dc59…`, which is also what
`data/snapshots/patents_es_manifest.json` records as `raw_source_sha256`. The document
was corrected to the observed value in this PR; no data file changed.

### 2.2 16 vs 15 records
`data/snapshots/patents_es_corpus.jsonl` holds **16** records (proof-of-method baseline
for the white-space pipeline, manifest `total_records: 16` — verified). The sealed
evaluation corpus holds **15** of them. The single snapshot-only record is
`ES-2918450-A1` (distributed energy-demand control platform, pub 2024-02-10): it has
no annotations and never entered the benchmark. Direction verified: every evaluation
id exists in the snapshots file; the reverse is not claimed and not required.

### 2.3 Demand ids: pool narrative vs sealed set
`docs/data_provenance.md` §2 narrates four illustrative solicitations (calls 2292,
2293, 2297, 2245) from the Spanish demand pool. The sealed benchmark contains three
calls with frozen posted dates: `INNOGET-2415` (2023-01-10), `INNOGET-2292`
(2023-02-15), `INNOGET-2501` (2023-03-20). These are different statements (pool
illustration vs sealed input), not a contradiction once labelled as such — which this
record does. Phase-2 pool construction must cite this section, not the narrative.

### 2.4 Temporal violations (known, flagged, untouched)
Strict prior-art rule (`t_pub < t_demand`, protocol §5.3): **3 of 23** annotated pairs
violate it. No equal-date pairs exist, so the strict and lenient readings agree.

| demand_id | publication_id | grade | t_pub | t_demand |
|---|---|---|---|---|
| INNOGET-2415 | ES-2901234-A1 | 2 | 2023-04-20 | 2023-01-10 |
| INNOGET-2501 | ES-2901234-A1 | 0 | 2023-04-20 | 2023-03-20 |
| INNOGET-2292 | ES-2856789-A1 | 0 | 2023-03-25 | 2023-02-15 |

Rule (binding from this PR): sealed data is immutable — pairs are flagged
`TEMPORAL_VIOLATION` in the audit report, never silently pruned. At evaluation time
the engine already treats them as ineligible (`overall 0.0`, `INELIGIBLE_TEMPORAL`).
Excluding such pairs at pool-construction time is Phase-2 work (PR-F track), where it
will happen before sealing, not after.

## 3. Audit verdict on current data

14 of 15 checks PASS; `temporal_eligibility` FAILs with the 3 pairs above.
Overall verdict: **FAIL** — which is the honest, committable state. The claim this PR
defends is exactly: *"we know what dataset is evaluated, its SHA, which embeddings
belong to it, and which observations violate the temporal restriction"* — and nothing more.

## 4. Explicitly not in this PR

Weights, thresholds, BM25, embeddings, ADR 0016 transform, metrics, labels, M0/M1
comparison, ADK, product code. The audit script exits 0 and reports; it does not gate.
Promoting the verdict to a CI gate happens only after the violations are remediated in
a new, separately sealed dataset version.
