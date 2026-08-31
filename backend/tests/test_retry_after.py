from main import _retry_after_seconds


def test_retry_after_seconds_parses_groq_message_formats():
    assert _retry_after_seconds(Exception("...Please try again in 6.4875s. Need m")) == 6.4875
    assert _retry_after_seconds(Exception("...Please try again in 592.5ms. Need m")) == 0.5925


def test_retry_after_seconds_returns_none_for_non_rate_limit_errors():
    assert _retry_after_seconds(Exception("some unrelated error")) is None
