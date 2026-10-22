"""Orchestration of W1–W6 (BIBLIO) and the acceptance roll-up, following WORKLOAD_CONTRACTS.md and the protocol with R2.

Nothing here runs against real data unless run_benchmark.py got past the authorisation barrier.
"""
import json
import statistics
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from harness.compare import IncompleteComparison, compare_load_checks, compare_pairs, compare_records
from harness.contract import EXIT_FAIL, EXIT_INCIDENT, EXIT_PASS, IntegrityError, Store
from harness.recorder import Recorder
from harness.session import Incident, order_for, wait_for_quiet
from harness.tables import ConstraintError, canonical_rows_digest

C3_BOUND_SECONDS = 188.6
ALTERATIONS = ("change_subclass", "flip_byte", "delete_object", "swap_rows")  # the last is reported, not graded
GRADED_ALTERATIONS = ALTERATIONS[:3]


@dataclass
class Reference:
    """What the outputs are compared with: the adapter path and the versioned results (never produced by the stores)."""
    rows: dict[str, list[tuple]]
    records: list
    pairs_expected: dict[str, dict]
    pairs_fn: Callable[[list, int], dict]
    origins: tuple[int, ...] = (2006, 2022)
    load_checks_expected: dict[str, int] | None = None

    def __post_init__(self):
        if not self.records or not self.pairs_expected:
            raise ValueError("the reference must not be empty: nothing could be compared against it")
        self.rows_digest = canonical_rows_digest(self.rows)


@dataclass
class Context:
    stores: dict[str, Store]                   # {"A": ..., "B": ...}
    reference: Reference
    recorder: Recorder
    results: list = field(default_factory=list)
    sink: Path | None = None
    quiet: Callable[[], float] = wait_for_quiet
    names: dict[str, str] = field(default_factory=dict)  # unique version names per alternative


def _emit(ctx: Context, **rec) -> dict:
    ctx.results.append(rec)
    if ctx.sink:
        with ctx.sink.open("a") as f:
            f.write(json.dumps(rec, default=str) + "\n")
    return rec


class ProcedureFailure(Exception):
    """A recovery step failed after the original was dropped, with no environment cause found at that moment (R2 item 1)."""

    def __init__(self, outputs: dict) -> None:
        super().__init__(json.dumps(outputs, default=str))
        self.outputs = outputs


def _run(ctx: Context, workload: str, alt: str, rep: int, run_kind: str, body: Callable[[], tuple[dict, dict]],
         check_exceptions: tuple[type[Exception], ...] = ()) -> dict:
    """status ok / check_failed / incident, decided by exception type only (contract 'Common rules')."""
    order = 1 if order_for(rep)[0] == alt else 2
    before = len(ctx.recorder.entries)
    start_load = None
    try:
        if run_kind == "warm":
            start_load = ctx.quiet()
        outputs, checks = body()
        status = "ok" if all(checks.values()) else "check_failed"
        incident = None
    except Incident as exc:
        outputs, checks, status, incident = {}, {}, "incident", str(exc)
    except check_exceptions as exc:
        outputs, checks, status, incident = getattr(exc, "outputs", {"error": repr(exc)}), {}, "check_failed", None
    except IncompleteComparison as exc:
        outputs, checks, status, incident = {"error": repr(exc)}, {}, "check_failed", None  # reference is validated non-empty
    except Exception as exc:  # noqa: BLE001 - anything else is outside the alternative's contract
        outputs, checks, status, incident = {}, {}, "incident", repr(exc)
    return _emit(ctx, workload=workload, alternative=alt, repetition=rep, run_kind=run_kind, order_in_repetition=order,
                 status=status, timings=[vars(e) for e in ctx.recorder.entries[before:]], outputs=outputs, checks=checks,
                 incident=incident, start_load=start_load)


def _sec(ctx, workload, alt, phase, label, run_kind, rep):
    order = 1 if order_for(rep)[0] == alt else 2
    return ctx.recorder.section(workload=workload, alternative=alt, phase=phase, label=label, run_kind=run_kind,
                                repetition=rep, order_in_repetition=order)


def w1_prepare(ctx: Context, alt: str, rep: int, run_kind: str, version: str) -> dict:
    store, ref = ctx.stores[alt], ctx.reference

    def body():
        with _sec(ctx, "W1", alt, "prepare", "prepare", run_kind, rep):
            made = store.prepare(version, ref.rows)
        checks = {"logical_equal": store.logical_digest(version) == ref.rows_digest}
        if ref.load_checks_expected is not None and hasattr(store, "load_checks"):
            checks.update({f"load_{k}": v for k, v in compare_load_checks(store.load_checks(version), ref.load_checks_expected).items()})
        return {"manifest_digest": made.manifest_digest, "size_bytes": store.size_bytes(version),
                "verified": store.verify(version) == made}, checks
    return _run(ctx, "W1", alt, rep, run_kind, body, (ConstraintError, IntegrityError))


def w2_report(ctx: Context, alt: str, rep: int, run_kind: str, version: str, workload: str = "W2", store: Store | None = None) -> dict:
    store, ref = store or ctx.stores[alt], ctx.reference

    def body():
        mark = len(ctx.recorder.entries)
        with _sec(ctx, workload, alt, "execute", "read", run_kind, rep):
            records = store.read_records(version)
        with _sec(ctx, workload, alt, "execute", "compute", run_kind, rep):
            result = {str(o): ref.pairs_fn(records, o) for o in ref.origins}
        total = sum(e.seconds for e in ctx.recorder.entries[mark:])
        pairs_ok = compare_pairs(ref.pairs_expected, result)
        return {"total_seconds": total}, {"pairs_equal": all(pairs_ok.values()),
                                          "records_equal": compare_records(ref.records, records).equal}
    return _run(ctx, workload, alt, rep, run_kind, body, (IntegrityError,))


def w3_verify(ctx: Context, alt: str, rep: int, run_kind: str, version: str, recorded: str) -> dict:
    store = ctx.stores[alt]

    def body():
        with _sec(ctx, "W3", alt, "execute", "verify", run_kind, rep):
            got = store.verify(version)
        return {"digest": got.manifest_digest}, {"digest_unchanged": got.manifest_digest == recorded}
    return _run(ctx, "W3", alt, rep, run_kind, body, (IntegrityError,))


def w4_alteration(ctx: Context, alt: str, kind: str, rep: int = 1) -> dict:
    store = ctx.stores[alt]
    version = f"w4_{alt}_{kind}"

    def body():
        store.prepare(version, ctx.reference.rows)
        store.alter(version, kind)
        detected, error = False, None
        with _sec(ctx, "W4", alt, "execute", f"detect_{kind}", "warm", rep):
            try:
                store.verify(version)
            except IntegrityError as exc:
                detected = True
            except Exception as exc:  # a crash is not a controlled detection (contract W4)
                error = repr(exc)
        outputs = {"kind": kind, "detected": detected, "report_before_detection": False, "unexpected_exception": error}
        return outputs, ({f"detected_{kind}": detected} if kind in GRADED_ALTERATIONS else {})
    try:
        return _run(ctx, "W4", alt, rep, "warm", body)
    finally:
        try:
            store.drop(version)
        except Exception:  # noqa: BLE001 - cleanup of a throwaway
            pass


def w5_rebuild(ctx: Context, alt: str, prev: str, rep: int = 1) -> dict:
    store, ref = ctx.stores[alt], ctx.reference
    recorded = store.verify(prev).manifest_digest  # recorded before anything starts
    nxt = f"w5_{alt}_next"

    def body():
        rows = {k: list(v) for k, v in ref.rows.items()}
        first = rows["ipc_entry"][0]
        other = next(r[0] for r in rows["ipc_subclass"] if r[0] != first[2])
        rows["ipc_entry"][0] = (*first[:2], other, *first[3:])
        with _sec(ctx, "W5", alt, "prepare", "rebuild", "warm", rep):
            made = store.prepare(nxt, rows)
        changed = canonical_rows_digest(rows)
        checks = {"previous_unchanged": store.verify(prev).manifest_digest == recorded,
                  "next_verifies": store.verify(nxt) == made,
                  "logical_differs": store.logical_digest(nxt) != store.logical_digest(prev),
                  "logical_next_equals_changed_rows": store.logical_digest(nxt) == changed}
        return {"next_digest": made.manifest_digest}, checks
    try:
        return _run(ctx, "W5", alt, rep, "warm", body, (IntegrityError, ConstraintError))
    finally:
        try:
            store.drop(nxt)
        except Exception:  # noqa: BLE001
            pass


def w6_recovery(ctx: Context, alt: str, tmp: Path, rep: int = 1) -> list[dict]:
    """W6a then W6b (R2). Each on a freshly prepared version; backups timed; failure after the drop is a check failure."""
    store, ref, out = ctx.stores[alt], ctx.reference, []
    tmp.mkdir(parents=True, exist_ok=True)

    def prepared(name):
        made = store.prepare(name, ref.rows)
        dump = tmp / f"{alt}_{name}.bak"
        with _sec(ctx, "W6", alt, "execute", "backup", "warm", rep):
            store.backup(name, dump)
        return made, dump

    def a():
        made, dump = prepared(f"w6a_{alt}")
        with _sec(ctx, "W6a", alt, "execute", "restore_new", "warm", rep):
            other, version = store.restore_new(dump, f"w6a_{alt}")
        try:
            with _sec(ctx, "W6a", alt, "execute", "verify_restored_new", "warm", rep):
                got = other.verify(version)
            records = other.read_records(version)
            result = {str(o): ref.pairs_fn(records, o) for o in ref.origins}
            checks = {"digest_equal": got.manifest_digest == made.manifest_digest,
                      "original_unchanged": store.verify(f"w6a_{alt}").manifest_digest == made.manifest_digest,
                      "pairs_equal": all(compare_pairs(ref.pairs_expected, result).values()),
                      "records_equal": compare_records(ref.records, records).equal}
        finally:
            other.dispose()
        return {"digest": got.manifest_digest}, checks

    def b():
        made, dump = prepared(f"w6b_{alt}")
        name = f"w6b_{alt}"
        store.drop(name)  # from here the original is gone: a failure is the procedure's, unless an environment cause is found now
        state = {"original_dropped": True, "phase": "restore_in_place"}
        try:
            with _sec(ctx, "W6b", alt, "execute", "restore_in_place", "warm", rep):
                store.restore(dump, name)
            state["phase"] = "verify_restored_in_place"
            with _sec(ctx, "W6b", alt, "execute", "verify_restored_in_place", "warm", rep):
                got = store.verify(name)
            state["phase"] = "report_on_restored"
            records = store.read_records(name)
            result = {str(o): ref.pairs_fn(records, o) for o in ref.origins}
        except Exception as exc:  # noqa: BLE001 - classified below with the evidence available at this moment
            problems = store.environment_problems(2 * dump.stat().st_size)
            if problems:
                raise Incident(f"W6b failed in {state['phase']} after the drop with environment evidence {problems}: {exc!r}") from exc
            raise ProcedureFailure({**state, "environment_problems": [], "error": repr(exc)}) from exc
        return {"digest": got.manifest_digest, **state}, {"digest_equal": got.manifest_digest == made.manifest_digest,
                                                          "pairs_equal": all(compare_pairs(ref.pairs_expected, result).values()),
                                                          "records_equal": compare_records(ref.records, records).equal}
    # an exception after the original was dropped is a procedure failure (R2 item 1), never an incident
    out.append(_run(ctx, "W6a", alt, rep, "warm", a, (IntegrityError,)))
    out.append(_run(ctx, "W6b", alt, rep, "warm", b, (ProcedureFailure,)))
    for n in (f"w6a_{alt}", f"w6b_{alt}"):
        try:
            store.drop(n)
        except Exception:  # noqa: BLE001
            pass
    return out


def run_biblio_session(ctx: Context, tmp: Path, repetitions: int = 5, alternatives: tuple[str, ...] = ("A", "B")) -> list[dict]:
    """One `first_run_after_start` then `repetitions` warm runs per operation, alternating A/B; then W4-W6.

    The first runs of A and B are recorded but never compared with each other; to compare initial performance, run this
    in separate fresh sessions with `alternatives=("A",)` and `("B",)` (R1 section 2).
    """
    main = {alt: f"main_{alt}" for alt in alternatives}
    for alt in alternatives:
        w1_prepare(ctx, alt, 0, "first_run_after_start", main[alt])
    for rep in range(1, repetitions + 1):
        for alt in [a for a in order_for(rep) if a in alternatives]:
            name = f"w1warm_{alt}_{rep}"
            w1_prepare(ctx, alt, rep, "warm", name)
            ctx.stores[alt].drop(name)
    recorded = {alt: ctx.stores[alt].verify(main[alt]).manifest_digest for alt in alternatives}
    for alt in alternatives:
        w2_report(ctx, alt, 0, "first_run_after_start", main[alt])
        w3_verify(ctx, alt, 0, "first_run_after_start", main[alt], recorded[alt])
    for rep in range(1, repetitions + 1):
        for alt in [a for a in order_for(rep) if a in alternatives]:
            w2_report(ctx, alt, rep, "warm", main[alt])
            w3_verify(ctx, alt, rep, "warm", main[alt], recorded[alt])
    for alt in alternatives:
        for kind in ALTERATIONS:
            w4_alteration(ctx, alt, kind)
        w5_rebuild(ctx, alt, main[alt])
        w6_recovery(ctx, alt, tmp)
    return ctx.results


def evaluate(results: list[dict], alternatives: tuple[str, ...] = ("A", "B")) -> tuple[int, dict]:
    """Roll-up of protocol section 5. C3 needs 5 valid warm W2 runs and uses max(); any incident gives exit code 3 until repeated."""
    table: dict[str, dict] = {}
    for alt in alternatives:
        mine = [r for r in results if r["alternative"] == alt]

        def passed(workload: str) -> bool:
            runs = [r for r in mine if r["workload"] == workload and r["status"] != "incident"]
            return bool(runs) and all(r["status"] == "ok" for r in runs)

        w4 = {r["outputs"].get("kind"): r["outputs"].get("detected") for r in mine if r["workload"] == "W4" and r["status"] != "incident"}
        totals = [r["outputs"]["total_seconds"] for r in mine if r["workload"] == "W2" and r["run_kind"] == "warm"
                  and r["status"] != "incident" and "total_seconds" in r["outputs"]]
        table[alt] = {
            "C1": passed("W1") and passed("W2"),
            "C2": all(w4.get(k) is True for k in GRADED_ALTERATIONS),
            "C3": len(totals) == 5 and max(totals) <= C3_BOUND_SECONDS,
            "C3_stats": {"n": len(totals), "min": min(totals, default=None),
                         "median": statistics.median(totals) if totals else None, "max": max(totals, default=None)},
            "C4": passed("W6a") and passed("W6b"),
            "C5": passed("W5"),
            "W7_ids_order": passed("W7") if any(r["workload"] == "W7" for r in mine) else None,
            "incidents": sum(1 for r in mine if r["status"] == "incident"),
        }
    if any(t["incidents"] for t in table.values()):
        return EXIT_INCIDENT, table
    graded = all(t[c] for t in table.values() for c in ("C1", "C2", "C3", "C4", "C5")) and all(t["W7_ids_order"] is not False for t in table.values())
    return (EXIT_PASS if graded else EXIT_FAIL), table
