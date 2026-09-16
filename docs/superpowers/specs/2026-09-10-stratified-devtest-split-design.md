# Stratified Dev/Test Split — Design

**Status:** Proposed. Resolves #79 (Dev/Test split infrastructure), building on the
now-frozen sector assignments (#92) and consistent with ADR 0026's experiment/domain
boundary (established in #87 and exercised throughout #88–#92).

## Why this exists

`docs/empirical-study-protocol.md` §3 requires demands to be partitioned into a
Development Split (`D_dev`) and Test Split (`D_test`), stratified by sector, with
`D_dev` used exclusively for hyperparameter tuning (ADR 0016's `α, β, γ` and
`S_best_single`) and `D_test` held out untouched until confirmatory evaluation. This
infrastructure does not exist yet. #79's own review thread (accepted before this spec)
fixed three requirements this design must satisfy:

- **A.** The dev/test allocation rule per stratum must be a fully deterministic,
  explicitly stated rule — not "~40/60" left to whatever `round()` happens to do —
  including a stated behavior for strata too small to split cleanly (with the current
  N=13 sector-coverable population, per-stratum counts are `{1, 2, 3, 3, 4}` — this is
  the common case, not a rare edge).
- **B.** No-leakage must be an interface property, not only a test: the future tuning
  component must be constructible only from `D_dev`, the future confirmatory-evaluation
  component only from `D_test`; no API accepts the undivided corpus; the frozen
  partition artifact is the sole source of truth for membership.
- **C.** Sector must already be a frozen, formalized attribute before stratification
  runs — satisfied: `sector_assignments_n24_v1.json` (#92) is the input, restricted to
  its 13 `assignments` entries. The 11 `no_sector_coverage` entries (#90/#91) are
  categorically excluded from this population, not merely "small."

## Architecture

Per ADR 0026: the split *mechanism* is generic and lives in `backend/src/main`; the
WPI-specific *instantiation* (which corpus, which seed, which fraction, whose sector
labels) lives entirely in `experiments/wpi-demand-patent-matching/`. Nothing in
`backend/src` may reference a WPI sector name, `N=13`, a specific seed value, or `0.40`
as a default — these are always caller-supplied parameters.

```text
backend/src/main
  domain/models/evaluation.py       — DevPartition, TestPartition (frozen data contracts)
  application/evaluation/stratified_split.py  — stratified_split() (the algorithm),
                                                 StratifiedSplitResult, StratumCount

experiments/wpi-demand-patent-matching
  config/devtest_split_v1.json      — dev_fraction, seed, stratum_key, input hash pins
  data/devtest_split_n13_v1.json    — frozen dev/test membership + manifest + sha256
  checks/generate_devtest_split.py  — instantiates stratified_split() against #92
  checks/check_devtest_split.py     — verifies the frozen instantiation
```

## Components

### `domain/models/evaluation.py`: `DevPartition` / `TestPartition`

Two distinct, frozen (pydantic `ConfigDict(frozen=True)`) types, each holding only
`demand_ids: tuple[str, ...]` (validated non-empty, unique). They are deliberately
**not** two fields on one `SplitResult` class that a careless caller could destructure
past: a future tuning component's constructor type-hints `dev: DevPartition` and
literally cannot accept a `TestPartition` or an undivided corpus in its place; the
future confirmatory-evaluation component is the mirror image. This is #79 review
requirement B's "interface property" — enforced by the type system for whatever
consumes these types next (ADR 0016 and beyond, out of this issue's scope), not by a
convention someone has to remember.

`StratifiedSplitResult` wraps `dev: DevPartition`, `test: TestPartition`, and
`per_stratum_counts: tuple[StratumCount, ...]` (for audit — not itself a membership
source of truth). Unlike `DevPartition`/`TestPartition`, it lives in
`application/evaluation/stratified_split.py`, not `domain/models/evaluation.py`: per
ADR 0026's own domain/application split (`domain` = structural types with no known
values; `application` = generic mechanism), `StratifiedSplitResult` exists only to
carry `stratified_split()`'s output and isn't a structural contract any other
component is meant to depend on — so it belongs beside the mechanism that returns it,
not beside the types (`DevPartition`/`TestPartition`) a future consumer's constructor
is meant to type-hint against. A future component must be constructed from
`.dev`/`.test` individually, never from `StratifiedSplitResult` as a whole — that type
exists only as the algorithm's return value and the thing frozen to the
content-addressed artifact. `per_stratum_counts` is a tuple of frozen `StratumCount`
models rather than `dict[str, dict[str, int]]`: pydantic's `frozen=True` blocks
reassigning a model field but not mutating a dict *value* in place, so a plain dict
field would not have been genuinely immutable despite the model being "frozen".

### `application/evaluation/stratified_split.py`: `stratified_split()`

```text
def stratified_split(
    items: Sequence[T],
    stratum_key: Callable[[T], str],
    item_id: Callable[[T], str],
    dev_fraction: float,
    seed: int,
) -> StratifiedSplitResult
```

Generic over `T` — the WPI caller passes sector-assignment entries and
`stratum_key=lambda e: e.sector_code`, `item_id=lambda e: e.demand_id`; nothing here
assumes what `T` is.

**Allocation policy with feasibility floor** (#79 review requirement A; named
"allocation policy," not "rounding policy," since the floor is load-bearing, not
incidental — per review). For each stratum of size $n_s$:

1. If $n_s = 1$: the single item is assigned entirely to Test. Dev count = 0. (No
   partition of a singleton can represent it on both sides without duplication.)
2. If $n_s \ge 2$: compute the target Dev count using **round-half-up**, defined
   exactly (Python's `round()` is banker's-rounding and must not be used implicitly):
   $$d_s = \left\lfloor 0.40 \, n_s + 0.5 \right\rfloor$$
   (`dev_fraction` generalizes the `0.40` here — the formula is
   $d_s = \lfloor \text{dev\_fraction} \cdot n_s + 0.5 \rfloor$).
   Then apply the floor: if $d_s = 0$, set $d_s = 1$; if $d_s = n_s$, set
   $d_s = n_s - 1$. This guarantees both sides of every stratum with $n_s \ge 2$ are
   non-empty, taking precedence over the exact `dev_fraction` target when the two
   conflict (per the accepted review decision).
3. Which $d_s$ specific items land in Dev (vs. the remaining $n_s - d_s$ in Test) is
   decided by `random.Random(f"{seed}:{stratum}").shuffle()` of the stratum's items
   (in `item_id` sort order, for determinism independent of input iteration order),
   taking the first $d_s$ post-shuffle as Dev. The per-stratum seed is derived from
   both the global `seed` and the stratum name -- not the bare global `seed` -- so
   that strata of equal size get decorrelated (not identical) shuffle permutations,
   while staying fully deterministic (same seed + same stratum name -> same
   permutation, every time).

**This is a property of `stratified_split()` itself, enforced by backend unit tests
against synthetic strata** (#79 review requirement 2) — not only checked against the
one real WPI instantiation by `check_devtest_split.py`. The experimental check
verifies the *instantiation* (right input, right seed, right output); the backend
tests verify the *algorithm* (right policy, for any input shape).

**`stratum_key` / `item_id` contract** (#79 review requirement 3, explicit rather than
accidental):

- If `stratum_key(item)` returns `None` or an empty string for any item: raises
  `ValueError` naming the offending item's `item_id`. A missing/null stratum is not
  silently grouped into an "unknown" bucket.
- Duplicate `item_id` values across `items`: raises `ValueError`. Membership integrity
  cannot be established over a multiset.
- `items` empty, or `dev_fraction` outside `(0, 1)`, or `seed` not an int: raises
  `ValueError` / `TypeError` at the boundary, before any allocation logic runs.
- A stratum can never be *empty* by construction (it is derived by grouping `items`
  by `stratum_key` — a key with zero members doesn't appear as a stratum at all), so
  "empty stratum" is not a distinct runtime case to guard, only worth stating as a
  non-issue here for the record.

### Experiment instantiation

- `config/devtest_split_v1.json`: `dev_fraction: 0.40`, `seed: 42`, declares the input
  as `experiments/wpi-demand-patent-matching/data/sector_assignments_n24_v1.json` +
  its sha256 (hash-pinned, same pattern as every prior config in this chain).
- `checks/generate_devtest_split.py`: loads `sector_assignments_n24_v1.json`, verifies
  its sidecar, **takes only the `assignments` list — asserts `no_sector_coverage` is
  never read for membership** — calls `stratified_split()` with
  `stratum_key=sector_code, item_id=demand_id`, writes the frozen artifact.
- `data/devtest_split_n13_v1.json` + `.sha256` + `.manifest.json`: `dev: [demand_id,
  ...]`, `test: [demand_id, ...]`, `per_stratum_counts`, `manifest.derived_from`
  pinning `assignments_sha256` and the config's own sha256, `dev_fraction`, `seed`
  recorded in the manifest (observability, not re-derivation — the check recomputes
  from the config, doesn't trust the manifest's copy as authoritative).
- `checks/check_devtest_split.py`: sidecars valid; `dev ∪ test` equals exactly the 13
  `assignments` `demand_id`s (**explicitly asserts no `no_sector_coverage` id is
  present in either**); `dev ∩ test = ∅`; per-stratum counts match the floor-policy
  table for `{1,2,3,3,4}` (`{0,1},{1,1},{1,2},{1,2},{2,2}` dev/test pairs); re-running
  `generate_devtest_split.py` reproduces the frozen artifact byte-for-byte.

## Testing

**Backend unit tests first** (`backend/test/unit/application/evaluation/test_stratified_split.py`),
synthetic strata only, no WPI names:

- No overlap between `dev`/`test`; exact union equals input `item_id`s.
- Determinism: same `items`/`seed` → identical `StratifiedSplitResult`.
- Different `seed` → a different (not necessarily fully disjoint, but different)
  within-stratum selection, for at least one stratum size where multiple selections
  are possible ($n_s \ge 3$).
- Full floor-policy table: $n_s \in \{1, 2, 3, 4, 5, 10\}$ against `dev_fraction=0.40`
  produce the exact expected `(dev, test)` counts. Neither floor branch fires for
  `0.40` at these sizes (by construction of the formula), so the floor branches
  themselves are proven with two additional, deliberately chosen fractions: `0.1`
  with $n_s=2$ (formula alone gives $d_s=0$; floor must bump it to `1`) and `0.9`
  with $n_s=2$ (formula alone gives $d_s=n_s=2$; floor must reduce it to `1`) — both
  asserted directly, not inferred from the `0.40` table.
- `stratum_key` returning `None`/`""` for one item → `ValueError`.
- Duplicate `item_id` → `ValueError`.
- `DevPartition` and `TestPartition` are distinct types (a type-level/isinstance
  assertion, not just value equality) — a regression here is exactly what would
  silently reopen the leakage risk requirement B exists to close.

**Experimental check** (`check_devtest_split.py`): instantiation correctness against
the real #92 artifact, as described above — not a re-test of the algorithm's general
properties, which belong to the backend suite.

## Non-goals

- Does not implement ADR 0016's `α, β, γ` tuning or `S_best_single` selection — those
  are future consumers of `DevPartition`, out of scope here.
- Does not implement the confirmatory Wilcoxon evaluation — a future consumer of
  `TestPartition`.
- Does not modify `sector_assignments_n24_v1.json` (#92), `phase2_sector_taxonomy_v1`
  (#83), or any earlier frozen artifact in this chain.
- Does not touch ADR 0018 / temporal pool construction.
