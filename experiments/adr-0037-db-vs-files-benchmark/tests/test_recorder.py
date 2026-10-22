import pytest
from harness.recorder import Recorder, materially_different


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def kw(**o):
    return {"workload": "W2", "alternative": "A", "phase": "execute", "label": "report", "run_kind": "warm",
            "repetition": 1, "order_in_repetition": 1, **o}


def test_shouldRecordElapsedSecondsWithItsPhaseAndRunKind():
    clock = Clock(); rec = Recorder(clock)
    with rec.section(**kw(phase="prepare", run_kind="first_run_after_start")):
        clock.t = 2.5
    e = rec.entries[0]
    assert (e.seconds, e.phase, e.run_kind) == (2.5, "prepare", "first_run_after_start")


def test_shouldRefuseNestedSectionsBecauseTheyDoubleCount():
    rec = Recorder(Clock())
    with rec.section(**kw()), pytest.raises(RuntimeError):
        with rec.section(**kw(label="inner")):
            pass


def test_shouldSummariseOnlyWarmRunsOfTheSameCell():
    clock = Clock(); rec = Recorder(clock)
    for dur, kind in [(9, "first_run_after_start"), (1, "warm"), (3, "warm"), (2, "warm")]:
        with rec.section(**kw(run_kind=kind)):
            clock.t += dur
    with rec.section(**kw(phase="prepare")):
        clock.t += 100
    s = rec.summary("W2", "A", "execute", "report")
    assert s == {"warm_runs": 3, "min": 1, "median": 2, "max": 3}


def test_shouldCallDifferenceMaterialOnlyWhenRangesAreDisjointAndMediansDifferTwofold():
    a = {"warm_runs": 5, "min": 1.0, "median": 1.1, "max": 1.2}
    assert materially_different(a, {"warm_runs": 5, "min": 2.4, "median": 2.5, "max": 2.6})
    assert not materially_different(a, {"warm_runs": 5, "min": 1.3, "median": 1.4, "max": 1.5})  # disjoint, under 2x
    assert not materially_different(a, {"warm_runs": 5, "min": 1.1, "median": 2.6, "max": 3.0})  # 2x, overlapping
    assert not materially_different(a, {"warm_runs": 0})
