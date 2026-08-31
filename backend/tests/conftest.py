import pytest


@pytest.fixture(autouse=True)
def _reset_analyze_rate_limit():
    """The rate limiter is a module-level dict shared by every test file's
    TestClient (all requests come from the same "testclient" host), so it
    must be reset between tests or unrelated tests exhaust each other's quota."""
    import main

    main._analyze_request_times.clear()
    yield
