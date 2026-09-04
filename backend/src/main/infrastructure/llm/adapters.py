"""Provider adapters translating domain agent protocols to concrete LLM transports."""

import json

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
from infrastructure.llm.client_protocol import (
    LlmChatMessage,
    LlmChatRequest,
    LlmClientProtocol,
)


def validate_grounded_citations(cited_patents: list[str], prior_art: list[PatentRecord]) -> list[str]:
    """Deterministically validate that cited patents exist in the supplied prior art."""
    valid_pub_numbers = {p.publication_number for p in prior_art}
    return [p for p in cited_patents if p in valid_pub_numbers]


class LlmAgentAdapter(InventorAgentProtocol, AdversarialAgentProtocol):
    """Adapter implementing domain agent ports using a low-level LLM client."""

    def __init__(self, llm_client: LlmClientProtocol | None = None) -> None:
        self.client = llm_client

    def propose_candidate(
        self,
        cluster_id: str,
        demands: list[DemandSignal],
        prior_art: list[PatentRecord],
    ) -> InventionCandidate:
        if not self.client:
            raise ValueError("LLM client not configured")

        demand_text = "\n".join(f"- {d.title}: {d.description}" for d in demands[:3])
        prior_art_text = "\n".join(f"- {p.publication_number}: {p.title}" for p in prior_art[:5])

        system_prompt = (
            "You are an industrial patent inventor. Given the unmet demand signals and domestic prior art, "
            "propose a novel, patentable technical solution. Respond ONLY in valid JSON matching the schema:\n"
            '{"title": "...", "description": "...", "claimed_novelty": "..."}'
        )
        user_prompt = f"Cluster: {cluster_id}\n\nDemands:\n{demand_text}\n\nPrior Art:\n{prior_art_text}"

        request = LlmChatRequest(
            messages=[
                LlmChatMessage(role="system", content=system_prompt),
                LlmChatMessage(role="user", content=user_prompt),
            ],
            response_format="json_object",
        )
        res = self.client.chat_completion(request)
        data = json.loads(res.content)

        if not isinstance(data, dict) or "title" not in data or "claimed_novelty" not in data:
            raise ValueError(f"LLM response failed schema validation: {res.content}")

        return InventionCandidate(
            candidate_id=f"cand_{cluster_id}_001",
            cluster_id=cluster_id,
            title=data["title"],
            description=data.get("description", ""),
            claimed_novelty=data["claimed_novelty"],
        )

    def critique_candidate(
        self,
        candidate: InventionCandidate,
        prior_art: list[PatentRecord],
    ) -> AdversarialVerdict:
        if not prior_art:
            return AdversarialVerdict(
                candidate_id=candidate.candidate_id,
                verdict="survives",
                rationale="No domestic prior art found anticipating the candidate.",
                cited_patents=["NONE"],
            )

        if not self.client:
            raise ValueError("LLM client not configured")

        prior_art_text = "\n".join(
            f"- {p.publication_number}: {p.title} - {p.abstract[:200]}" for p in prior_art[:5]
        )
        system_prompt = (
            "You are a European patent examiner. Conduct an adversarial novelty analysis. "
            "You MUST cite at least one real publication number from the provided prior art list. "
            "Respond ONLY in valid JSON matching:\n"
            '{"verdict": "survives"|"rejected", "rationale": "...", "cited_patents": ["PUB_NUM"]}'
        )
        user_prompt = (
            f"Candidate Invention: {candidate.title}\nDescription: {candidate.description}\n"
            f"Novelty: {candidate.claimed_novelty}\n\nPrior Art:\n{prior_art_text}"
        )

        request = LlmChatRequest(
            messages=[
                LlmChatMessage(role="system", content=system_prompt),
                LlmChatMessage(role="user", content=user_prompt),
            ],
            response_format="json_object",
        )
        res = self.client.chat_completion(request)
        data = json.loads(res.content)

        if not isinstance(data, dict) or "verdict" not in data or "cited_patents" not in data:
            raise ValueError(f"LLM response failed schema validation: {res.content}")

        raw_cites = data.get("cited_patents", [])
        if not isinstance(raw_cites, list):
            raise ValueError(f"Expected cited_patents to be a list, got {type(raw_cites)}")

        grounded_cites = validate_grounded_citations(raw_cites, prior_art)
        if not grounded_cites:
            raise ValueError(
                f"Adversarial critique cited no valid prior art from supplied candidates: {raw_cites}"
            )

        return AdversarialVerdict(
            candidate_id=candidate.candidate_id,
            verdict=data.get("verdict", "survives"),
            rationale=data.get("rationale", "Evaluation complete"),
            cited_patents=grounded_cites,
        )


GroqAgentAdapter = LlmAgentAdapter
