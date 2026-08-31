"""One-command end-to-end validation of the full agent graph against mock data.

Usage: .venv/bin/python run_pipeline.py
Requires a working GEMINI/Vertex express key in .env (Vertex AI API enabled).
Prints each stage's structured output so Days 7-11 DoD can be checked by eye.
"""

import asyncio
import json
import os
import time

from dotenv import load_dotenv

load_dotenv()

from google.adk.plugins.base_plugin import BasePlugin
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from patent_agent.agent import root_agent
from patent_agent.shared.state_keys import (
    ADVERSARIAL_VERDICTS,
    CANDIDATE_INVENTIONS,
    PATENT_LANDSCAPE,
    SCORED_CANDIDATES,
)

PROMPT = (
    "Mine the patent landscape for the locked demo domain "
    "'solid-state battery electrolytes' (query: 'solid electrolyte interphase'). "
    "Cluster into white-space vs saturated areas, propose candidate inventions for "
    "the top white-space cluster, adversarially validate them against prior art, "
    "and score survivors."
)

STATE_KEYS = [PATENT_LANDSCAPE, CANDIDATE_INVENTIONS, ADVERSARIAL_VERDICTS, SCORED_CANDIDATES]


def show(label: str, value):
    print(f"\n=== {label} ===")
    if value is None:
        print("  <missing>")
    elif isinstance(value, str):
        try:
            print(json.dumps(json.loads(value), indent=2)[:2000])
        except json.JSONDecodeError:
            print(value[:2000])
    else:
        print(json.dumps(value, indent=2, default=str)[:2000])


from patent_agent.shared.provider_policy import ProviderPacingPlugin, RateLimiter
from patent_agent.shared.telemetry import PipelineProfiler



async def main() -> None:
    os.environ.setdefault("USE_MOCK_BIGQUERY", "true")
    session_service = InMemorySessionService()
    runner = Runner(
        agent=root_agent,
        app_name="pipeline_check",
        session_service=session_service,
        plugins=[RateLimiter()],
    )
    session = await session_service.create_session(app_name="pipeline_check", user_id="dev")

    print(f"model={os.getenv('GEMINI_MODEL')} mock_bigquery={os.getenv('USE_MOCK_BIGQUERY')}")
    print("running root_agent (research -> inventor/adversarial loop -> governor)...")

    msg = types.Content(role="user", parts=[types.Part(text=PROMPT)])
    events = 0
    for event in runner.run(user_id="dev", session_id=session.id, new_message=msg):
        events += 1
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    who = event.author or "?"
                    snippet = part.text.strip().replace("\n", " ")[:120]
                    print(f"  [{who}] {snippet}")

    final = await session_service.get_session(
        app_name="pipeline_check", user_id="dev", session_id=session.id
    )
    print(f"\n{events} events total.")
    for key in STATE_KEYS:
        show(key, (final.state or {}).get(key))


if __name__ == "__main__":
    asyncio.run(main())
