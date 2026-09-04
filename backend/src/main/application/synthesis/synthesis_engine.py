"""Decoupled Multi-Agent Synthesis & Adversarial Prior-Art Orchestration."""

from domain.models.runtime_schemas import (
    AdversarialVerdict,
    DemandSignal,
    InventionCandidate,
    PatentRecord,
)
from domain.protocols.agents import (
    AdversarialAgentProtocol,
    InventorAgentProtocol,
)


class SynthesisEngine:
    """Application use-case orchestrating candidate invention proposals and adversarial critiques.

    Invariants:
    - Depends strictly on domain capability ports (InventorAgentProtocol, AdversarialAgentProtocol).
    - Contains ZERO LLM transport abstractions (no chat completions, prompts, temperatures, or formats).
    - Fails fast if required agent ports are missing.
    """

    def __init__(
        self,
        inventor: InventorAgentProtocol | None = None,
        adversarial: AdversarialAgentProtocol | None = None,
        *,
        agent: InventorAgentProtocol | None = None,
    ) -> None:
        inv = inventor or agent
        self.inventor = inv
        self.adversarial = adversarial or (inv if hasattr(inv, "critique_candidate") else None)

    def propose_candidate(
        self,
        cluster_id: str,
        demands: list[DemandSignal],
        prior_art: list[PatentRecord],
    ) -> InventionCandidate:
        if not self.inventor:
            raise ValueError("Inventor agent not configured")
        return self.inventor.propose_candidate(cluster_id, demands, prior_art)

    def evaluate_adversarial(
        self,
        candidate: InventionCandidate,
        prior_art: list[PatentRecord],
    ) -> AdversarialVerdict:
        if not self.adversarial:
            raise ValueError("Adversarial agent not configured")
        return self.adversarial.critique_candidate(candidate, prior_art)

    critique_candidate = evaluate_adversarial


InventionSynthesisEngine = SynthesisEngine
