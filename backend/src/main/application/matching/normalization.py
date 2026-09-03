def min_max_normalize(scores: dict[str, float]) -> dict[str, float]:
    """Normalizes raw scores to [0.0, 1.0] across a candidate pool.

    Invariants:
    - If all scores are identical (max == min), all candidates receive 0.0.
    - If scores is empty, returns an empty dictionary.
    - Order of keys in the input is preserved.
    """
    if not scores:
        return {}

    values = list(scores.values())
    min_val = min(values)
    max_val = max(values)

    if max_val == min_val:
        return {k: 0.0 for k in scores}

    spread = max_val - min_val
    return {k: (v - min_val) / spread for k, v in scores.items()}
