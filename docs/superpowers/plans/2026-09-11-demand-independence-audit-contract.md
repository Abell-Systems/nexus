# Demand Independence Audit Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the roadmap's "demand independence audit" gap (`docs/roadmap.md` line 141, quoted below) with the one axis of non-independence the frozen corpus actually has accept-only, unambiguous evidence for today: shared `requesting_organization` identity. Produces a new, frozen `dataset_phase2_independent_corpus_v1.json` — the first artifact in this codebase to distinguish "eligible demand" (N=24, existing) from "independent demand" (a strict subset, derived here) — via the exact same contract → test → code, accept-only-never-inferred, generate/check script discipline this codebase already established for construct eligibility (#84–#86) and the eligible corpus (#88).

**Architecture:** A demand's `requesting_organization` was already extracted at acquisition time (`domain/models/demand.py`'s `RawExtractedDemandFields.organization_raw` / `DemandRecord.requesting_organization`) and survives today only in an audit sidecar (`experiments/wpi-demand-patent-matching/data/dataset_phase2_demand_corpus_n39.origin_audit.json`) — never inferred from title/description text. This plan adds a new, generic, reusable domain model (`DemandOrganizationObservation`, `DemandIndependenceGroupEntry`, `DemandIndependenceStatus` in `domain/models/annotation.py`, alongside the existing `ConstructEligibilityRubric` pattern) and a pure grouping function (`application/annotation/demand_independence.py`'s `derive_independence_groups`) that groups demands sharing an **exact-match**, non-excluded `requesting_organization` string, marking exactly one deterministic representative per group `INDEPENDENT` and the rest `PSEUDOREPLICATE`. Unlike `family_policy` (ADR 0027), this is **not** a runtime `EvaluationExecutionContext` toggle — independence is a one-time *corpus-construction* decision (like construct eligibility), so it never touches `DefaultEvaluationRunner` or any evaluation-domain type. Experiment-specific tooling under `experiments/wpi-demand-patent-matching/` supplies the real `requesting_organization` values and the one documented non-identifying placeholder value ("Anonymous Organization"), and derives two frozen artifacts mirroring the existing eligible-corpus pipeline exactly: an audit (`phase2_demand_independence_audit_n24_v1.json`) and a corpus projection (`dataset_phase2_independent_corpus_v1.json`).

**Tech Stack:** Python 3.12, Pydantic v2 (frozen domain models), pytest.

**Spec:** No separate spec document. The roadmap gap this closes (`docs/roadmap.md` line 141): *"Demand independence audit: the existing Phase-2 audits (#84–#86) check whether each demand *is* a valid technology solicitation (construct eligibility), not whether the 39/24/60 demands are independent observations (same company, sector, tech family, or duplicate industrial problem). These are different questions; only the first has been done."* This plan closes the **company/organization** axis only — see ADR 0029 (written by Task 3) §"What this ADR does not do" for why the other three named axes (sector, tech family, duplicate industrial problem) are explicitly deferred, not silently ignored. Direct structural precedent: `docs/phase2-demand-construct-eligibility-audit-protocol.md` + `backend/src/main/domain/models/annotation.py`'s `ConstructEligibilityRubric`/`ConstructEligibilityStatus` + `backend/src/main/application/annotation/construct_eligibility.py`'s `derive_construct_status` + `experiments/wpi-demand-patent-matching/checks/{generate,check}_construct_eligibility_audit.py` and `{generate,check}_eligible_corpus.py` — read all of these before starting; this plan's Task 1 and Task 2 mirror their shape almost exactly.

## Global Constraints

- Clean Architecture (CLAUDE.md): the grouping *rule* is generic, in `backend/src/main` (domain model + one pure application function), covered by synthetic-fixture unit tests. All real data (`requesting_organization` values, the non-identifying-placeholder exclusion list, generated artifacts) lives under `experiments/wpi-demand-patent-matching/` (ADR 0026 boundary). `backend/src/main` code must never contain a literal demand_id, organization name, or any other experiment-specific value.
- No heuristic: grouping is exact string match only. Never compute or infer organization identity from title, description, CPC, or any text-similarity signal — this would be exactly the circularity risk ADR 0027 already rejected for patent-family detection, for the identical reason.
- Independence is a corpus-construction-time decision, not a runtime evaluation policy: do **not** add any field to `EvaluationExecutionContext`, do **not** modify `DefaultEvaluationRunner`, do **not** import anything from `domain.models.evaluation` into the new domain model beyond what's already the existing pattern (`ConstructEligibilityRubric` imports nothing from `evaluation.py` except `RelevanceGrade` for an unrelated model in the same file — the new models added here import nothing from `evaluation.py` at all).
- Never modify any existing frozen artifact under `experiments/wpi-demand-patent-matching/data/` (`dataset_phase2_demand_corpus_n39.json`, `dataset_phase2_eligible_corpus_n24_v1.json`, `phase2_demand_construct_eligibility_n39_v1.json`, `dataset_phase2_demand_corpus_n39.origin_audit.json` — its content, not a new sidecar for it) or anything under `data/experiments/`.
- Every new frozen artifact this plan produces must have a sha256 sidecar, verified by both its own generation script (before writing) and a companion `check_*.py` script (independent re-derivation, not just a hash check) — mirroring `generate_eligible_corpus.py`/`check_eligible_corpus.py` exactly.
- Run the full suite from the repo root: `python -m pytest backend/test -q`. Run `python -m mypy backend/src/main --ignore-missing-imports` after every task. `experiments/` check scripts are run directly with `python <path>`, not via pytest (matching existing convention — confirm by checking whether any existing `check_*.py` is also wired into pytest before assuming otherwise; if it is, follow suit).

---

### Task 1: Domain contract + pure grouping function (generic, backend)

**Files:**
- Modify: `backend/src/main/domain/models/annotation.py`
- Create: `backend/src/main/application/annotation/demand_independence.py`
- Test: `backend/test/unit/application/test_demand_independence.py`

**Interfaces:**
- Consumes: nothing new from elsewhere in the codebase.
- Produces: `DemandIndependenceStatus`, `DemandOrganizationObservation`, `DemandIndependenceGroupEntry` (domain models), `derive_independence_groups(observations, non_identifying_values) -> list[DemandIndependenceGroupEntry]` (pure function) — both consumed by Task 2's experiment scripts.

- [ ] **Step 1: Write the failing tests**

Create `backend/test/unit/application/test_demand_independence.py`:

```python
"""Tests for application.annotation.demand_independence.derive_independence_groups
(ADR 0029). Synthetic fixtures only -- no real demand_id or organization name
from the WPI corpus appears here; that data lives entirely under
experiments/wpi-demand-patent-matching/ and is exercised by that directory's
own check scripts (Task 2)."""

import pytest

from application.annotation.demand_independence import derive_independence_groups
from domain.models.annotation import DemandIndependenceStatus, DemandOrganizationObservation


def _obs(demand_id: str, org: str | None) -> DemandOrganizationObservation:
    return DemandOrganizationObservation(demand_id=demand_id, requesting_organization=org)


def test_single_demand_with_organization_is_independent():
    entries = derive_independence_groups([_obs("D-1", "Acme Corp")], frozenset())
    assert entries[0].status == DemandIndependenceStatus.INDEPENDENT
    assert entries[0].independence_group_id == "Acme Corp"


def test_two_demands_same_organization_one_independent_one_pseudoreplicate():
    entries = derive_independence_groups(
        [_obs("D-2", "Acme Corp"), _obs("D-1", "Acme Corp")], frozenset()
    )
    by_id = {e.demand_id: e for e in entries}
    assert by_id["D-1"].status == DemandIndependenceStatus.INDEPENDENT
    assert by_id["D-2"].status == DemandIndependenceStatus.PSEUDOREPLICATE
    assert by_id["D-1"].independence_group_id == by_id["D-2"].independence_group_id == "Acme Corp"


def test_three_demands_same_organization_only_lexicographically_first_is_independent():
    entries = derive_independence_groups(
        [_obs("D-3", "Acme Corp"), _obs("D-1", "Acme Corp"), _obs("D-2", "Acme Corp")], frozenset()
    )
    by_id = {e.demand_id: e for e in entries}
    assert by_id["D-1"].status == DemandIndependenceStatus.INDEPENDENT
    assert by_id["D-2"].status == DemandIndependenceStatus.PSEUDOREPLICATE
    assert by_id["D-3"].status == DemandIndependenceStatus.PSEUDOREPLICATE


def test_representative_selection_is_independent_of_input_order():
    entries_order_a = derive_independence_groups(
        [_obs("D-1", "Acme Corp"), _obs("D-2", "Acme Corp")], frozenset()
    )
    entries_order_b = derive_independence_groups(
        [_obs("D-2", "Acme Corp"), _obs("D-1", "Acme Corp")], frozenset()
    )
    statuses_a = {e.demand_id: e.status for e in entries_order_a}
    statuses_b = {e.demand_id: e.status for e in entries_order_b}
    assert statuses_a == statuses_b == {
        "D-1": DemandIndependenceStatus.INDEPENDENT,
        "D-2": DemandIndependenceStatus.PSEUDOREPLICATE,
    }


def test_demand_with_none_organization_is_always_independent_and_ungrouped():
    entries = derive_independence_groups([_obs("D-1", None), _obs("D-2", None)], frozenset())
    for e in entries:
        assert e.status == DemandIndependenceStatus.INDEPENDENT
        assert e.independence_group_id is None


def test_demands_with_shared_non_identifying_value_are_not_grouped_with_each_other():
    entries = derive_independence_groups(
        [_obs("D-1", "Anonymous Organization"), _obs("D-2", "Anonymous Organization")],
        frozenset({"Anonymous Organization"}),
    )
    for e in entries:
        assert e.status == DemandIndependenceStatus.INDEPENDENT
        assert e.independence_group_id is None


def test_near_duplicate_organization_names_are_not_grouped_exact_match_only():
    """ADR 0029: exact string match only, never name-similarity inference."""
    entries = derive_independence_groups(
        [_obs("D-1", "Bax & Company"), _obs("D-2", "Indira from Bax&Co")], frozenset()
    )
    for e in entries:
        assert e.status == DemandIndependenceStatus.INDEPENDENT
        assert e.independence_group_id is None


def test_output_preserves_input_order():
    observations = [_obs("D-3", "X"), _obs("D-1", "Y"), _obs("D-2", "X")]
    entries = derive_independence_groups(observations, frozenset())
    assert [e.demand_id for e in entries] == ["D-3", "D-1", "D-2"]


def test_real_n24_eligible_corpus_organizations_reproduce_expected_grouping():
    """Regression pin using the WPI corpus's real, already-extracted
    requesting_organization values for the frozen N=24 eligible corpus (from
    dataset_phase2_demand_corpus_n39.origin_audit.json) -- confirms this pure
    function's real-world result before Task 2 freezes it as an artifact.
    18 INDEPENDENT (24 - 4 SMAR3TS pseudoreplicates - 2 Lacer pseudoreplicates),
    6 PSEUDOREPLICATE."""
    real_data = [
        ("INNOGET-1605", "Bax & Company"),
        ("INNOGET-1607", "ALLIANCE project"),
        ("INNOGET-1625", "Anonymous Organization"),
        ("INNOGET-1689", "Celsa Group"),
        ("INNOGET-1726", "Familia Torres"),
        ("INNOGET-1870", "Fundingbox"),
        ("INNOGET-1932", "Anonymous Organization"),
        ("INNOGET-1935", "Anonymous Organization"),
        ("INNOGET-1965", "Blue Room Innovation"),
        ("INNOGET-1972", "Anonymous Organization"),
        ("INNOGET-2006", "Alberto from Pharmactive Biotech Products"),
        ("INNOGET-2173", "Indira from Bax&Co"),
        ("INNOGET-2258", "Repsol"),
        ("INNOGET-2301", "INDUSAC"),
        ("INNOGET-2401", "SMAR3TS"),
        ("INNOGET-2403", "SMAR3TS"),
        ("INNOGET-2404", "SMAR3TS"),
        ("INNOGET-2405", "SMAR3TS"),
        ("INNOGET-2417", "SMAR3TS"),
        ("INNOGET-2491", "Lacer, S.A"),
        ("INNOGET-2492", "Lacer, S.A"),
        ("INNOGET-2493", "Lacer, S.A"),
        ("LOMBARDIA-860", None),
        ("LOMBARDIA-947", None),
    ]
    observations = [_obs(did, org) for did, org in real_data]
    entries = derive_independence_groups(observations, frozenset({"Anonymous Organization"}))
    by_id = {e.demand_id: e for e in entries}

    independent = {did for did, e in by_id.items() if e.status == DemandIndependenceStatus.INDEPENDENT}
    pseudoreplicate = {did for did, e in by_id.items() if e.status == DemandIndependenceStatus.PSEUDOREPLICATE}

    assert pseudoreplicate == {
        "INNOGET-2403", "INNOGET-2404", "INNOGET-2405", "INNOGET-2417",  # SMAR3TS, keep 2401
        "INNOGET-2492", "INNOGET-2493",  # Lacer, S.A, keep 2491
    }
    assert len(independent) == 18
    assert len(pseudoreplicate) == 6
    assert by_id["INNOGET-2401"].status == DemandIndependenceStatus.INDEPENDENT
    assert by_id["INNOGET-2491"].status == DemandIndependenceStatus.INDEPENDENT
    # The 4 "Anonymous Organization" demands and both None-organization demands
    # must all be INDEPENDENT with no group_id, never merged with each other.
    for did in ("INNOGET-1625", "INNOGET-1932", "INNOGET-1935", "INNOGET-1972", "LOMBARDIA-860", "LOMBARDIA-947"):
        assert by_id[did].status == DemandIndependenceStatus.INDEPENDENT
        assert by_id[did].independence_group_id is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest backend/test/unit/application/test_demand_independence.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'application.annotation.demand_independence'` (and the domain models don't exist yet either).

- [ ] **Step 3: Add the domain models**

Open `backend/src/main/domain/models/annotation.py`. Add these three classes at the end of the file:

```python
class DemandIndependenceStatus(StrEnum):
    """Outcome of the demand-independence grouping decision (ADR 0029,
    docs/phase2-demand-independence-audit-protocol.md)."""

    INDEPENDENT = "INDEPENDENT"
    PSEUDOREPLICATE = "PSEUDOREPLICATE"


class DemandOrganizationObservation(BaseModel):
    """One demand's observed requesting-organization identity, as extracted at
    acquisition time (domain.models.demand.RawExtractedDemandFields.organization_raw
    / DemandRecord.requesting_organization) -- never inferred at audit time. The
    sole basis this domain currently supports for grouping demands into
    independence clusters is an exact string match on this field. A text- or
    name-similarity heuristic (e.g. matching "Bax & Company" to "Indira from
    Bax&Co" as the same entity) is explicitly out of scope -- see ADR 0029
    Context, which rejects it for the same circularity reason ADR 0027 rejected
    heuristic patent-family detection: any similarity signal strong enough to
    merge near-duplicate names is also a signal that could correlate with the
    relevance judgments this dataset exists to evaluate honestly.
    """

    model_config = ConfigDict(frozen=True)

    demand_id: str = Field(min_length=1)
    requesting_organization: str | None = None


class DemandIndependenceGroupEntry(BaseModel):
    """Outcome of the demand-independence grouping decision for one demand
    (ADR 0029). `independence_group_id` is the exact `requesting_organization`
    string when the demand was assigned to a group; `None` when the demand's
    organization is missing or was excluded as a known non-identifying
    placeholder (e.g. "Anonymous Organization") -- such a demand is always
    INDEPENDENT and is never grouped with any other demand, including another
    demand that also has `independence_group_id=None`.
    """

    model_config = ConfigDict(frozen=True)

    demand_id: str = Field(min_length=1)
    requesting_organization: str | None = None
    independence_group_id: str | None = None
    status: DemandIndependenceStatus
```

- [ ] **Step 4: Add the pure grouping function**

Create `backend/src/main/application/annotation/demand_independence.py`:

```python
"""Pure demand-independence grouping decision (ADR 0029)."""

from domain.models.annotation import (
    DemandIndependenceGroupEntry,
    DemandIndependenceStatus,
    DemandOrganizationObservation,
)


def derive_independence_groups(
    observations: list[DemandOrganizationObservation],
    non_identifying_values: frozenset[str],
) -> list[DemandIndependenceGroupEntry]:
    """ADR 0029's independence-grouping decision rule, as a pure function of the
    observed organization identities. This is the only place the rule is
    implemented -- any independence audit derives its groupings here rather
    than recording them as an independent, unverified judgment.

    Two demands are grouped together (one INDEPENDENT, the rest
    PSEUDOREPLICATE) iff their `requesting_organization` values are identical,
    non-None, and not listed in `non_identifying_values` -- exact string match
    only, never inferred from name/text similarity. `non_identifying_values` is
    supplied by the caller (an experiment-specific, documented, literal
    exclusion list of known placeholder values from the source data, e.g.
    "Anonymous Organization") -- this function never hardcodes such values
    itself, since what counts as a non-identifying placeholder is a property of
    a specific data source, not of this decision rule.

    Within a group, the lexicographically smallest `demand_id` is marked
    INDEPENDENT and every other member PSEUDOREPLICATE -- a deterministic,
    arbitrary tie-break (mirrors ADR 0027 §2's `collapse` representative
    selection), not a claim that the selected demand is scientifically more
    representative than its group-mates.

    A demand whose `requesting_organization` is None or in
    `non_identifying_values` always receives `independence_group_id=None` and
    `status=INDEPENDENT`, and is never grouped with any other such demand.

    Returns entries in the same order as `observations`.
    """
    groups: dict[str, list[DemandOrganizationObservation]] = {}
    ungrouped: list[DemandOrganizationObservation] = []

    for obs in observations:
        org = obs.requesting_organization
        if org is None or org in non_identifying_values:
            ungrouped.append(obs)
        else:
            groups.setdefault(org, []).append(obs)

    entries_by_id: dict[str, DemandIndependenceGroupEntry] = {}

    for obs in ungrouped:
        entries_by_id[obs.demand_id] = DemandIndependenceGroupEntry(
            demand_id=obs.demand_id,
            requesting_organization=obs.requesting_organization,
            independence_group_id=None,
            status=DemandIndependenceStatus.INDEPENDENT,
        )

    for org, members in groups.items():
        members_sorted = sorted(members, key=lambda o: o.demand_id)
        for idx, obs in enumerate(members_sorted):
            status = (
                DemandIndependenceStatus.INDEPENDENT
                if idx == 0
                else DemandIndependenceStatus.PSEUDOREPLICATE
            )
            entries_by_id[obs.demand_id] = DemandIndependenceGroupEntry(
                demand_id=obs.demand_id,
                requesting_organization=org,
                independence_group_id=org,
                status=status,
            )

    return [entries_by_id[obs.demand_id] for obs in observations]
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest backend/test/unit/application/test_demand_independence.py -v`
Expected: all 10 tests PASS.

- [ ] **Step 6: Run the full suite and mypy**

Run: `python -m pytest backend/test -q`
Expected: all pass (no existing test touches `annotation.py`'s end-of-file or imports everything from it with a wildcard that could break — confirm by checking `test_construct_eligibility.py` and any other importer of `domain.models.annotation` still passes).

Run: `python -m mypy backend/src/main --ignore-missing-imports`
Expected: clean.

- [ ] **Step 7: Commit**

```bash
git add backend/src/main/domain/models/annotation.py \
        backend/src/main/application/annotation/demand_independence.py \
        backend/test/unit/application/test_demand_independence.py
git commit -m "feat(lab): add demand-independence grouping contract (ADR 0029)"
```

---

### Task 2: Freeze the audit trail — independence audit + independent corpus (experiment-specific)

**Files:**
- Create: `experiments/wpi-demand-patent-matching/data/dataset_phase2_demand_corpus_n39.origin_audit.json.sha256`
- Create: `experiments/wpi-demand-patent-matching/checks/generate_independence_audit.py`
- Create: `experiments/wpi-demand-patent-matching/checks/check_independence_audit.py`
- Create (generated by running the script above): `experiments/wpi-demand-patent-matching/data/phase2_demand_independence_audit_n24_v1.json`, `.json.sha256`, `.manifest.json`
- Create: `experiments/wpi-demand-patent-matching/checks/generate_independent_corpus.py`
- Create: `experiments/wpi-demand-patent-matching/checks/check_independent_corpus.py`
- Create (generated by running the script above): `experiments/wpi-demand-patent-matching/data/dataset_phase2_independent_corpus_v1.json`, `.sha256`, `.manifest.json`

**Interfaces:**
- Consumes: `derive_independence_groups`, `DemandOrganizationObservation` (Task 1), the existing frozen `dataset_phase2_eligible_corpus_n24_v1.json` and `dataset_phase2_demand_corpus_n39.origin_audit.json`.
- Produces: `dataset_phase2_independent_corpus_v1.json` — consumed by Task 3's roadmap/ADR update as the concrete result to cite, and by any future PR that needs the independent (as opposed to merely eligible) demand set.

- [ ] **Step 1: Freeze `origin_audit.json` with its own sha256 sidecar**

`experiments/wpi-demand-patent-matching/data/dataset_phase2_demand_corpus_n39.origin_audit.json` currently has no sha256 sidecar (it predates this codebase's sidecar-verification convention for derivation inputs). It is about to become a load-bearing input to a derivation script, so freeze it the same way every other derivation input already is. Do not modify its content.

```bash
cd experiments/wpi-demand-patent-matching/data
sha256sum dataset_phase2_demand_corpus_n39.origin_audit.json > /tmp/origin_audit_sha.txt
cat /tmp/origin_audit_sha.txt
```

Write the sidecar in the exact `<sha256>  <filename>` format the other sidecars use (verify by inspecting `dataset_phase2_eligible_corpus_n24_v1.sha256`'s exact format first — two spaces, filename with no path prefix):

```bash
echo "$(sha256sum dataset_phase2_demand_corpus_n39.origin_audit.json)" > dataset_phase2_demand_corpus_n39.origin_audit.json.sha256
cat dataset_phase2_demand_corpus_n39.origin_audit.json.sha256
```

Confirm the format matches the existing sidecar convention exactly (check one existing `.sha256` file's exact bytes with `cat -A` if unsure about spacing) before proceeding — the verification code in Step 3/4 below depends on `sidecar_path.read_text().strip().split(maxsplit=1)` parsing correctly.

- [ ] **Step 2: Write `generate_independence_audit.py`**

Create `experiments/wpi-demand-patent-matching/checks/generate_independence_audit.py`:

```python
#!/usr/bin/env python3
"""Derives the WPI Phase 2 demand-independence audit (ADR 0029) for the N=24
eligible corpus: for each eligible demand, join its already-frozen
requesting_organization value (from dataset_phase2_demand_corpus_n39.origin_audit.json,
extracted at acquisition time -- never inferred here) and classify it via
Nexus's generic exact-match grouping rule
(application.annotation.demand_independence.derive_independence_groups).

This is experiment tooling: it supplies the concrete non_identifying_values
exclusion list (a literal, documented property of the InnoGet source data, not
a general rule) and persists the resulting frozen artifact. It does not
implement the grouping rule itself -- that lives in backend/src/main and is
covered by generic, synthetic-fixture unit tests
(backend/test/unit/application/test_demand_independence.py).
"""

import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "backend" / "src" / "main"))

from application.annotation.demand_independence import derive_independence_groups  # noqa: E402
from domain.models.annotation import DemandOrganizationObservation  # noqa: E402

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

ELIGIBLE_NAME = "dataset_phase2_eligible_corpus_n24_v1.json"
ELIGIBLE_SHA_NAME = "dataset_phase2_eligible_corpus_n24_v1.sha256"
ORIGIN_AUDIT_NAME = "dataset_phase2_demand_corpus_n39.origin_audit.json"
ORIGIN_AUDIT_SHA_NAME = "dataset_phase2_demand_corpus_n39.origin_audit.json.sha256"
AUDIT_NAME = "phase2_demand_independence_audit_n24_v1.json"
AUDIT_SHA_NAME = "phase2_demand_independence_audit_n24_v1.json.sha256"
AUDIT_MANIFEST_NAME = "phase2_demand_independence_audit_n24_v1.manifest.json"

# InnoGet's own placeholder for a demand whose requesting organization was
# withheld/anonymized at the source -- a literal, documented sentinel string,
# never a similarity judgment. Present for 4/24 eligible demands (INNOGET-1625,
# 1932, 1935, 1972), each independently anonymized and never to be treated as
# a shared identity with each other.
NON_IDENTIFYING_VALUES = frozenset({"Anonymous Organization"})


def _load(name: str) -> dict:
    with open(DATA_DIR / name, encoding="utf-8") as f:
        return json.load(f)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _verify_sidecar(artifact_path: Path, sidecar_path: Path) -> str:
    computed = _sha256_file(artifact_path)
    declared_sha, declared_name = sidecar_path.read_text(encoding="utf-8").strip().split(maxsplit=1)
    assert declared_sha == computed, (
        f"{artifact_path.name}: bytes do not match {sidecar_path.name} -- refusing to derive "
        "from a modified input. Investigate before regenerating."
    )
    assert declared_name == artifact_path.name
    return computed


def main() -> int:
    eligible_sha = _verify_sidecar(DATA_DIR / ELIGIBLE_NAME, DATA_DIR / ELIGIBLE_SHA_NAME)
    origin_audit_sha = _verify_sidecar(DATA_DIR / ORIGIN_AUDIT_NAME, DATA_DIR / ORIGIN_AUDIT_SHA_NAME)

    eligible = _load(ELIGIBLE_NAME)
    origin_audit = _load(ORIGIN_AUDIT_NAME)

    org_by_id = {r["demand_id"]: r.get("requesting_organization") for r in origin_audit["records"]}
    eligible_ids = [d["demand_id"] for d in eligible["demands"]]

    missing = [did for did in eligible_ids if did not in org_by_id]
    if missing:
        raise SystemExit(f"origin_audit.json has no record for eligible demand_ids: {missing}")

    observations = [
        DemandOrganizationObservation(demand_id=did, requesting_organization=org_by_id[did])
        for did in eligible_ids
    ]
    entries = derive_independence_groups(observations, NON_IDENTIFYING_VALUES)

    artifact = {
        "audit_id": "phase2_demand_independence_audit_n24_v1",
        "protocol_reference": "docs/phase2-demand-independence-audit-protocol.md",
        "adr_reference": "docs/adr/0029-demand-independence-audit-contract.md",
        "source_eligible_corpus": f"experiments/wpi-demand-patent-matching/data/{ELIGIBLE_NAME}",
        "source_eligible_corpus_sha256": eligible_sha,
        "source_origin_audit": f"experiments/wpi-demand-patent-matching/data/{ORIGIN_AUDIT_NAME}",
        "source_origin_audit_sha256": origin_audit_sha,
        "non_identifying_values": sorted(NON_IDENTIFYING_VALUES),
        "entries": [e.model_dump(mode="json") for e in entries],
    }

    output_file = DATA_DIR / AUDIT_NAME
    serialized = json.dumps(artifact, indent=2, ensure_ascii=False) + "\n"
    output_file.write_text(serialized, encoding="utf-8")

    digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    (DATA_DIR / AUDIT_SHA_NAME).write_text(f"{digest}  {output_file.name}\n", encoding="utf-8")

    independent = sum(1 for e in entries if e.status == "INDEPENDENT")
    pseudoreplicate = sum(1 for e in entries if e.status == "PSEUDOREPLICATE")
    group_sizes: dict[str, int] = {}
    for e in entries:
        if e.independence_group_id is not None:
            group_sizes[e.independence_group_id] = group_sizes.get(e.independence_group_id, 0) + 1

    manifest = {
        "total": len(entries),
        "independent_count": independent,
        "pseudoreplicate_count": pseudoreplicate,
        "group_sizes": group_sizes,
    }
    (DATA_DIR / AUDIT_MANIFEST_NAME).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    print(f"Emitted {output_file}: {digest}")
    print(f"INDEPENDENT={independent} PSEUDOREPLICATE={pseudoreplicate} (total={len(entries)})")
    print(f"Groups with >1 member: { {k: v for k, v in group_sizes.items() if v > 1} }")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 3: Run it and inspect the output**

```bash
python experiments/wpi-demand-patent-matching/checks/generate_independence_audit.py
```

Expected output: `INDEPENDENT=18 PSEUDOREPLICATE=6 (total=24)`, groups with >1 member showing `SMAR3TS: 5` and `Lacer, S.A: 3`. If the numbers differ from this, stop and investigate before proceeding — this plan's Task 1 Step 1 test (`test_real_n24_eligible_corpus_organizations_reproduce_expected_grouping`) already pins these exact expected values independently; a mismatch here means the real `origin_audit.json` data has drifted from what that test assumed, or the join logic has a bug.

- [ ] **Step 4: Write `check_independence_audit.py`**

Create `experiments/wpi-demand-patent-matching/checks/check_independence_audit.py`:

```python
#!/usr/bin/env python3
"""Manifest-conformance + re-derivation check for the WPI Phase 2 demand-
independence audit (ADR 0029). Verifies phase2_demand_independence_audit_n24_v1.json
is EXACTLY what application.annotation.demand_independence.derive_independence_groups
produces from the frozen eligible corpus + origin_audit.json, with no drift.
"""

import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "backend" / "src" / "main"))

from application.annotation.demand_independence import derive_independence_groups  # noqa: E402
from domain.models.annotation import DemandOrganizationObservation  # noqa: E402

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

ELIGIBLE_NAME = "dataset_phase2_eligible_corpus_n24_v1.json"
ELIGIBLE_SHA_NAME = "dataset_phase2_eligible_corpus_n24_v1.sha256"
ORIGIN_AUDIT_NAME = "dataset_phase2_demand_corpus_n39.origin_audit.json"
ORIGIN_AUDIT_SHA_NAME = "dataset_phase2_demand_corpus_n39.origin_audit.json.sha256"
AUDIT_NAME = "phase2_demand_independence_audit_n24_v1.json"
AUDIT_SHA_NAME = "phase2_demand_independence_audit_n24_v1.json.sha256"


def _load(name: str) -> dict:
    with open(DATA_DIR / name, encoding="utf-8") as f:
        return json.load(f)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _verify_sidecar(artifact_path: Path, sidecar_path: Path) -> str:
    computed = _sha256(artifact_path)
    declared_sha, declared_name = sidecar_path.read_text(encoding="utf-8").strip().split(maxsplit=1)
    assert declared_sha == computed, f"{artifact_path.name}: bytes do not match {sidecar_path.name}"
    assert declared_name == artifact_path.name
    return computed


def main() -> int:
    eligible_sha = _verify_sidecar(DATA_DIR / ELIGIBLE_NAME, DATA_DIR / ELIGIBLE_SHA_NAME)
    origin_audit_sha = _verify_sidecar(DATA_DIR / ORIGIN_AUDIT_NAME, DATA_DIR / ORIGIN_AUDIT_SHA_NAME)
    _verify_sidecar(DATA_DIR / AUDIT_NAME, DATA_DIR / AUDIT_SHA_NAME)

    eligible = _load(ELIGIBLE_NAME)
    origin_audit = _load(ORIGIN_AUDIT_NAME)
    audit = _load(AUDIT_NAME)

    assert audit["source_eligible_corpus_sha256"] == eligible_sha
    assert audit["source_origin_audit_sha256"] == origin_audit_sha

    org_by_id = {r["demand_id"]: r.get("requesting_organization") for r in origin_audit["records"]}
    eligible_ids = [d["demand_id"] for d in eligible["demands"]]

    non_identifying_values = frozenset(audit["non_identifying_values"])
    observations = [
        DemandOrganizationObservation(demand_id=did, requesting_organization=org_by_id[did])
        for did in eligible_ids
    ]
    expected_entries = derive_independence_groups(observations, non_identifying_values)
    expected = [e.model_dump(mode="json") for e in expected_entries]

    assert audit["entries"] == expected, "Audit entries do not match a fresh re-derivation -- drift detected."

    independent_ids = {e["demand_id"] for e in audit["entries"] if e["status"] == "INDEPENDENT"}
    pseudoreplicate_ids = {e["demand_id"] for e in audit["entries"] if e["status"] == "PSEUDOREPLICATE"}
    assert independent_ids | pseudoreplicate_ids == set(eligible_ids)
    assert not (independent_ids & pseudoreplicate_ids)

    print(
        f"OK: {len(independent_ids)} INDEPENDENT, {len(pseudoreplicate_ids)} PSEUDOREPLICATE "
        "(re-derivation matches exactly)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

Run it:

```bash
python experiments/wpi-demand-patent-matching/checks/check_independence_audit.py
```

Expected: `OK: 18 INDEPENDENT, 6 PSEUDOREPLICATE (re-derivation matches exactly)`.

- [ ] **Step 5: Write `generate_independent_corpus.py`**

Create `experiments/wpi-demand-patent-matching/checks/generate_independent_corpus.py`:

```python
#!/usr/bin/env python3
"""Derives the WPI Phase 2 independent demand corpus (ADR 0029) as a
deterministic projection: read the independence audit -> select INDEPENDENT
demand_ids -> project the matching records out of the frozen N=24 eligible
corpus, in N=24 order.

Pure filter, no judgment: the audit's status is treated as already decided by
application.annotation.demand_independence.derive_independence_groups. This
script does not re-derive it.
"""

import hashlib
import json
import sys
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

ELIGIBLE_NAME = "dataset_phase2_eligible_corpus_n24_v1.json"
ELIGIBLE_SHA_NAME = "dataset_phase2_eligible_corpus_n24_v1.sha256"
AUDIT_NAME = "phase2_demand_independence_audit_n24_v1.json"
AUDIT_SHA_NAME = "phase2_demand_independence_audit_n24_v1.json.sha256"
INDEPENDENT_NAME = "dataset_phase2_independent_corpus_v1.json"
INDEPENDENT_SHA_NAME = "dataset_phase2_independent_corpus_v1.sha256"
INDEPENDENT_MANIFEST_NAME = "dataset_phase2_independent_corpus_v1.manifest.json"


def _load(name: str) -> dict:
    with open(DATA_DIR / name, encoding="utf-8") as f:
        return json.load(f)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _verify_sidecar(artifact_path: Path, sidecar_path: Path) -> str:
    computed = _sha256_file(artifact_path)
    declared_sha, declared_name = sidecar_path.read_text(encoding="utf-8").strip().split(maxsplit=1)
    assert declared_sha == computed, (
        f"{artifact_path.name}: bytes do not match {sidecar_path.name} -- refusing to derive "
        "from a modified input. Investigate before regenerating."
    )
    assert declared_name == artifact_path.name
    return computed


def main() -> int:
    eligible_sha = _verify_sidecar(DATA_DIR / ELIGIBLE_NAME, DATA_DIR / ELIGIBLE_SHA_NAME)
    audit_sha = _verify_sidecar(DATA_DIR / AUDIT_NAME, DATA_DIR / AUDIT_SHA_NAME)

    eligible = _load(ELIGIBLE_NAME)
    audit = _load(AUDIT_NAME)
    eligible_manifest = _load("dataset_phase2_eligible_corpus_n24_v1.manifest.json")

    independent_ids = {e["demand_id"] for e in audit["entries"] if e["status"] == "INDEPENDENT"}
    independent_demands = [d for d in eligible["demands"] if d["demand_id"] in independent_ids]

    independent_dataset = {
        "dataset_id": "nexus-phase2-independent-corpus-v1",
        "schema_version": eligible["schema_version"],
        "dataset_version": "1.0.0",
        "description": (
            "Nexus Phase 2 independent demand corpus: deterministic projection of "
            "dataset_phase2_eligible_corpus_n24_v1.json onto the status == INDEPENDENT "
            "entries of phase2_demand_independence_audit_n24_v1.json (ADR 0029). One "
            "demand per requesting-organization identity (exact string match); a demand "
            "whose organization is missing or a known non-identifying placeholder is "
            "always included. See docs/phase2-demand-independence-audit-protocol.md."
        ),
        "demands": independent_demands,
    }

    independent_path = DATA_DIR / INDEPENDENT_NAME
    independent_path.write_text(
        json.dumps(independent_dataset, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    independent_sha = _sha256_file(independent_path)

    manifest = {
        "dataset_id": independent_dataset["dataset_id"],
        "schema_version": independent_dataset["schema_version"],
        "dataset_version": independent_dataset["dataset_version"],
        "source_authorities": eligible_manifest["source_authorities"],
        "demand_count": len(independent_demands),
        "patent_count": 0,
        "annotation_count": 0,
        "content_sha256": independent_sha,
        "derived_from": {
            "source_eligible_corpus_path": f"experiments/wpi-demand-patent-matching/data/{ELIGIBLE_NAME}",
            "source_eligible_corpus_sha256": eligible_sha,
            "independence_audit_path": f"experiments/wpi-demand-patent-matching/data/{AUDIT_NAME}",
            "independence_audit_sha256": audit_sha,
        },
    }

    (DATA_DIR / INDEPENDENT_MANIFEST_NAME).write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (DATA_DIR / INDEPENDENT_SHA_NAME).write_text(f"{independent_sha}  {INDEPENDENT_NAME}\n", encoding="utf-8")

    print(f"Wrote {len(independent_demands)} independent demands -> {independent_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

Run it:

```bash
python experiments/wpi-demand-patent-matching/checks/generate_independent_corpus.py
```

Expected: `Wrote 18 independent demands -> .../dataset_phase2_independent_corpus_v1.json`.

- [ ] **Step 6: Write `check_independent_corpus.py`**

Create `experiments/wpi-demand-patent-matching/checks/check_independent_corpus.py`:

```python
#!/usr/bin/env python3
"""Manifest-conformance check for the WPI Phase 2 independent demand corpus
(ADR 0029). Verifies dataset_phase2_independent_corpus_v1.json is exactly the
deterministic projection of dataset_phase2_eligible_corpus_n24_v1.json onto the
status == INDEPENDENT entries of phase2_demand_independence_audit_n24_v1.json:
  - both inputs are treated as frozen (sha256-checked; independence status
    itself is not re-derived here, that is check_independence_audit.py's job);
  - the independent sequence is exactly the N=24 subsequence induced by
    INDEPENDENT, in N=24 order (no reordering, no PSEUDOREPLICATE leakage);
  - each selected demand object is field-for-field identical, as parsed JSON,
    to its N=24 counterpart -- no field transformation.
"""

import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "backend" / "src" / "main"))

from domain.models.evaluation import DemandCorpus  # noqa: E402

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

ELIGIBLE_NAME = "dataset_phase2_eligible_corpus_n24_v1.json"
ELIGIBLE_SHA_NAME = "dataset_phase2_eligible_corpus_n24_v1.sha256"
AUDIT_NAME = "phase2_demand_independence_audit_n24_v1.json"
AUDIT_SHA_NAME = "phase2_demand_independence_audit_n24_v1.json.sha256"
INDEPENDENT_NAME = "dataset_phase2_independent_corpus_v1.json"
INDEPENDENT_SHA_NAME = "dataset_phase2_independent_corpus_v1.sha256"
INDEPENDENT_MANIFEST_NAME = "dataset_phase2_independent_corpus_v1.manifest.json"


def _load(name: str) -> dict:
    with open(DATA_DIR / name, encoding="utf-8") as f:
        return json.load(f)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _verify_sidecar(artifact_path: Path, sidecar_path: Path) -> str:
    computed = _sha256(artifact_path)
    declared_sha, declared_name = sidecar_path.read_text(encoding="utf-8").strip().split(maxsplit=1)
    assert declared_sha == computed, f"{artifact_path.name}: bytes do not match {sidecar_path.name}"
    assert declared_name == artifact_path.name
    return computed


def main() -> int:
    eligible_sha = _verify_sidecar(DATA_DIR / ELIGIBLE_NAME, DATA_DIR / ELIGIBLE_SHA_NAME)
    audit_sha = _verify_sidecar(DATA_DIR / AUDIT_NAME, DATA_DIR / AUDIT_SHA_NAME)
    independent_sha = _verify_sidecar(DATA_DIR / INDEPENDENT_NAME, DATA_DIR / INDEPENDENT_SHA_NAME)

    eligible = _load(ELIGIBLE_NAME)
    audit = _load(AUDIT_NAME)
    independent = _load(INDEPENDENT_NAME)
    manifest = _load(INDEPENDENT_MANIFEST_NAME)

    assert manifest["content_sha256"] == independent_sha
    assert manifest["derived_from"]["source_eligible_corpus_sha256"] == eligible_sha
    assert manifest["derived_from"]["independence_audit_sha256"] == audit_sha

    eligible_by_id = {d["demand_id"]: d for d in eligible["demands"]}
    eligible_order = [d["demand_id"] for d in eligible["demands"]]

    independent_ids_from_audit = {e["demand_id"] for e in audit["entries"] if e["status"] == "INDEPENDENT"}
    pseudoreplicate_ids = {e["demand_id"] for e in audit["entries"] if e["status"] != "INDEPENDENT"}

    independent_demands = independent["demands"]
    independent_ids = [d["demand_id"] for d in independent_demands]

    assert len(independent_ids) == len(set(independent_ids)), "Duplicate demand_id in independent corpus"
    assert set(independent_ids) == independent_ids_from_audit, (
        "Independent corpus does not match exactly the audit's INDEPENDENT demand_ids "
        f"(missing={independent_ids_from_audit - set(independent_ids)}, "
        f"extra={set(independent_ids) - independent_ids_from_audit})"
    )
    assert not (set(independent_ids) & pseudoreplicate_ids), "Independent corpus leaks a PSEUDOREPLICATE demand_id"

    expected_order = [did for did in eligible_order if did in independent_ids_from_audit]
    assert independent_ids == expected_order, (
        "Independent corpus order must be the N=24 subsequence induced by INDEPENDENT, "
        f"got {independent_ids} expected {expected_order}"
    )

    for demand in independent_demands:
        assert demand == eligible_by_id[demand["demand_id"]], (
            f"{demand['demand_id']}: independent-corpus object differs from its N=24 counterpart"
        )

    assert manifest["demand_count"] == len(independent_demands)

    # Schema-contract validity (generic DemandCorpus, not an experiment-specific rule).
    DemandCorpus.model_validate_json((DATA_DIR / INDEPENDENT_NAME).read_bytes())

    print(f"OK: {len(independent_demands)} independent demands")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

Run it:

```bash
python experiments/wpi-demand-patent-matching/checks/check_independent_corpus.py
```

Expected: `OK: 18 independent demands`.

- [ ] **Step 7: Run the full suite and mypy**

Run: `python -m pytest backend/test -q`
Expected: all pass (these are standalone scripts, not part of the pytest suite — confirm this matches how `check_eligible_corpus.py` etc. are treated today before assuming; if the existing checks ARE wired into pytest via some collection mechanism, wire these the same way).

Run: `python -m mypy backend/src/main --ignore-missing-imports`
Expected: clean (the `experiments/` scripts are not covered by this mypy invocation, matching existing convention).

- [ ] **Step 8: Commit**

```bash
git add experiments/wpi-demand-patent-matching/data/dataset_phase2_demand_corpus_n39.origin_audit.json.sha256 \
        experiments/wpi-demand-patent-matching/checks/generate_independence_audit.py \
        experiments/wpi-demand-patent-matching/checks/check_independence_audit.py \
        experiments/wpi-demand-patent-matching/data/phase2_demand_independence_audit_n24_v1.json \
        experiments/wpi-demand-patent-matching/data/phase2_demand_independence_audit_n24_v1.json.sha256 \
        experiments/wpi-demand-patent-matching/data/phase2_demand_independence_audit_n24_v1.manifest.json \
        experiments/wpi-demand-patent-matching/checks/generate_independent_corpus.py \
        experiments/wpi-demand-patent-matching/checks/check_independent_corpus.py \
        experiments/wpi-demand-patent-matching/data/dataset_phase2_independent_corpus_v1.json \
        experiments/wpi-demand-patent-matching/data/dataset_phase2_independent_corpus_v1.sha256 \
        experiments/wpi-demand-patent-matching/data/dataset_phase2_independent_corpus_v1.manifest.json
git commit -m "data(lab): freeze Phase 2 demand-independence audit + independent corpus (N=18) (ADR 0029)"
```

---

### Task 3: ADR 0029, protocol doc, roadmap update

**Files:**
- Create: `docs/adr/0029-demand-independence-audit-contract.md`
- Create: `docs/phase2-demand-independence-audit-protocol.md`
- Modify: `docs/roadmap.md`

**Interfaces:** None — documentation only, closing out this plan.

- [ ] **Step 1: Write the protocol doc**

Create `docs/phase2-demand-independence-audit-protocol.md`, mirroring `docs/phase2-demand-construct-eligibility-audit-protocol.md`'s structure (Status/Why this exists/Explicit separation/Rubric or rule/Closure):

```markdown
# Phase 2 Demand Independence Audit — Protocol

**Status:** Closed. Resolves the roadmap's "demand independence audit" gap for the
organization axis only (see "Explicit separation from other independence axes" below).

## Why this exists

`docs/roadmap.md` (§6, external scientific-rigor review): *"Demand independence audit:
the existing Phase-2 audits (#84–#86) check whether each demand *is* a valid technology
solicitation (construct eligibility), not whether the 39/24/60 demands are independent
observations (same company, sector, tech family, or duplicate industrial problem).
These are different questions; only the first has been done."*

This document closes the first, most tractable sub-question: two demands submitted by
the same requesting organization are not independent observations of the underlying
matching problem in the same sense two demands from different organizations are — an
organization that submits five related solicitations is one recurring perspective, not
five independent draws from the population this benchmark samples.

## Explicit separation from other independence axes

**Sector, technology family, and duplicate-industrial-problem non-independence are not
addressed here and are not inferred from organization identity.** A demand can share an
organization with another demand while addressing an entirely distinct technical
problem (both remain independent on every axis except the one this document closes);
conversely a demand can duplicate another's industrial problem while coming from a
different organization (a case this document cannot and does not detect). See ADR 0029
§"What this ADR does not do" for why each of the other three axes is deferred rather
than solved with a heuristic.

## Grouping rule

For each of the N=24 eligible demands, using only `requesting_organization` (extracted
at acquisition time, `dataset_phase2_demand_corpus_n39.origin_audit.json` — never
inferred from title/description text):

- Two demands with an **identical, non-empty, non-placeholder** `requesting_organization`
  string are grouped. The lexicographically smallest `demand_id` in the group is
  `INDEPENDENT`; every other member is `PSEUDOREPLICATE`. This tie-break is
  deterministic, not a claim that the selected demand is the most representative of
  its group — see ADR 0029 §3.
- A demand whose `requesting_organization` is missing (`null`), or equal to the one
  documented non-identifying placeholder value `"Anonymous Organization"` (InnoGet's
  own sentinel for an anonymized submitter), is always `INDEPENDENT` and is never
  grouped with any other demand — including another demand that also has a missing or
  placeholder organization.
- Grouping is **exact string match only**. `"Bax & Company"` (INNOGET-1605) and `"Indira
  from Bax&Co"` (INNOGET-2173) are almost certainly the same real-world organization but
  are NOT grouped — merging them would require a name-normalization heuristic, which
  this protocol explicitly declines to build for the same reason ADR 0027 declined a
  patent-family-detection heuristic (see ADR 0029 Context).

Implemented once, generically, in `application.annotation.demand_independence.derive_independence_groups`
(backend/src/main), covered by synthetic-fixture tests plus a pinned real-data regression
test (`backend/test/unit/application/test_demand_independence.py`). This document's
closure is the record of applying that rule to the real N=24 corpus, not a second,
independent implementation of the rule itself.

## Closure

Applied to the frozen `dataset_phase2_eligible_corpus_n24_v1.json` (24 demands) via
`experiments/wpi-demand-patent-matching/checks/generate_independence_audit.py`, frozen as
`phase2_demand_independence_audit_n24_v1.json`:

- **18 INDEPENDENT**, **6 PSEUDOREPLICATE**.
- Two real, multi-member organization groups found:
  - **SMAR3TS** (5 members: INNOGET-2401, 2403, 2404, 2405, 2417) → INNOGET-2401 independent, 4 pseudoreplicates.
  - **Lacer, S.A** (3 members: INNOGET-2491, 2492, 2493) → INNOGET-2491 independent, 2 pseudoreplicates.
- 4 demands carry the `"Anonymous Organization"` placeholder (INNOGET-1625, 1932, 1935,
  1972) — correctly treated as 4 independent, unrelated demands, not one group.
- 2 demands (LOMBARDIA-860, LOMBARDIA-947) have no recorded organization — correctly
  treated as 2 independent demands.
- The remaining 9 organizations (Bax & Company, ALLIANCE project, Celsa Group, Familia
  Torres, Fundingbox, Blue Room Innovation, Alberto from Pharmactive Biotech Products,
  Indira from Bax&Co, Repsol, INDUSAC) each appear exactly once in the eligible corpus.

Projected into a new frozen artifact, `dataset_phase2_independent_corpus_v1.json`
(N=18), via `experiments/wpi-demand-patent-matching/checks/generate_independent_corpus.py`.
Independently re-verified (fresh re-derivation, not just a hash check) by
`check_independence_audit.py` and `check_independent_corpus.py`.

## Known limitations (not resolved by this document)

1. **Near-duplicate organization names are not merged** (see "Grouping rule" above,
   `Bax & Company` / `Indira from Bax&Co`). A future organization-name normalization
   pass is a separate, explicit decision — not silently applied here.
2. **Sector, technology-family, and duplicate-industrial-problem independence are
   entirely unaddressed** — see ADR 0029 for why.
3. **The frozen WPI Dev/Test split (`experiments/wpi-demand-patent-matching/data/devtest_split_n13_v1.json`)
   currently places organization-correlated demands on opposite sides of the split**:
   Lacer, S.A.'s INNOGET-2491 is in Dev while INNOGET-2492/2493 are in Test; SMAR3TS's
   INNOGET-2404 is in Dev while INNOGET-2403 is in Test. This is a real leakage risk in
   an already-frozen artifact. This document records it; it is not fixed here —
   re-freezing the Dev/Test split is a separate, larger decision requiring its own
   review (see `docs/roadmap.md`).
```

- [ ] **Step 2: Write ADR 0029**

Create `docs/adr/0029-demand-independence-audit-contract.md`:

```markdown
# ADR 0029: Demand Independence Audit Contract

**Status:** Accepted
**Date:** 2026-09-11
**Scope:** Closes the organization/company axis of the roadmap's "demand independence
audit" gap (`docs/roadmap.md` §6). The sector, technology-family, and
duplicate-industrial-problem axes named in that same gap remain open — see "What this
ADR does not do."

## Context

`docs/roadmap.md` names the gap directly: *"Demand independence audit: the existing
Phase-2 audits (#84–#86) check whether each demand *is* a valid technology solicitation
(construct eligibility), not whether the 39/24/60 demands are independent observations
(same company, sector, tech family, or duplicate industrial problem). These are
different questions; only the first has been done."*

`domain/models/demand.py`'s `RawExtractedDemandFields.organization_raw` and
`DemandRecord.requesting_organization` already carry a real, acquisition-time-extracted
organization identity for every demand — never inferred from title/description text.
This field survives today only in
`experiments/wpi-demand-patent-matching/data/dataset_phase2_demand_corpus_n39.origin_audit.json`,
an audit sidecar never joined against the frozen eligible corpus for any
independence-relevant purpose.

The obvious temptation, as with ADR 0027's patent-family question, is to widen coverage
by clustering demands with *similar* (not identical) organization names, or by
inferring shared identity from title/description similarity. This ADR rejects that path
for the same reason ADR 0027 rejected heuristic patent-family detection: any
similarity signal strong enough to catch real near-duplicates (e.g. "Bax & Company" vs.
"Indira from Bax&Co") is also a signal that risks correlating with the very relevance
judgments this dataset exists to evaluate honestly, and a false-positive merge would
silently discard a genuinely independent demand from the powered sample.

## Decision

### 1. `requesting_organization` is accepted, never inferred

The grouping rule (§2) operates only on `requesting_organization` values already
extracted at acquisition time. No code introduced by this ADR computes an organization
identity from title, description, CPC, or any other text signal.

### 2. Exact-match grouping only, with an explicit non-identifying-value exclusion list

Two demands are grouped iff their `requesting_organization` values are byte-identical
and neither is `None` nor listed in a caller-supplied `non_identifying_values` set (a
literal, documented property of a specific data source — e.g. `experiments/wpi-demand-patent-matching`'s
`generate_independence_audit.py` supplies `{"Anonymous Organization"}`, InnoGet's own
placeholder for an anonymized submitter). This set is never hardcoded inside the
generic decision rule (`application.annotation.demand_independence.derive_independence_groups`,
backend/src/main) — it is always supplied by the experiment-specific caller, per ADR
0026's boundary and per this codebase's existing "no hardcoded experiment-specific
values in generic backend code" convention.

### 3. Deterministic, arbitrary representative selection

Within a group, the lexicographically smallest `demand_id` is `INDEPENDENT`; every
other member is `PSEUDOREPLICATE`. This mirrors ADR 0027 §2's `collapse` tie-break
exactly, and carries the same caveat: it is a determinism mechanism, not a scientific
claim that the selected demand is the group's best or most representative member. That
decision (e.g. earliest posting date, most complete specification) is left for whichever
future PR needs it to be explicit, exactly as ADR 0027 left the analogous question open
for patent families.

### 4. Independence is a corpus-construction-time decision, not a runtime evaluation policy

Unlike `family_policy` (ADR 0027), which is a per-run `EvaluationExecutionContext` field
because the same corpus might legitimately be evaluated under different family
policies in different runs, demand independence is decided **once**, when the analytic
corpus is constructed — exactly like construct eligibility (#84–#86) already is. There
is no `independence_policy` field, and this ADR does not touch
`EvaluationExecutionContext`, `DefaultEvaluationRunner`, or any evaluation-domain type.
The output is a new frozen dataset artifact (§5), not a new execution mode.

### 5. Provenance chain

Two new frozen artifacts, mirroring the eligible-corpus pipeline (`generate_eligible_corpus.py`
/ `check_eligible_corpus.py`) exactly:

- `phase2_demand_independence_audit_n24_v1.json` — one entry per eligible demand,
  recording `requesting_organization`, `independence_group_id`, and `status`
  (`INDEPENDENT`/`PSEUDOREPLICATE`), sha256-sidecared, generated by
  `generate_independence_audit.py`, independently re-verified by
  `check_independence_audit.py` (a fresh re-derivation, not merely a hash check).
- `dataset_phase2_independent_corpus_v1.json` — the deterministic projection of the
  N=24 eligible corpus onto `INDEPENDENT` demand_ids, sha256-sidecared, generated by
  `generate_independent_corpus.py`, independently re-verified by
  `check_independent_corpus.py`.

`dataset_phase2_demand_corpus_n39.origin_audit.json` gains its own sha256 sidecar for
the first time (content unchanged) since it is now a load-bearing derivation input,
matching this codebase's established sidecar-verification convention for every other
derivation input.

## What this ADR does not do

- Does not address sector-based non-independence (a separate axis; sector assignment
  already exists as its own frozen artifact — see #80/#91/#92 — and using it for
  independence purposes is a distinct, undecided design question, not resolved here).
- Does not address technology-family non-independence (distinct from, and not to be
  confused with, ADR 0027's *patent*-family concept — this would be a demand-side
  concept with its own definition question).
- Does not implement, or authorize implementing, any duplicate-industrial-problem
  detector (would require text/title similarity — the same circularity risk this ADR's
  Context section rejects for organization-name matching, at a higher-stakes level
  since it operates directly on the demand text used for retrieval).
- Does not normalize or merge near-duplicate organization names (e.g. "Bax & Company"
  vs. "Indira from Bax&Co") — documented as a known limitation, not silently resolved.
- Does not grow the corpus toward the N=60 target — this ADR operates entirely within
  the existing frozen N=24 eligible corpus.
- Does not fix the Dev/Test split leak this audit surfaced (organization-correlated
  demands on opposite sides of `devtest_split_n13_v1.json`) — recorded in the protocol
  doc's "Known limitations" and in `docs/roadmap.md`, not resolved by re-freezing the
  split here.
- Does not change any field on `EvaluationExecutionContext`, `DefaultEvaluationRunner`,
  or any evaluation-domain type (§4).

## Consequences

### Positive

- Closes the most tractable of the roadmap's four named independence axes with a
  precise, testable, honest contract, using only data that was already extracted
  (zero fabrication, zero heuristic inference).
- Produces the first artifact in this codebase that distinguishes "eligible demand"
  from "independent demand" — the powered efficacy analysis (PR-F) now has an explicit
  population to draw from (N=18) instead of silently treating N=24 as if every member
  were an independent observation.
- Surfaced a concrete, previously undocumented leakage risk in the frozen Dev/Test
  split (organization-correlated demands split across Dev/Test), now recorded rather
  than latent.

### Negative

- N=18 is a real reduction from the N=24 eligible population, and further below the
  N=60 target — this ADR does not grow the corpus, so the powered-sample gap remains
  exactly as large as before, now measured honestly instead of masked by an inflated N.
- Three of the four independence axes the roadmap names remain open; a reader could
  reasonably ask whether N=18 itself still contains sector- or problem-duplicated
  demands. It is more scientifically honest than N=24, not a complete answer.

## Enforcement

A future PR is **non-compliant** with this ADR if it:

1. Computes or infers `requesting_organization`, or any independence-grouping key,
   from title, description, CPC, or any other text/relevance-adjacent signal.
2. Hardcodes `non_identifying_values` (or any other experiment-specific literal) inside
   `application/annotation/demand_independence.py` or any other generic backend module,
   rather than supplying it from experiment-specific tooling.
3. Adds an `independence_policy` (or equivalent) field to `EvaluationExecutionContext`,
   or implements independence filtering inside `DefaultEvaluationRunner`,
   `DefaultMatchingAdapter`, or `DefaultMatchingEngine`.
4. Merges near-duplicate organization names by similarity without a separate,
   explicitly reviewed ADR documenting the normalization rule.
5. Reports a powered efficacy result treating N=24 (or N=39) as independent
   observations without accounting for this audit's findings, once this ADR has landed.
6. Silently re-freezes `devtest_split_n13_v1.json` to fix the organization-correlation
   leak without a separate, explicitly reviewed PR.
```

- [ ] **Step 3: Update `docs/roadmap.md`**

Read the current text around line 141 (the exact gap quote) and lines 91-92 (PR-F row) first. Replace the gap description to mark the organization axis closed while keeping the other three axes explicitly open — do not delete the sentence, amend it in place so the history of what was and wasn't resolved stays legible:

Find:
```
* **Demand independence audit:** the existing Phase-2 audits (#84–#86) check whether each demand *is* a valid technology solicitation (construct eligibility), not whether the 39/24/60 demands are independent observations (same company, sector, tech family, or duplicate industrial problem). These are different questions; only the first has been done.
```

Replace with:
```
* **Demand independence audit:** the existing Phase-2 audits (#84–#86) check whether each demand *is* a valid technology solicitation (construct eligibility), not whether the 39/24/60 demands are independent observations (same company, sector, tech family, or duplicate industrial problem). **Partially closed** (ADR 0029): the company/organization axis is resolved — 6 of the 24 eligible demands are pseudoreplicates of two organizations (SMAR3TS ×5, Lacer S.A. ×3), leaving an independent corpus of N=18 (`dataset_phase2_independent_corpus_v1.json`). The sector, tech-family, and duplicate-industrial-problem axes remain open, as does growing the independent population toward `|D|=60`. ADR 0029 also surfaced a real leakage risk in the frozen Dev/Test split (organization-correlated demands currently split across Dev/Test) — not yet fixed.
```

Also update the PR-F summary row (around line 92) to reflect this: find the row's "**Open:**" clause and add the independence-audit outcome to what's now partial rather than fully open, without overstating it — read the current row's exact wording first and make the smallest edit that keeps it accurate (e.g. changing "the two gaps in §6 (family-aware evaluation, demand-independence audit)" to reflect that family-aware evaluation (ADR 0027/0028) and the organization axis of demand independence (ADR 0029) are now done, while the remaining independence axes and N=60 growth stay open). Match the row's existing terseness — this is a table cell, not prose.

- [ ] **Step 4: Run the full suite and mypy one final time**

Run: `python -m pytest backend/test -q`
Expected: all pass.

Run: `python -m mypy backend/src/main --ignore-missing-imports`
Expected: clean.

- [ ] **Step 5: Commit**

```bash
git add docs/adr/0029-demand-independence-audit-contract.md \
        docs/phase2-demand-independence-audit-protocol.md \
        docs/roadmap.md
git commit -m "docs(adr): add ADR 0029 demand-independence audit contract, update roadmap"
```

## Self-Review

**1. Spec coverage:** The roadmap's four named independence axes (company, sector, tech family, duplicate industrial problem) are each explicitly addressed: company/organization is resolved (Tasks 1-2), the other three are explicitly deferred with named reasons (ADR 0029 "What this ADR does not do," Task 3). The four demand-status distinctions the calling task named (eligible / independent / annotated / analysis-included) now have concrete referents: eligible = `dataset_phase2_eligible_corpus_n24_v1.json` (existing), independent = `dataset_phase2_independent_corpus_v1.json` (this plan), annotated/analysis-included remain for the dual-annotation-at-scale PR that should follow this one. Dev/Test isolation is not modified by this plan (Global Constraints) — the leak this audit found is documented, not silently fixed, consistent with "do not silently reinterpret existing pilot results" and "do not solve more than the selected PR scope."

**2. Placeholder scan:** No "TBD"/"add validation"/"similar to Task N" patterns. Every code block is complete and was checked against real repository files (existing `generate_eligible_corpus.py`/`check_eligible_corpus.py`, `ConstructEligibilityRubric`, real `origin_audit.json` data) before being written into this plan.

**3. Type consistency:** `DemandOrganizationObservation`/`DemandIndependenceGroupEntry`/`DemandIndependenceStatus` are defined once in Task 1 Step 3 and used with identical field names in Task 1's test file, Task 1's `derive_independence_groups`, and Task 2's two generation scripts (`e.model_dump(mode="json")`, `e.status`, `e.independence_group_id` all match the Task 1 model definition exactly).
