# Scientific Model — Nexus

**Status:** conceptual, non-normative. Does not supersede any ADR, `roadmap.md`, or
`empirical-study-protocol.md` — it is the map that tells you *which* of those to open.
**Purpose:** let a scientific decision be understood without knowing the conversation
that produced it. If growing the number of ADRs/experiments/protocols means the project's
working memory has to live in two people's heads, this page is the external memory.

---

## 1. The question chain

```text
Scientific question
        │
        ▼
What technological demand exists?             → DEMAND
        │
        ▼
What technologies could respond to it?         → TECHNOLOGY
        │
        ▼
How well do we retrieve/match them?            → EVIDENCE
        │
        ▼
How do we avoid bias in that judgment?         → EVALUATION
        │
        ▼
What can we actually claim?                    → CLAIM
```

Five concepts, nothing else:

**DEMAND → TECHNOLOGY → EVIDENCE → EVALUATION → CLAIM**

Every ADR, experiment, and protocol document in `docs/` is a mechanism for making one
arrow in that chain valid. If a piece of work can't be placed on this chain, it isn't
part of the scientific model yet — see §4.

## 2. The evidence gradient

Nothing above the `EVIDENCE` step is allowed to skip levels. Four levels, strictly ordered:

| Level | Meaning | Example |
|---|---|---|
| **Observation** | Raw fact, directly sourced | "Company X holds patent families A, B, C." |
| **Derivation** | Deterministic transform, no judgment | "A, B, C share CPC class H01M." |
| **Inference** | Model/LLM judgment over derived facts | "A, B, C appear to address problem P." |
| **Claim** | Inference that has passed `EVALUATION` | Only stated after evaluation, never before. |

This gradient already operates in Nexus (Head A "discovery" vs. Head B
"verification" per ADR 0017 §2.3/§5.8; `FieldObservation` provenance per
`docs/SCIENTIFIC_RESULTS_CONTRACT.md` §5). Any future capability — competitor-aware
landscape included — inherits this gradient rather than reinventing it.

## 3. Per-experiment header

Every experiment/protocol doc should carry these six lines at the top. If more detail
is needed, the reader descends into the linked ADR — this header is not a replacement
for the ADR, it's the index entry for it.

```text
QUESTION:
INPUT:
METHOD:
OUTPUT:
VALIDITY:
STATUS:
```

Worked example, #104:

```text
QUESTION:  Can Nexus retrieve technologies relevant to TED demands?
INPUT:     65 independent demands + eligible patent corpus.
METHOD:    Candidate generation + ranking + blind evaluation.
OUTPUT:    Retrieval/ranking metrics.
VALIDITY:  Temporality + independence + family-awareness + eligible denominators.
STATUS:    BLOCKED — patent corpus not yet qualified at scale (see the OEPM
           production-scale patent corpus contract, `feat/pr101b-corpus-expansion-acquisition`).
```

## 4. The admission rule

> **If a Nexus capability cannot be placed on the DEMAND → TECHNOLOGY → EVIDENCE →
> EVALUATION → CLAIM chain, it is not yet ready to become part of the architecture.**

Corollary for the competitor-aware landscape idea specifically: no ADR for it is
written until (a) the current empirical bottleneck (#104, patent corpus
qualification) is resolved, and (b) the actual competitive structure of the real
corpus has been observed — not designed speculatively. Until then it stays a roadmap
note, tracked in `[[project_nexus_oepm_corpus_state]]` (agent memory) and this file's
§5, not an ADR.

## 5. Current position in the chain (2026-09-15)

```text
DEMAND        — sourced (TED/CORDIS), independence/eligibility audited
                (pending merge from `feat/pr101b-corpus-expansion-acquisition`)
TECHNOLOGY    — OEPM corpus §11.3 ingestion PASS; scale (N≥60) NOT YET DETERMINED
EVIDENCE      — blocked upstream of TECHNOLOGY: #104 dual annotation cannot start
                until corpus qualification resolves
EVALUATION    — protocol frozen, waiting on EVIDENCE
CLAIM         — none yet; nothing above should be read as a result
```

Deferred, not designed: competitor-aware landscape (`organization → family →
technology → problem`) — see §4. Revisit only after `TECHNOLOGY`/`EVIDENCE` above
are unblocked.
