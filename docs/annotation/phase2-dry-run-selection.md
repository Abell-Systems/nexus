# PR-E Dry-Run Demand Selection — FINAL

**Status:** FINAL. All 8 proposed demands accepted as-is by Valentín + Lydia on 2026-09-08 — no substitutions. Frozen scientific artifact per `docs/superpowers/specs/2026-09-08-pr-e-dry-run-execution-design.md` §7 — see `phase2-dry-run-selection.manifest.json`/`phase2-dry-run-selection.sha256` for hash/provenance.

## Real-data correction to the spec's assumed criterion

Before selecting, checked `data/evaluation/dataset_phase2_demand_corpus_n39.json` directly: `target_cpc_prefixes` is `[]` (empty) for **all 39 demands**, not just some. The spec's §4 criterion "at least one or two demands where CPC concordance is likely to carry real signal (a well-populated `target_cpc_prefixes`)" can't be applied as written — that field is never populated in this corpus.

This doesn't block the criterion's intent, though: `DuckDbCPCRetriever` doesn't read `target_cpc_prefixes` at all — it derives CPC symbols from demand text via `extract_demand_cpc_auto()` → `map_concept_to_cpc()` (`application/landscape/cpc_taxonomy.py`) at retrieval time. So "CPC-informative" below is judged by whether a demand's title/description uses vocabulary a rule-based concept→CPC mapper could plausibly resolve (e.g. "arc welding," "electrolytic hydrogen production") — not by a corpus field.

**Scope update:** the execution-design spec's §6 resolved the semantic retriever as deferred (no open-corpus embedding pipeline exists yet — see that spec for the full finding). This dry-run's independent pool is `top-20 BM25 ∪ top-20 CPC` only. References to "semantic" divergence below are kept as historical rationale for why these demands are still lexically/conceptually interesting, but no `EligibilityReason`/pool outcome in the actual dry-run will involve a semantic score — the underlying BM25/CPC selection rationale stands unchanged.

## Corpus-wide observation relevant to selection

Not all 39 records are genuine technology-seeking demands amenable to a patent-candidate search. A meaningful fraction (e.g. `INNOGET-2293` "Kitchen sink: The centerpiece of your kitchen," `INNOGET-2299` "Redesign ENVIT's Website," `INNOGET-2300`/`2301` "Call for EU University students" innovation-challenge prompts, `INNOGET-2248` "Seeking patents for license" — a licensing meta-request, not a technology ask) read as marketing/consulting/student-challenge prompts rather than technology-transfer demands. These were excluded from consideration here — including one wouldn't stress-test the annotation protocol, it would just produce a near-empty or nonsensical candidate pool.

## Proposed 8 demands

| Demand ID | Source | Domain | Why (stress-test criteria) |
|---|---|---|---|
| `INNOGET-1625` | InnoGet | Fuel/refining chemistry | Technical vocabulary (desalination/dewatering of residual fuel oil) with real BM25/CPC signal expected. Wayback-confirmed upper bound (2023-09-28) — exercises the `ELIGIBLE`/`EXCLUDED_TEMPORAL` branches, not just `TEMPORAL_UNKNOWN`. |
| `INNOGET-1689` | InnoGet | Metallurgy/steel | Broad, lexically loose ask ("improve rebars and beams... material or manufacturing process") — good test of whether BM25 and CPC diverge on an underspecified query. Wayback-confirmed (2023-06-10). |
| `INNOGET-1870` | InnoGet | Manufacturing/arc welding | Clear, CPC-informative domain (arc welding maps cleanly to a narrow CPC region) — a positive control for CPC concordance actually carrying signal. No Wayback capture found — exercises `TEMPORAL_UNKNOWN` end-to-end. |
| `INNOGET-1932` | InnoGet | Materials/electronics | Specific technical constraint (LCD display materials surviving >85-95°C) — narrow enough to test precision, not just recall. Wayback-confirmed (2020-10-26). |
| `INNOGET-1935` | InnoGet | Environmental sensing | "Semiconductor sensing and miniaturization" — cross-domain vocabulary (sensing technology terms may not overlap with a given patent's surface terms even when conceptually related), useful for BM25-vs-CPC divergence even without a semantic retriever. Wayback-confirmed (2020-10-26). |
| `INNOGET-1972` | InnoGet | Biotech/cosmetic chemistry | Deliberately ambiguous term ("antioxidant extract from micro algae") — could map to food chemistry, pharma, or cosmetics CPC subclasses; a real test of the 1↔2/2↔3 boundary once the guide exists. Wayback-confirmed (2023-06-01). |
| `INNOGET-2258` | InnoGet | Energy/electrochemistry | Technical but broad ("advanced electrolytic processes," "hydrogen transport and storage") — plausible high-recall/low-precision case. Wayback-confirmed (2024-07-23). |
| `LOMBARDIA-947` | Open Innovation Lombardia | Environmental/mining engineering | Only non-InnoGet source with a clearly technical ask (PM10 dust monitoring/mitigation in open-pit/underground mining). Description is in Italian — a genuine stress test of whether BM25 (English-trained Spanish-patent corpus) still surfaces anything sensible. No Wayback check was run for Lombardia URLs (ADR 0019's check covered InnoGet only) — exercises `TEMPORAL_UNKNOWN`, and is an open item if Lombardia coverage matters later. |

## Coverage against §4 criteria

- **Technical diversity:** fuel chemistry, metallurgy, welding/manufacturing, materials/electronics, environmental sensing, biotech/cosmetics, energy/electrochemistry, mining/environmental — 8 distinct domains, no repeats.
- **Lexical ambiguity:** `INNOGET-1972` (extract/antioxidant), `INNOGET-1689` (broadly stated ask), `INNOGET-1935` (cross-domain sensing).
- **CPC-informative:** `INNOGET-1870` (welding) is the strongest positive control; `INNOGET-2258` (electrochemistry/hydrogen) and `INNOGET-1625` (refining) are plausible secondary cases.
- **Expected retriever divergence (BM25 vs. CPC only — semantic deferred, see scope update above):** `INNOGET-1935` and `INNOGET-2258` are the two most likely to show BM25 (surface terms) vs. CPC (taxonomic concept) disagreement.
- **Temporal branch coverage:** 6 of 8 have a Wayback-confirmed upper bound (exercises `ELIGIBLE`/`EXCLUDED_TEMPORAL`); `INNOGET-1870` and `LOMBARDIA-947` have none (exercises `TEMPORAL_UNKNOWN`).
- **Source diversity:** 7 InnoGet + 1 Lombardia (matches the corpus's own 37:2 ratio reasonably; a second Lombardia demand (`LOMBARDIA-860`, bridge-joint maintenance) was considered but not included, to keep the set at 8 and avoid over-indexing on a 2-item source).

## Finalization record

All 8 demands proposed above (`INNOGET-1625`, `INNOGET-1689`, `INNOGET-1870`, `INNOGET-1932`, `INNOGET-1935`, `INNOGET-1972`, `INNOGET-2258`, `LOMBARDIA-947`) were accepted as the final dry-run selection by Valentín + Lydia on 2026-09-08, with no substitutions and no change in count.
