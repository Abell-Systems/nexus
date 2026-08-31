# NOTE: google-adk has begun deprecating LoopAgent/SequentialAgent in favor of a
# new Workflow API, but as of the installed version Workflow cannot yet be used as
# an LlmAgent sub-agent — irrelevant here since invention_loop is nested inside a
# SequentialAgent, not an LlmAgent. Revisit this if a later google-adk release
# removes these classes (see docs/roadmap.md open risks).
from google.adk.agents import LoopAgent, SequentialAgent

from .config import INVENTION_LOOP_MAX_ITERATIONS
from .prompt import ROOT_AGENT_INSTRUCTION
from .sub_agents.adversarial.agent import adversarial_agent, build_adversarial_agent
from .sub_agents.governor.agent import governor_agent, build_governor_agent
from .sub_agents.inventor.agent import inventor_agent, build_inventor_agent
from .sub_agents.research.agent import research_agent


def build_invention_loop() -> LoopAgent:
    return LoopAgent(
        name="invention_loop",
        sub_agents=[build_inventor_agent(), build_adversarial_agent()],
        max_iterations=INVENTION_LOOP_MAX_ITERATIONS,
    )


def build_invention_pipeline() -> SequentialAgent:
    return SequentialAgent(
        name="invention_pipeline",
        description="Invention loop and governor validation pipeline.",
        sub_agents=[build_invention_loop(), build_governor_agent()],
    )


invention_loop = LoopAgent(
    name="invention_loop",
    sub_agents=[inventor_agent, adversarial_agent],
    max_iterations=INVENTION_LOOP_MAX_ITERATIONS,
)

root_agent = SequentialAgent(
    name="patent_innovation_agent",
    description=ROOT_AGENT_INSTRUCTION,
    sub_agents=[research_agent, invention_loop, governor_agent],
)

