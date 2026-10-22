"""W7: operational retrieval. A = pgvector exact scan (as in spike P2), B = the current numpy path. Contract: WORKLOAD_CONTRACTS.md W7."""
import statistics
from dataclasses import dataclass
from typing import Protocol

import numpy as np
import psycopg
from pgvector.psycopg import register_vector

from harness.session import Incident, order_for
from harness.workloads import Context, _emit, _sec

SQL = """SELECT a.publication_number, round((((1 - (e.embedding <=> %s))+1)/2)::numeric, 6)::float8 AS score
FROM {s}.asset_embedding e JOIN eligible USING(asset_id) JOIN {s}.asset a USING(asset_id)
ORDER BY score DESC, a.publication_number ASC LIMIT %s"""


class Retriever(Protocol):
    def retrieve(self, demand, vector: np.ndarray, limit: int) -> list[tuple[str, float]]: ...


@dataclass
class NumpyRetriever:
    """B: the current path (`NumpyDenseRetriever`) called exactly as production calls it."""
    inner: object
    method: object  # RetrievalMethod.SEMANTIC

    def retrieve(self, demand, vector, limit):
        return [(c.publication_id, c.retrieval_scores[self.method]) for c in self.inner.retrieve(demand, limit=limit)]


class PgRetriever:
    """A: exact cosine scan in SQL over the eligible assets; eligibility stays in code (ADR 0037 §3.2) and is loaded as a temp table."""

    def __init__(self, dsn: str, schema: str, publication_ids: list[str], matrix: np.ndarray, eligible: list[int]) -> None:
        self.conn = psycopg.connect(dsn, autocommit=True)
        self.schema = schema
        self.conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        register_vector(self.conn)
        c = self.conn
        c.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE; CREATE SCHEMA {schema}")
        c.execute(f"CREATE TABLE {schema}.asset(asset_id int PRIMARY KEY, publication_number text UNIQUE NOT NULL)")
        c.execute(f"CREATE TABLE {schema}.asset_embedding(asset_id int PRIMARY KEY REFERENCES {schema}.asset, embedding vector({matrix.shape[1]}) NOT NULL)")
        with c.cursor() as cur:
            with cur.copy(f"COPY {schema}.asset FROM STDIN") as cp:
                for i, p in enumerate(publication_ids):
                    cp.write_row((i, p))
            with cur.copy(f"COPY {schema}.asset_embedding FROM STDIN (FORMAT BINARY)") as cp:
                cp.set_types(["int4", "vector"])
                for i in range(len(publication_ids)):
                    cp.write_row((i, matrix[i]))
        c.execute("ANALYZE")
        c.execute("CREATE TEMP TABLE eligible(asset_id int PRIMARY KEY)")
        with c.cursor() as cur, cur.copy("COPY eligible FROM STDIN") as cp:
            for i in eligible:
                cp.write_row((i,))

    def retrieve(self, demand, vector, limit):
        return [(p, s) for p, s in self.conn.execute(SQL.format(s=self.schema), (vector, limit)).fetchall()]

    def close(self) -> None:
        self.conn.execute(f"DROP SCHEMA IF EXISTS {self.schema} CASCADE")
        self.conn.close()


def p95(xs: list[float]) -> float:
    return statistics.quantiles(xs, n=20)[-1]


def w7_operational(ctx: Context, retrievers: dict[str, Retriever], demands: list, vectors: dict[str, np.ndarray],
                   reps: int = 20, limits: tuple[int, ...] = (5, 100)) -> list[dict]:
    """Parity of ids and order (graded), then `reps` warm observations per demand at limit 5, alternating A/B per demand (R2)."""
    import time
    out = []
    alts = tuple(retrievers)
    parity = {"cases": 0, "ids_order_identical": 0, "scores_strict_equal": 0, "scores_within_one_unit": 0}
    if len(alts) == 2:
        a, b = (retrievers[x] for x in alts)
        for d in demands:
            for limit in limits:
                ra, rb = a.retrieve(d, vectors[d.demand_id], limit), b.retrieve(d, vectors[d.demand_id], limit)
                parity["cases"] += 1
                same = [x[0] for x in ra] == [x[0] for x in rb]
                parity["ids_order_identical"] += same
                if same:
                    units = [round(abs(x[1] - y[1]) * 1e6) for x, y in zip(ra, rb, strict=True)]
                    parity["scores_strict_equal"] += all(u == 0 for u in units)
                    parity["scores_within_one_unit"] += all(u <= 1 for u in units)
    obs: dict[str, dict[str, list[float]]] = {alt: {d.demand_id: [] for d in demands} for alt in alts}
    loads: dict[str, dict[str, list[float]]] = {alt: {d.demand_id: [] for d in demands} for alt in alts}
    try:
        for d in demands:
            for rep in range(1, reps + 1):
                for alt in [x for x in (order_for(rep) if len(alts) == 2 else alts) if x in alts]:
                    loads[alt][d.demand_id].append(ctx.quiet())  # R2: the gate precedes every warm observation, its load is kept
                    t = time.perf_counter()
                    with _sec(ctx, "W7", alt, "execute", "retrieve", "warm", rep):
                        retrievers[alt].retrieve(d, vectors[d.demand_id], 5)
                    obs[alt][d.demand_id].append(time.perf_counter() - t)
    except Incident as exc:
        return [_emit(ctx, workload="W7", alternative=alt, repetition=0, run_kind="warm", order_in_repetition=0, status="incident",
                      timings=[], outputs={}, checks={}, incident=str(exc), start_load=None) for alt in alts]
    for alt in alts:
        pooled = [x for v in obs[alt].values() for x in v]
        per_demand = {k: {"median": statistics.median(v), "p95": p95(v)} for k, v in obs[alt].items() if len(v) >= 2}
        graded_ok = len(alts) < 2 or parity["ids_order_identical"] == parity["cases"]
        out.append(_emit(ctx, workload="W7", alternative=alt, repetition=0, run_kind="warm", order_in_repetition=0,
                         status="ok" if graded_ok else "check_failed", timings=[],
                         outputs={"observations": len(pooled), "pooled_p95": p95(pooled), "pooled_median": statistics.median(pooled),
                                  "per_demand_diagnostic": per_demand, "parity": parity,
                                  "load_before_each_observation": loads[alt]},
                         checks={"ids_order_identical": graded_ok}, incident=None, start_load=None))
    return out


def eligible_ids(policy, assets: list, demands: list) -> list[int]:
    """Eligible asset indexes, computed for EVERY demand like the numpy path does. If the policy ever depends on the demand the
    sets differ and the harness stops: a single shared eligible table would then not reproduce the reference path."""
    sets = [frozenset(i for i, a in enumerate(assets) if policy.evaluate(a.patent, d).is_eligible) for d in demands]
    if len(set(sets)) != 1:
        raise ValueError("eligibility depends on the demand: the shared eligible table of alternative A cannot reproduce the reference")
    return sorted(sets[0])


def build_real_operational(directory, dsn: str | None, namespace: str, alternatives: tuple[str, ...]):
    """The real W7 inputs, as in spike P2: the frozen artifacts (hash-verified by the loader), their demands and query vectors.
    Returns (retrievers, demands, vectors, closers). Never called by the tests."""
    from pathlib import Path

    from domain.models.matching import RetrievalMethod
    from infrastructure.embeddings.embedding_texts import demand_embedding_text
    from infrastructure.embeddings.frozen_embedding_index import load_index
    from infrastructure.operational.artifacts import load_operational_artifacts

    directory = Path(directory)
    art = load_operational_artifacts(directory)
    demands = art.demands.list_all()
    vectors = {}
    for d in demands:
        q = np.asarray(art.retriever._embedder.embed(demand_embedding_text(d.title, d.description)), dtype=np.float32)
        vectors[d.demand_id] = q / float(np.linalg.norm(q))
    retrievers, closers = {}, []
    if "B" in alternatives:
        retrievers["B"] = NumpyRetriever(art.retriever, RetrievalMethod.SEMANTIC)
    if "A" in alternatives:
        assets = art.catalog.list_all()
        eligible = eligible_ids(art.policy, assets, demands)
        pg = PgRetriever(dsn, f"{namespace}_operational_v1", [a.patent.publication_id for a in assets],
                         load_index(directory, "embeddings_patents_v1").matrix, eligible)
        retrievers["A"] = pg
        closers.append(pg.close)
    return retrievers, demands, vectors, closers
