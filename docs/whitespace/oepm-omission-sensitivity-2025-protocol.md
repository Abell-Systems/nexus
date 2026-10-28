# Protocol: descriptive sensitivity of the 2025 unobserved pairs (fixed before any result)

**Status:** Protocol, written and committed **before** the analysis is run. It reports no result. It is exploratory and descriptive; it decides nothing about D4, E5 or E7 and exposes no candidate. Any change after the first execution must be recorded as an amendment with its date, never as a silent edit.
**Date:** 2026-10-28
**Context:** the article outline ([descriptive-article-outline.md](descriptive-article-outline.md) §2.4) cannot claim sensitivity of the 2025 counts, because [oepm-omission-sensitivity.md](oepm-omission-sensitivity.md) covers only the origins 2003 and 2006.

## 1. Fixed inputs

| Item | Value |
|---|---|
| Corpus | `BIBLIO_2000…2025` (2010 absent), 711,547 records; SHA-256 of each file as in `oepm-unobserved-pairs-results.json`, `corpus.files` |
| Base result | `oepm-unobserved-pairs-results.json`, SHA-256 `6a269125d4d92725d74a875f1264553bacb798dac0b1ef7061508027fb3482f7` |
| Unit | O4: the publication identifier, with the union of the subclasses of its earliest date |
| Origin | 2025 (documents published in or before 2025) |
| Activity threshold (base) | 20 O4 identifiers, cumulative to the origin |
| E | Σ_y n_i(y)·n_j(y)/N(y), years with documents only; 2010 skipped and never counted as zero; `E_min = 1` |
| Pair | Unordered pair of active subclasses; *unobserved* if no single source record published up to 2025 carries both |

## 2. Scenarios

| Id | Intervention | Reps |
|---|---|---|
| S-A | None. **Stop rule:** if it does not give 621 active subclasses, 192,510 pairs and 149,048 unobserved pairs, stop, diagnose, and run nothing else. | 1 |
| S-B1 | Remove every document of one publication year, one year at a time. Eligible years: every year 2000–2025 with documents (25 years). 2010 is not eligible: it is already a gap, not a year with data. | 25 |
| S-C | Remove 10 % of the O4 identifiers, **stratified by publication year** (each year loses round(0.10 · n_y), ties of rounding by floor). Seeds fixed now: **20261101, 20261102, 20261103, 20261104, 20261105** (Python `random.Random(seed)`). | 5 |
| S-D | Same corpus, activity threshold 10 and 40 (base 20 is S-A). All other rules unchanged. | 2 |

In S-B1 and S-C, N(y) and n_i(y) are recomputed on the reduced corpus; a removed year has no term in E (it is skipped like 2010), so S-B1 also changes the temporal history used for E. This is stated, not corrected.

## 3. Statistics

Let U_A be the set of unobserved pairs of S-A (149,048) and U_s that of scenario *s*. All statistics are aggregate.

1. **Active subclasses and unobserved pairs of *s*:** counts.
2. **Loss of unobservedness (S-B1, S-C):** `|U_A \ U_s| / |U_A|`, over pairs of U_A whose two subclasses are still active in *s*. Pairs whose subclass falls below the threshold are counted apart as `dropped`, and the denominator is stated for both.
3. **S-D:** the comparison universe is the pairs whose two subclasses are active in **both** S-A and the S-D configuration. Reported separately: (a) pairs of U_A leaving the universe because a subclass is no longer active (threshold 40), (b) pairs entering because new subclasses become active (threshold 10), (c) within the common universe, change of observed status and rank change of E.
4. **Rank correlation of E:** Spearman ρ between E in S-A and E in *s*, computed over the pairs in U_A ∩ U_s (unobserved in both). Ties receive average ranks. Pairs absent from either side are excluded, and their number is reported. E is taken with 9 decimals as stored.
5. **S-C:** the five replicates are reported individually and summarised by min, median and max. They are five draws of one artificial mechanism, not five independent observations of the real world, and no confidence interval is computed from them.
6. **S-B1:** reported per year and as min/median/max across years.

## 4. Output

Aggregate tables only, as `oepm-omission-sensitivity-2025-results.json` and `oepm-omission-sensitivity-2025.md`. **No list of pairs and no identifiers**, in any file or log. Each result records the configuration, the seeds and the SHA-256 of the inputs. Invariants checked at run time: S-A counts above; |U_s| ≥ 0; a pair in U_s is a pair between active subclasses of *s*; the same seed gives the same output byte for byte.

## 5. Interpretation limits (stated in the report)

- The removal is artificial. It does **not** estimate the effect of the real omitted publications, whose classification is unavailable.
- Removing a year also changes the temporal history from which E is computed.
- The alternative thresholds measure sensitivity to a design decision. They do not identify the correct threshold.
- Nothing here is evidence of technological opportunity, novelty, patentability or freedom to operate.

## 6. Order of work

1. This protocol is reviewed and committed. 2. Only then the analysis is run. 3. The report states every deviation from this document.
