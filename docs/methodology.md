# Methodology — Patent Innovation Agent

*Formal specification of the method, intended as the methodological basis for a
scientific publication. Mirrors the code in `backend/patent_agent/` as implemented
(August 2026). Spanish version: [metodologia.md](metodologia.md).*

---

## 1. Overview

We propose a multi-agent system for the automated identification and validation of
invention opportunities (*white space*) in patent landscapes. The system combines
(i) deterministic patent-data mining, (ii) taxonomic segmentation of the landscape
with a composite opportunity metric, and (iii) a generative-adversarial loop based
on large language models (LLMs) whose output is subject to an architectural
traceability requirement: every claim must be accompanied by verifiable citations
to specific patent documents.

Evaluation domain: **solid-state electrolytes for EV batteries** (fixed throughout
the study).

## 2. Data sources

| Source | Content | Role |
|---|---|---|
| Google Patents Public Datasets (BigQuery) | Patent publications: publication number, title, abstract, assignee, inventors, dates, CPC codes, citation count | Supply signal: what already exists |
| SBIR/STTR (US) and CORDIS (EU) | Open technology-need solicitations | Demand signal: what is needed |

The system defines two data contracts (`PatentRecord`, `DemandSignal` in
`tools/schemas.py`) and an abstraction layer that allows swapping the real source
for controlled mock data (`USE_MOCK_BIGQUERY=true`), guaranteeing reproducibility
of experiments without dependence on external credentials.

## 3. Technology-landscape segmentation

Patents retrieved for the domain are grouped by their **primary CPC prefix** (the
first 4 characters of each document's first CPC code). Each group constitutes a
technology cluster. This taxonomic segmentation is deliberately transparent and
auditable; future replacement with semantic-embedding-based clustering is planned
with no change to the output contracts.

Each cluster publishes its three representative patents, selected by highest
citation count.

## 4. Composite white-space metric

For each cluster $i$ with $n_i$ patents, let $n_{max} = \max_j n_j$. Four signals
normalized to $[0, 1]$ are defined:

**Relative density** (saturation):
$$d_i = \frac{n_i}{n_{max}}$$

**Recency** — mean filing age against a 20-year horizon:
$$r_i = \mathrm{clip}\left(1 - \frac{\bar{a}_i}{20},\ 0,\ 1\right), \quad \bar{a}_i = \frac{1}{n_i}\sum_k \max(1,\ y_{today} - y_{filing,k})$$

**Citation velocity** — citations per year since filing (active research interest):
$$v_i = \mathrm{clip}\left(\frac{1}{n_i}\sum_k \frac{c_k}{a_k},\ 0,\ 1\right) \text{ with } /10 \text{ scaling}$$

**Demand** — open technology needs whose CPC prefix matches the cluster:
$$q_i = \begin{cases} m_i / m_{max} & \text{if any signal exists} \\ 0 & \text{otherwise}\end{cases}$$

The white-space score is the weighted linear combination:

$$W_i = 0.4\,(1 - d_i) + 0.2\, r_i + 0.15\, v_i + 0.25\, q_i$$

A cluster is declared white space if $W_i \geq 0.5$ (default threshold).
Clusters are ranked by descending $W_i$.

*Weight justification:* low density dominates (0.40) because saturation is the
primary obstacle to patentability; demand (0.25) prevents classifying an area as
an opportunity simply because nobody wants it; recency (0.20) and citation
velocity (0.15) filter out abandoned areas. The weighting is a declared parameter
of the method and amenable to sensitivity analysis.

## 5. Generative protocol (inventor agent)

Over each white-space cluster, an LLM agent (Gemini, via Google ADK) generates
invention candidates. Each candidate is constrained by structured schema
(`InventionCandidate`) to five fields: identifier, originating cluster, title,
description, and **claimed novelty** — the specific hypothesis that will be
subjected to refutation.

## 6. Adversarial protocol (adversarial agent)

A second LLM agent evaluates each candidate against available prior art. Its
output is schema-constrained (`AdversarialVerdict`) to:

- `verdict` ∈ {`survives`, `rejected`}
- `rationale` (text)
- `cited_patents`: **mandatory non-empty list** of publication numbers

The `min_length=1` constraint on `cited_patents` is structural (validated at
runtime by the schema): the system **rejects by construction** any verdict
lacking cited prior art. This is the method's central traceability mechanism: it
turns documentary citation of an AI judgment from a recommendation into a
validity requirement.

The inventor and adversarial agents operate in a loop (propose → critique →
propose again) until a candidate survives scrutiny or the configured maximum
number of iterations ($k_{max}$, quota-limited by default) is reached.

## 7. Final scoring (governor agent)

Surviving candidates receive a score card (`ScoreCard`) with four dimensions in
$[0,1]$: novelty, prior-art risk, differentiation, and evidence. As in §6, the
`supporting_evidence` field has minimum cardinality 1: every score must cite
publication numbers traceable to earlier pipeline stages.

## 8. End-to-end chain of evidence custody

The method guarantees end-to-end traceability:

```
PatentRecord.publication_number  (mining)
   → PatentCluster.representative_patents  (segmentation)
   → AdversarialVerdict.cited_patents  (refutation)
   → ScoreCard.supporting_evidence  (scoring)
```

Every citation number at any stage can be traced back to the original patent
document. No link in the chain accepts unverified free text as justification.

## 9. Limitations and threats to validity

1. **Taxonomic segmentation**: CPC-prefix grouping inherits CPC classification
   biases (an invention may cross classes); cluster granularity depends on the
   retrieval query.
2. **Metric weights**: the §4 coefficients are a defensible parametric choice but
   not empirically estimated; they invite calibration against grant-outcome data.
3. **LLM non-determinism**: the generative stages (§5–7) are stochastic;
   reproducibility requires fixing temperature/seed and reporting cross-run
   variability.
4. **Residual hallucination**: the schema guarantees citations *exist* as fields,
   but verifying that a citation *actually supports* the verdict requires
   additional human or automated checking (open work stream).
5. **Mock data**: part of the validation runs against controlled mock sources;
   results with real BigQuery data require GCP credentials.
6. **Inference quota**: the free API tier (20 requests/day per model) restricts
   the number of adversarial-loop iterations per run.

## 10. Reproducibility

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env          # USE_MOCK_BIGQUERY=true by default
pytest                            # unit test suite
uvicorn main:app --port 8080     # deterministic pipeline via GET /api/landscape
```

Declared parameters of the method: white-space threshold (0.5), recency horizon
(20 years), citation-velocity scale (10 citations/year), §4 weights, maximum loop
iterations (`INVENTION_LOOP_MAX_ITERATIONS`), Gemini model (`GEMINI_MODEL`).
