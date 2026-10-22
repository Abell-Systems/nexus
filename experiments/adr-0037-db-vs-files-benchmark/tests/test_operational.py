import os
from dataclasses import dataclass

import numpy as np
import pytest
from harness.operational import NumpyRetriever, PgRetriever, p95, w7_operational
from harness.recorder import Recorder
from harness.workloads import Context


@dataclass
class D:
    demand_id: str


class FakeNumpy:
    """Exact cosine like production's NumpyDenseRetriever: float32 matvec, clip, (cos+1)/2, round(6), ties by id."""

    def __init__(self, ids, matrix, eligible):
        self.ids, self.matrix, self.eligible = ids, matrix, set(eligible)

    def retrieve(self, demand, vector, limit):
        sims = np.clip(self.matrix @ vector, -1, 1)
        scored = sorted(((self.ids[i], round((float(sims[i]) + 1) / 2, 6)) for i in self.eligible), key=lambda t: (-t[1], t[0]))
        return scored[:limit]


def corpus(n=300, dim=16, seed=1):
    rng = np.random.default_rng(seed)
    m = rng.normal(size=(n, dim)).astype(np.float32)
    m /= np.linalg.norm(m, axis=1, keepdims=True)
    return [f"ES{i:05d}A1" for i in range(n)], m, [i for i in range(n) if i % 7 != 0]


def queries(k=6, dim=16):
    rng = np.random.default_rng(2)
    q = rng.normal(size=(k, dim)).astype(np.float32)
    q /= np.linalg.norm(q, axis=1, keepdims=True)
    return [D(f"D{i}") for i in range(k)], {f"D{i}": q[i] for i in range(k)}


def test_shouldComputeP95WithTheDefaultQuantileMethod():
    assert p95(list(range(1, 101))) == pytest.approx(95.95)


def test_shouldGradeIdsAndOrderAndReportScoreCountsAndPerDemandDiagnostics():
    ids, m, el = corpus()
    demands, vecs = queries()
    same = FakeNumpy(ids, m, el)
    ctx = Context(stores={}, reference=None, recorder=Recorder(), quiet=lambda: 0.0)  # type: ignore[arg-type]
    out = w7_operational(ctx, {"A": same, "B": FakeNumpy(ids, m, el)}, demands, vecs, reps=3)
    assert [r["status"] for r in out] == ["ok", "ok"]
    assert out[0]["outputs"]["parity"]["cases"] == 12 and out[0]["outputs"]["observations"] == 18
    assert set(out[0]["outputs"]["per_demand_diagnostic"]) == {"D0", "D1", "D2", "D3", "D4", "D5"}


def test_shouldFailTheCheckWhenAnOrderDiffers():
    ids, m, el = corpus()
    demands, vecs = queries()

    class Reversed(FakeNumpy):
        def retrieve(self, demand, vector, limit):
            return list(reversed(super().retrieve(demand, vector, limit)))
    ctx = Context(stores={}, reference=None, recorder=Recorder(), quiet=lambda: 0.0)  # type: ignore[arg-type]
    out = w7_operational(ctx, {"A": FakeNumpy(ids, m, el), "B": Reversed(ids, m, el)}, demands, vecs, reps=2)
    assert out[0]["status"] == "check_failed"


def test_shouldHavePgvectorAgreeWithExactNumpyOnIdsAndOrder():
    dsn = os.environ.get("NEXUS_BENCH_PG_DSN")
    if not dsn:
        pytest.skip("NEXUS_BENCH_PG_DSN not set")
    ids, m, el = corpus()
    demands, vecs = queries()
    pg = PgRetriever(dsn, f"w7_{os.getpid()}", ids, m, el)
    try:
        ctx = Context(stores={}, reference=None, recorder=Recorder(), quiet=lambda: 0.0)  # type: ignore[arg-type]
        out = w7_operational(ctx, {"A": pg, "B": FakeNumpy(ids, m, el)}, demands, vecs, reps=2)
        assert out[0]["checks"]["ids_order_identical"], out[0]["outputs"]["parity"]
        assert out[0]["outputs"]["parity"]["scores_within_one_unit"] == out[0]["outputs"]["parity"]["cases"]
    finally:
        pg.close()


def test_shouldApplyTheGateBeforeEveryObservationAndKeepItsLoad():
    ids, m, el = corpus()
    demands, vecs = queries(k=3)
    calls = []

    def quiet():
        calls.append(1)
        return 0.25
    ctx = Context(stores={}, reference=None, recorder=Recorder(), quiet=quiet)  # type: ignore[arg-type]
    out = w7_operational(ctx, {"A": FakeNumpy(ids, m, el), "B": FakeNumpy(ids, m, el)}, demands, vecs, reps=4)
    assert len(calls) == 3 * 4 * 2  # demands x repetitions x alternatives
    loads = out[0]["outputs"]["load_before_each_observation"]
    assert all(v == [0.25] * 4 for v in loads.values())


def test_shouldEndW7AsAnIncidentWhenTheGateFails():
    from harness.session import Incident
    ids, m, el = corpus()
    demands, vecs = queries(k=2)

    def noisy():
        raise Incident("load 3.0")
    ctx = Context(stores={}, reference=None, recorder=Recorder(), quiet=noisy)  # type: ignore[arg-type]
    out = w7_operational(ctx, {"A": FakeNumpy(ids, m, el), "B": FakeNumpy(ids, m, el)}, demands, vecs, reps=2)
    assert [r["status"] for r in out] == ["incident", "incident"]


class _Asset:
    def __init__(self, i):
        self.patent = i


class _Result:
    def __init__(self, ok):
        self.is_eligible = ok


def test_shouldReturnTheSharedEligibleSetWhenPolicyIgnoresTheDemand():
    from harness.operational import eligible_ids

    class P:
        def evaluate(self, patent, demand):
            return _Result(patent % 2 == 0)
    assert eligible_ids(P(), [_Asset(i) for i in range(6)], [D("a"), D("b")]) == [0, 2, 4]


def test_shouldStopWhenEligibilityDependsOnTheDemand():
    from harness.operational import eligible_ids

    class P:
        def evaluate(self, patent, demand):
            return _Result(demand.demand_id == "a" or patent == 0)
    with pytest.raises(ValueError):
        eligible_ids(P(), [_Asset(i) for i in range(4)], [D("a"), D("b")])


def test_shouldAgreeWithTheProductionPolicyThatItIgnoresTheDemand():
    """The real policy is demand-independent (retrieval spec A1): proven here on a small mixed set, not assumed."""
    from domain.models.patent import PatentDocument
    from infrastructure.matching.operational_corpus import operational_eligibility_policy
    from eligible_support import assets_for_policy
    from harness.operational import eligible_ids
    assets = assets_for_policy()
    assert eligible_ids(operational_eligibility_policy(), assets, [D("x"), D("y"), D("z")]) == [0, 3]
