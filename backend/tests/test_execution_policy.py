import pytest
from patent_agent.shared.provider_policy import (
    DirectProviderPolicy,
    ExecutionPolicy,
    GroqFreeTierPolicy,
    get_execution_policy,
)


@pytest.mark.anyio
async def test_execution_policy_concurrency():
    policy = DirectProviderPolicy()
    exec_policy = ExecutionPolicy(provider_policy=policy, max_concurrency=2)

    assert not exec_policy.is_busy()

    async with exec_policy.acquire_execution_slot():
        assert exec_policy.active_runs == 1
        assert not exec_policy.is_busy()

        async with exec_policy.acquire_execution_slot():
            assert exec_policy.active_runs == 2
            assert exec_policy.is_busy()

        assert exec_policy.active_runs == 1
        assert not exec_policy.is_busy()

    assert exec_policy.active_runs == 0
