# TED construct-eligibility classifier: validated fix design

Status: design frozen, pending implementation.
Fixes: the `has_articulated_technical_problem` tautology in
`backend/src/main/application/corpus/mappers/ted_mapper.py:94`
(`bool(description.strip())`, which can never be `False` because an empty
description already raises `MappingError` earlier in the same function).
Corrects ADR 0034's claim that the generic `NO_TECHNICAL_PROBLEM` policy
criterion does real eligibility filtering for TED — it currently cannot fire
at all; only the 25-word `min_word_count` gate filters TED intake.

## 1. Background

Found by independent code review of PR #112 (2026-09-23; see project memory
`project_nexus_pr112_113_construct_validity_blocker`). ADR 0033's own
qualification spike had already flagged the TED Innovation Partnership
population as not construct-uniform (one sampled notice, `452177-2026`
AENA, had no real technical-problem narrative) and explicitly deferred
resolving it until "a real sample is run through
`has_articulated_technical_problem`-equivalent criteria." That sample then
ran through a criterion that structurally cannot reject anything.

Practical consequence: `N_power=65` (frozen in project memory as "PASS")
currently means "≥25-word description," not "articulated technical
problem," and is provisional until this is fixed and the affected
measurement is re-run.

TED has no dedicated "technical problem" field distinct from its one
narrative field (`BT-24-Procedure`, "Description") — unlike EEN/POD, whose
mapper detects a *structurally distinct* technical-problem section/heading
and only falls back to the Abstract for two specific constructs
(`_CONSTRUCTS_WITH_TECHNICAL_ABSTRACT = {"Technology request", "R&D
request"}`, validated in commit `ec4b1c0` against a 10/10 + 10/10 positive
sample vs. a 5/5 Business-offer negative control). TED's fix cannot reuse
that structural approach — it requires classifying the *content* of the one
available field.

## 2. Decision: LLM classifier, gated by a validated acceptance test

Per explicit user decision, this is not a regex/keyword heuristic (this
project already hit exactly that failure mode once — the CPC channel
diagnostic's exact-phrase matcher failed against procurement prose due to a
vocabulary-register gap, a directly analogous risk here across TED's ~10
languages). It is also not "LLM classifies 114 and we trust it" — the LLM
classifier must first pass a human-validated acceptance gate before it is
allowed to touch the real eligibility decision for any candidate.

## 3. Operative class definitions (frozen before any labeling)

- **`TECHNICAL_PROBLEM`** — the description articulates a specific
  technical, scientific, or engineering challenge, need, or capability gap
  that a solution is being sought for: it describes what is technically
  difficult or unsolved.
- **`GENERIC_PROCUREMENT`** — the description specifies a scope of work,
  deliverable, standard/certification to follow, quantity, or
  administrative/contractual term, without articulating an underlying
  technical problem: it reads as "what to buy/deliver," not "what technical
  difficulty needs solving." (This is the AENA failure mode.)
- **`EMPTY_INSUFFICIENT`** — the description is empty, near-empty, or so
  minimal/boilerplate that no meaningful judgment can be made either way.
  Distinct from `GENERIC_PROCUREMENT`, which has real content, just not a
  technical problem.

These three definitions are frozen text, given verbatim to every human
annotator and embedded verbatim in the LLM classifier's prompt — neither
side gets a different wording of the task.

## 4. Population and boundary stratum

- **Population:** all 114 TED candidates that successfully mapped under
  `TedCandidateMapper` (`data/experiments/phase2_v4/candidates_mapped.json`,
  72 currently accepted + 42 currently rejected under the broken criterion).
- **Boundary stratum:** every candidate with
  `|canonical_word_count(description) - min_word_count| <= 10`, i.e.
  approximately 15-35 words given the policy's current `min_word_count=25`.
  Defined by this formula alone, frozen before inspecting any text — not a
  window chosen after looking at which cases are hard. This stratum is
  included **in full**, not sampled: it is a directed probe of the zone
  where the known failure (AENA) lives, not a convenience sample.

## 5. Control sample composition

- **All** boundary-stratum candidates. The exact count is a computed fact
  of the live 114-candidate population, not a design parameter — the
  implementation must compute it from SS4's formula and report it, not
  guess or round it. Expected small, given `min_word_count` already gates
  most short-content candidates out.
- **Fill to n=30 total**, stratified by (accepted/rejected under the
  current broken policy) x (language), drawn from the non-boundary
  remainder.
- n=30 is explicitly **an acceptance gate for allowing automated
  classification, not a powered estimate of population-level classifier
  sensitivity or specificity.** This sentence is carried verbatim into the
  results doc this design produces — the design must not be sold as a
  statistically powered performance claim it cannot support at this sample
  size.

## 6. Labeling protocol

1. Valentín and Lydia independently label all n=30 control-sample
   candidates into the three classes (SS3), blind to each other and to any
   LLM output.
2. **Human-human agreement is checked first.** If the two annotators
   disagree substantially, the class definitions (SS3) are not sharp enough
   yet — that gets fixed and re-labeled before any LLM comparison, not
   patched around.
3. Disagreements are adjudicated under the same discipline as the 108-pair
   gold set (same contract, no criterion change, divergent adjudications
   flagged explicitly rather than silently smoothed). The adjudicated
   consensus becomes the reference label for each of the n=30.
4. The LLM classifier (SS7) then classifies the same n=30, blind to every
   human label, deterministic settings.

## 7. LLM classifier

- Uses the repo's existing `infrastructure/llm` provider stack (no new
  provider/dependency).
- **Deterministic**: temperature=0, fixed model/version pinned in the
  implementation plan the way ADR 0014 pins its embedding model.
- Prompt carries SS3's three definitions verbatim and nothing else framing
  the task (no examples that could leak the boundary-stratum construction
  logic into the prompt).
- Classifies from `description_text` alone — the same field the mapper
  already extracts, no new data source.

## 8. Validation criteria (two separate gates, not conflated)

**Gate A — statistical criterion (an acceptance threshold, not a
population-level performance estimate, per SS5):**
- Recall for `TECHNICAL_PROBLEM` >= 90% (real problems must not be
  misclassified as generic — an over-rejection risk).
- Specificity against `GENERIC_PROCUREMENT` >= 90% (correctly identifying
  generic text as generic — this is the actual bug's failure mode).

**Gate B — construct-validity safety gate (zero tolerance, operational
acceptance criterion, not a claim about the population false-positive
rate):**
- Zero `GENERIC_PROCUREMENT -> TECHNICAL_PROBLEM` misclassifications within
  the boundary-stratum subset specifically. Any single miss here fails
  validation outright, regardless of the aggregate Gate A numbers.

**Decision rule:**
- **Both gates pass** -> the LLM classifier is applied to the full 114
  (control-sample LLM outputs are reused, not recomputed).
- **Either gate fails** -> escalate to full manual classification of all
  114 by Valentín and Lydia (same blind-dual + adjudication discipline as
  SS6), no LLM in the eligibility path for this source.
- **No tuning after seeing results**: if Gate A or B fails, the response is
  escalation to manual classification, never adjusting the prompt,
  thresholds, or class definitions and re-testing against the same n=30
  (that would be validating against data already used to tune the
  classifier). A revised classifier would need a fresh control sample.

## 9. What happens after classification (either path)

1. `TedCandidateMapper.map_payload` is changed to call the classifier (or,
   on the manual-fallback path, read frozen manual labels) instead of the
   current tautological `bool(description.strip())`, producing a real
   three-way distinction collapsed to the existing boolean
   `has_articulated_technical_problem` field (`True` only for
   `TECHNICAL_PROBLEM`) plus the classification result disclosed alongside
   it for auditability.
2. `expansion_policy_validator.py`'s existing `NO_TECHNICAL_PROBLEM` check
   (SS6 in that file) requires no code change — it already reads
   `has_articulated_technical_problem` correctly; the bug was entirely in
   what fed that flag.
3. The full acquisition/eligibility measurement is re-run against the
   corrected mapper. The resulting `N_power` may differ from 65 — this is
   expected and correct, not a regression, and must be reported as the new
   frozen number with an explicit note that it supersedes the prior
   (invalid) 65.
4. `ADR 0034` is corrected: its current claim that the generic
   `NO_TECHNICAL_PROBLEM` criterion "does the actual eligibility filtering"
   for TED is factually wrong as written and must be corrected to describe
   the new classifier, with a dated amendment note (same discipline as the
   temporal-window and construct-expansion amendments already in this
   project's history) rather than silently rewriting the ADR's history.

## 10. Disclosed limitations

- The n=30 control sample validates the classifier as an **acceptance
  gate**, not as a powered estimate of population sensitivity/specificity —
  stated explicitly in SS5 and repeated in the results doc this design
  produces, so it cannot be quoted out of context as a precision claim.
- The boundary-stratum definition (`|words - 25| <= 10`) is itself a
  judgment call, fixed before inspection specifically to avoid look-then-
  choose bias, but it is one reasonable window among others; it is
  disclosed as the frozen rule, not defended as the only possible one.
- If Gate A/B fails and manual classification is used instead, the
  resulting labels are still a single-pass human judgment (dual + adjudicated,
  same as the gold set) — not immune to the same "modular is a partial
  false cognate" class of contract ambiguity already seen once in this
  project's annotation history; any such ambiguity found during labeling
  must be disclosed the same way, not smoothed over.
