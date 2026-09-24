# TED construct-validity classifier -- LLM run complete, awaiting human labeling

Spec: docs/superpowers/specs/2026-09-23-ted-construct-validity-classifier-design.md
Plan: docs/superpowers/plans/2026-09-23-ted-construct-validity-classifier.md

## What was built

1. `TechnicalProblemClassification` domain enum + `TechnicalProblemClassifierProtocol`
   (backend/src/main/domain/).
2. `boundary_stratum.py` -- pure boundary-formula and stratified control-sample
   construction (backend/src/main/application/corpus/).
3. `LlmTechnicalProblemClassifier` -- deterministic (temperature=0) LLM classifier
   implementing the protocol (backend/src/main/infrastructure/llm/).
4. `validation_gate.py` -- the two-gate (statistical + boundary safety) decision
   rule (backend/src/main/application/corpus/).
5. `build_ted_construct_validity_control_sample.py` -- generated the real control
   sample manifest against the live 114-candidate population.
6. `export_ted_construct_validity_labeling_csv.py` -- exported three blank CSVs
   (template/valentin/lydia), 30 rows each.
7. `run_ted_construct_validity_llm_classification.py` -- run for real on
   2026-09-24 once `GROQ_API_KEY` became available (see 'Current state' below).
8. `evaluate_ted_construct_validity_gate.py` -- built and confirmed to correctly
   BLOCK against incomplete human labels (still the current state -- see below).

## Model pin correction (2026-09-24)

The originally-pinned model, `llama-3.3-70b-versatile`, was retired from Groq's
catalog between this branch's implementation and its first real run (confirmed
via `/v1/models`: 404 `model_not_found`). Re-pinned to `openai/gpt-oss-120b`
(closest available model in size/generality), verified manually against the
classifier's exact JSON-object/temperature=0 request shape before use. This is
a provenance correction, not a silent tuning change -- the class definitions,
thresholds, and decision rule are untouched.

## Current state

**LLM classification (Task 7): done.** `run_ted_construct_validity_llm_classification.py`
ran for real against all 30 control-sample candidates using `openai/gpt-oss-120b`,
sha256-verified against the manifest it read, producing
`data/annotations/ted_construct_validity_llm_classification.json` (+ sha256 sidecar).
Distribution: 21 `generic_procurement`, 6 `technical_problem`, 3 `empty_insufficient`.
This is the LLM's own classification of the 30 cases, produced blind to any human
label -- not yet compared against anything, since no human reference exists yet.

**Human labeling (Task 6 collection): still blank.** `data/annotations/ted_construct_validity_labeling_valentin.csv`
and `_lydia.csv` are still blank templates. The gate-check script
(`evaluate_ted_construct_validity_gate.py`) correctly refuses to run against them --
this is unchanged from the original stopping point and remains the actual blocker.

## Next step (not done here)

1. Valentín and Lydia independently label the 30-row control-sample CSVs, blind to
   each other and to any LLM output (already produced, but not to be looked at
   before labeling), per the class definitions in spec SS3.
2. Adjudicate any disagreements the same way as the 108-pair gold set, writing
   `data/annotations/ted_construct_validity_adjudication.json`.
3. Run `evaluate_ted_construct_validity_gate.py` for real -- it will report PASS
   or FAIL per the pre-registered thresholds (spec SS8), scored against the LLM
   classifications already on disk.
4. Only then: a follow-up implementation plan wires the actual fix into
   `ted_mapper.py` (full-114 LLM classification on PASS, full-114 manual
   classification on FAIL), re-runs the affected eligibility measurement, and
   corrects ADR 0034's now-false claim -- explicitly out of scope for this plan
   (spec SS9, plan Global Constraints).
