"""Pre-registered scoring library for the operational dense-retrieval probe.

Spec: docs/superpowers/specs/2026-09-30-operational-dense-retrieval-design.md, section 7.
Pure functions only; the two CLIs in this directory do the file I/O.
"""

import math
import random
import re
import sys
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "backend" / "src" / "main"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from application.evaluation.iaa import compute_iaa  # noqa: E402
from application.evaluation.statistics.bootstrap import paired_bootstrap_ci  # noqa: E402
from domain.models.annotation import AnnotationJudgment  # noqa: E402
from domain.models.evaluation import RelevanceGrade  # noqa: E402

TOP_K = 5
RELEVANT_MIN_GRADE = 2
P5_THRESHOLD = 0.40
DELTA_THRESHOLD = 0.15
KAPPA_THRESHOLD = 0.70
SEED = 42
COMMON_FRACTION = 0.2
_EPS = 1e-9  # the 0.15 threshold must survive float fuzz (0.41 - 0.26 == 0.14999999999999997)

Pair = tuple[str, str]
Label = int | None  # None = excluded (unresolved UNCERTAIN), never imputed as 0


class Outcome(StrEnum):
    RESOLVED_YES = "RESOLVED-YES"
    RESOLVED_NO = "RESOLVED-NO"
    UNRESOLVED = "UNRESOLVED"


@dataclass(frozen=True)
class PairedMacro:
    p5_bm25: float
    p5_dense: float
    delta: float
    n_used: int
    n_dropped: int


@dataclass(frozen=True)
class KappaResult:
    weighted_kappa: float
    binary_kappa: float
    n_used: int
    n_excluded: int


def union_pairs(bm25: Mapping[str, Sequence[str]], dense: Mapping[str, Sequence[str]]) -> list[Pair]:
    pairs: set[Pair] = set()
    for by_demand in (bm25, dense):
        for demand_id, publication_ids in by_demand.items():
            pairs.update((demand_id, pub) for pub in publication_ids)
    return sorted(pairs)


def blind_order(pairs: Collection[Pair], seed: int = SEED) -> list[Pair]:
    ordered = sorted(set(pairs))
    random.Random(seed).shuffle(ordered)
    return ordered


def draw_common_sample(
    ordered_pairs: Sequence[Pair], fraction: float = COMMON_FRACTION, seed: int = SEED
) -> list[Pair]:
    size = math.ceil(round(fraction * len(ordered_pairs), 9))  # 0.2 * 15 == 3.0000000000000004 in IEEE-754
    return sorted(random.Random(seed).sample(sorted(ordered_pairs), size))


def final_labels(
    model: Mapping[Pair, Label], human: Mapping[Pair, Label], human_pairs: Collection[Pair]
) -> dict[Pair, Label]:
    """Amendment A2: the human grade wherever the human graded, the model grade elsewhere."""
    human_set = set(human_pairs)
    labels: dict[Pair, Label] = {}
    for pair, grade in model.items():
        if pair in human_set:
            if pair not in human:
                raise KeyError(f"Pair {pair} is reserved for the human but has no human grade")
            labels[pair] = human[pair]
        elif grade is None:
            raise ValueError(f"Model-uncertain pair {pair} was not escalated to the human")
        else:
            labels[pair] = grade
    return labels


def needs_escalation(grade: Label, confidence: str) -> bool:
    """Fixed before the model ran (Amendment A2): low confidence or an uncertain grade goes to the human."""
    return grade is None or confidence == "low"


def escalation_pair_ids(judgments: Mapping[str, tuple[Label, str]], common_ids: Collection[str]) -> list[str]:
    """Pair ids the human must grade beyond the common sample, sorted."""
    common = set(common_ids)
    return sorted(pid for pid, (grade, confidence) in judgments.items()
                  if pid not in common and needs_escalation(grade, confidence))


def precision_at_5(demand_id: str, top5: Sequence[str], labels: Mapping[Pair, Label]) -> float | None:
    if len(top5) > TOP_K:
        raise ValueError(f"top list has {len(top5)} items, expected at most {TOP_K}")
    relevant = 0
    excluded = 0
    for publication_id in top5:
        key = (demand_id, publication_id)
        if key not in labels:
            raise KeyError(f"Unjudged pair {key}: every pair in a top-5 list needs a final label")
        label = labels[key]
        if label is None:
            excluded += 1
        elif label >= RELEVANT_MIN_GRADE:
            relevant += 1
    denominator = TOP_K - excluded
    return None if denominator == 0 else relevant / denominator


def paired_macro(bm25: Mapping[str, float | None], dense: Mapping[str, float | None]) -> PairedMacro:
    demands = sorted(set(bm25) & set(dense))
    usable = [d for d in demands if bm25[d] is not None and dense[d] is not None]
    if not usable:
        raise ValueError("No demand has a usable P@5 for both methods")
    p5_bm25 = sum(bm25[d] for d in usable) / len(usable)  # type: ignore[misc]
    p5_dense = sum(dense[d] for d in usable) / len(usable)  # type: ignore[misc]
    return PairedMacro(
        p5_bm25=p5_bm25,
        p5_dense=p5_dense,
        delta=p5_dense - p5_bm25,
        n_used=len(usable),
        n_dropped=len(demands) - len(usable),
    )


def classify_outcome(p5_dense: float, p5_bm25: float, weighted_kappa: float) -> Outcome:
    if weighted_kappa < KAPPA_THRESHOLD - _EPS:
        return Outcome.UNRESOLVED
    passes = p5_dense >= P5_THRESHOLD - _EPS and (p5_dense - p5_bm25) >= DELTA_THRESHOLD - _EPS
    return Outcome.RESOLVED_YES if passes else Outcome.RESOLVED_NO


def _ci(result) -> dict[str, float]:
    return {"estimate": result.estimate, "ci_lower": result.ci_lower, "ci_upper": result.ci_upper}


def bootstrap_summary(bm25: Mapping[str, float | None], dense: Mapping[str, float | None]) -> dict | None:
    """Informative uncertainty only (spec 7.7). Never used to change an outcome."""
    usable = [d for d in sorted(set(bm25) & set(dense)) if bm25[d] is not None and dense[d] is not None]
    if len(usable) < 2:
        return None
    b = [bm25[d] for d in usable]
    t = [dense[d] for d in usable]
    zeros = [0.0] * len(usable)
    return {
        "n_demands": len(usable),
        "delta": _ci(paired_bootstrap_ci(b, t, seed=SEED)),
        "dense": _ci(paired_bootstrap_ci(zeros, t, seed=SEED)),
        "bm25": _ci(paired_bootstrap_ci(zeros, b, seed=SEED)),
    }


def common_sample_kappa(
    grades_a: Mapping[Pair, Label], grades_b: Mapping[Pair, Label], common: Collection[Pair]
) -> KappaResult:
    usable = sorted(p for p in common if grades_a.get(p) is not None and grades_b.get(p) is not None)
    judgments_a = [
        AnnotationJudgment(demand_id=d, publication_id=p, annotator_id="A", grade=RelevanceGrade(grades_a[(d, p)]))
        for d, p in usable
    ]
    judgments_b = [
        AnnotationJudgment(demand_id=d, publication_id=p, annotator_id="B", grade=RelevanceGrade(grades_b[(d, p)]))
        for d, p in usable
    ]
    report = compute_iaa(judgments_a, judgments_b)
    return KappaResult(
        weighted_kappa=report.weighted_kappa,
        binary_kappa=report.binary_kappa,
        n_used=len(usable),
        n_excluded=len(set(common)) - len(usable),
    )


_ES_WORDS = re.compile(r"\b(el|la|los|las|del|que|para|con|una|por)\b")
_EN_WORDS = re.compile(r"\b(the|and|of|for|with|is|are|that)\b")


def guess_language(text: str) -> str:
    """Stopword heuristic, recorded as a heuristic: 'es' if Spanish stopwords outnumber English ones."""
    lowered = text.lower()
    return "es" if len(_ES_WORDS.findall(lowered)) > len(_EN_WORDS.findall(lowered)) else "en"
