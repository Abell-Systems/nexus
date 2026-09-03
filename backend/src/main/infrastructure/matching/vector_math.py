import math


def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """Computes cosine similarity between two dense real-valued vectors.

    sim = (v1 . v2) / (||v1|| * ||v2||)
    
    Returns 0.0 if either vector has norm 0 or vectors have different lengths.
    Clamps output strictly to [-1.0, 1.0].
    """
    if len(v1) != len(v2) or not v1:
        return 0.0

    dot_product = sum(a * b for a, b in zip(v1, v2, strict=False))
    norm_v1 = math.sqrt(sum(a * a for a in v1))
    norm_v2 = math.sqrt(sum(b * b for b in v2))

    if norm_v1 == 0.0 or norm_v2 == 0.0:
        return 0.0

    raw_cos = dot_product / (norm_v1 * norm_v2)
    # Numerical stability clamp
    return max(-1.0, min(1.0, raw_cos))
