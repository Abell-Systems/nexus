# Synthetic demand corpus

`data/` holds an **invented** corpus with the schema of the original N=39 demand corpus, produced by
`generate_synthetic_corpus.py` (deterministic). Records are marked `synthetic_control`, source `synthetic`.

* It lets the software and the generic conformance check run without third-party text:
  `WPI_DATA_DIR=experiments/wpi-demand-patent-matching/synthetic/data python experiments/wpi-demand-patent-matching/checks/check_demand_corpus.py`
* It is **not** the study's data. Nothing computed on it reproduces, supports or replaces a result of the original
  study, and it must not be reported as such.
* The other `checks/check_*.py` and `generate_*.py` verify the **original** study: they assert its identities
  (organisation names, demand ids, counts, frozen hashes). They need the restricted original corpus and stop with a
  message when it is absent. They are not expected to pass on this set.

Three levels of reproducibility, kept apart: (1) the code runs (synthetic set); (2) the recorded identity of the
original files (`../data/RETIRED_FILES.json`, hashes not recomputed); (3) the original study, which requires the
restricted original corpus and a documented basis to hold it.
