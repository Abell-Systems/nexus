# TED construct-validity classifier -- pipeline built, awaiting human labeling

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
7. `run_ted_construct_validity_llm_classification.py` -- attempted to run (see
   'Current state' below) -- blocked on missing `GROQ_API_KEY` credentials in
   this environment, no LLM classifications were produced.
8. `evaluate_ted_construct_validity_gate.py` -- built and confirmed to correctly
   BLOCK against incomplete human labels (the current state).

## Current state

No human labeling has occurred yet. `data/annotations/ted_construct_validity_labeling_valentin.csv`
and `_lydia.csv` are blank templates. The gate-check script (`evaluate_ted_construct_validity_gate.py`)
correctly refuses to run against them. `data/annotations/ted_construct_validity_llm_classification.json`
also does not exist yet -- Task 7's LLM run was blocked by a missing `GROQ_API_KEY` credential
in this environment (script committed and ready at
`experiments/phase2/run_ted_construct_validity_llm_classification.py`, not yet executed).

## Next step (not done here)

1. Valentín and Lydia independently label the 30-row control-sample CSVs, blind to
   each other and to any LLM output, per the class definitions in spec SS3.
2. Adjudicate any disagreements the same way as the 108-pair gold set, writing
   `data/annotations/ted_construct_validity_adjudication.json`.
3. Run `evaluate_ted_construct_validity_gate.py` for real -- it will report PASS
   or FAIL per the pre-registered thresholds (spec SS8).
4. Only then: a follow-up implementation plan wires the actual fix into
   `ted_mapper.py` (full-114 LLM classification on PASS, full-114 manual
   classification on FAIL), re-runs the affected eligibility measurement, and
   corrects ADR 0034's now-false claim -- explicitly out of scope for this plan
   (spec SS9, plan Global Constraints).
