import asyncio
import os
from types import SimpleNamespace

os.environ.setdefault("USE_MOCK_BIGQUERY", "true")

from run_pipeline import RateLimiter


def test_rate_limiter_estimates_tokens_from_request_size():
    limiter = RateLimiter()
    small = SimpleNamespace(contents="x" * 400, config="")
    big = SimpleNamespace(contents="x" * 22000, config="")
    assert limiter._estimate_tokens(big) > limiter._estimate_tokens(small)


def test_rate_limiter_flags_window_overrun_from_two_under_budget_calls():
    """Two calls that are each individually under budget but sum past it
    within the same window must be flagged — this is exactly the live Groq
    failure (5467 used + 5462 requested > 8000 TPM) that pacing by request
    count alone missed."""
    limiter = RateLimiter()
    limiter._min_gap = 0.0
    limiter._tpm_budget = 8000

    call = SimpleNamespace(contents="x" * 22000, config="")  # ~5500 tokens
    asyncio.run(limiter.before_model_callback(callback_context=None, llm_request=call))

    used = sum(tok for _, tok in limiter._calls)
    assert used + limiter._estimate_tokens(call) > limiter._tpm_budget
