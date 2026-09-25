"""Boundary-stratum and control-sample construction for the TED construct-validity
classifier validation, per
docs/superpowers/specs/2026-09-23-ted-construct-validity-classifier-design.md
SS4/SS5. Pure logic, no I/O."""

import random
from dataclasses import dataclass


@dataclass(frozen=True)
class ControlSample:
    boundary_ids: tuple[str, ...]
    fill_ids: tuple[str, ...]

    @property
    def all_ids(self) -> tuple[str, ...]:
        return self.boundary_ids + self.fill_ids


def is_boundary_case(word_count: int, min_word_count: int, tolerance: int = 10) -> bool:
    """SS4: |word_count - min_word_count| <= tolerance."""
    return abs(word_count - min_word_count) <= tolerance


def build_control_sample(
    candidates: list[dict],
    min_word_count: int,
    target_size: int,
    seed: int,
    tolerance: int = 10,
) -> ControlSample:
    """SS5: the full boundary stratum plus a stratified (status x language) random
    fill up to target_size, drawn only from non-boundary candidates. Deterministic
    regardless of the input list's ordering."""
    boundary = sorted(
        c["demand_id"] for c in candidates if is_boundary_case(c["word_count"], min_word_count, tolerance)
    )
    boundary_set = set(boundary)
    remainder = [c for c in candidates if c["demand_id"] not in boundary_set]

    if target_size < len(boundary):
        raise ValueError(
            f"target_size={target_size} is smaller than the boundary stratum ({len(boundary)}); "
            "the boundary stratum is never truncated"
        )
    fill_n = target_size - len(boundary)

    strata: dict[tuple[str, str], list[str]] = {}
    for c in remainder:
        key = (c["status"], c["language_code"])
        strata.setdefault(key, []).append(c["demand_id"])

    rng = random.Random(seed)
    shuffled: dict[tuple[str, str], list[str]] = {}
    for key in sorted(strata):
        ids = sorted(strata[key])
        shuffled[key] = rng.sample(ids, len(ids))

    fill: list[str] = []
    stratum_keys = sorted(strata)
    idx = 0
    while len(fill) < fill_n:
        progressed = False
        for key in stratum_keys:
            if idx < len(shuffled[key]):
                fill.append(shuffled[key][idx])
                progressed = True
                if len(fill) == fill_n:
                    break
        if not progressed:
            break
        idx += 1

    if len(fill) < fill_n:
        raise ValueError(
            f"Not enough non-boundary candidates to fill target_size={target_size} "
            f"(boundary={len(boundary)}, needed fill={fill_n}, only found {len(fill)})"
        )

    return ControlSample(boundary_ids=tuple(boundary), fill_ids=tuple(fill))
