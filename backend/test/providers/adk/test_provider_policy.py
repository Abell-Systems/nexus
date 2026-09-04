"""Unit tests for ProviderPolicy and ProviderPacingPlugin."""

from unittest.mock import AsyncMock, patch

import pytest

from infrastructure.llm.provider_policy import (
    DirectProviderPolicy,
    ExecutionPolicy,
    GroqFreeTierPolicy,
    ProviderPacingPlugin,
    ProviderPolicy,
    get_execution_policy,
)


def test_provider_policy_initialization():
    policy = ProviderPolicy(max_requests_per_minute=20, max_tokens_per_minute=20000, cooldown_seconds=1.5)
    assert policy.max_requests_per_minute == 20
    assert policy.max_tokens_per_minute == 20000
    assert policy.cooldown_seconds == 1.5

    assert issubclass(DirectProviderPolicy, ProviderPolicy)
    assert issubclass(GroqFreeTierPolicy, ProviderPolicy)


@pytest.mark.asyncio
async def test_execution_policy_slot_management():
    ep = ExecutionPolicy(max_concurrency=1)
    assert ep.is_busy() is False

    async with ep.acquire_execution_slot():
        assert ep.is_busy() is True
        assert ep.active_runs == 1

    assert ep.is_busy() is False
    assert ep.active_runs == 0


def test_get_execution_policy_singleton():
    ep = get_execution_policy()
    assert isinstance(ep, ExecutionPolicy)


@pytest.mark.asyncio
async def test_provider_pacing_plugin():
    policy = ProviderPolicy(cooldown_seconds=0.1)
    plugin = ProviderPacingPlugin(policy=policy)
    assert plugin.name == "provider_pacing"

    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        plugin._last_call_time = 100.0
        with patch("time.time", side_effect=[100.02, 100.12]):
            await plugin.before_model_call()
            mock_sleep.assert_awaited_once()
            called_wait = mock_sleep.call_args[0][0]
            assert 0.05 < called_wait <= 0.1
