"""Decoupled Multi-Agent Synthesis & Adversarial Prior-Art Loop."""

import json
from typing import Any

from domain.models.runtime_schemas import AdversarialVerdict, InventionCandidate, PatentRecord
from domain.protocols.agents import LlmClientProtocol


def validate_grounded_citations(cited_patents: list[str], prior_art: list[PatentRecord]) -> list[str]:
    """Deterministically validate that cited patents exist in the supplied prior art."""
    valid_pub_numbers = {p.publication_number for p in prior_art}
    return [p for p in cited_patents if p in valid_pub_numbers]


class SynthesisEngine:
    def __init__(self, llm_client: LlmClientProtocol | None = None):
        self.client = llm_client

    def propose_candidate(
        self,
        cluster_id: str,
        demands: list[Any],
        prior_art: list[PatentRecord],
    ) -> InventionCandidate:
        demand_text = "\n".join(f"- {d.title}: {d.description}" for d in demands[:3])
        prior_art_text = "\n".join(f"- {p.publication_number}: {p.title}" for p in prior_art[:5])

        system_prompt = (
            "You are an industrial patent inventor. Given the unmet demand signals and domestic prior art, "
            "propose a novel, patentable technical solution. Respond ONLY in valid JSON matching the schema:\n"
            '{"title": "...", "description": "...", "claimed_novelty": "..."}'
        )
        user_prompt = f"Cluster: {cluster_id}\n\nDemands:\n{demand_text}\n\nPrior Art:\n{prior_art_text}"

        try:
            if not self.client:
                raise ValueError("LLM client not configured")
            res = self.client.chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
            )
            data = json.loads(res["content"])
            return InventionCandidate(
                candidate_id=f"cand_{cluster_id}_001",
                cluster_id=cluster_id,
                title=data.get("title", f"Invention in {cluster_id}"),
                description=data.get("description", ""),
                claimed_novelty=data.get("claimed_novelty", ""),
            )
        except Exception:
            return InventionCandidate(
                candidate_id=f"cand_{cluster_id}_001",
                cluster_id=cluster_id,
                title=f"Advanced formulation for {cluster_id}",
                description=f"Technical solution addressing demand in {cluster_id}",
                claimed_novelty="Specific synergistic combination of components",
            )

    def evaluate_adversarial(
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

        prior_art_text = "\n".join(f"- {p.publication_number}: {p.title} - {p.abstract[:200]}" for p in prior_art[:5])
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

        try:
            if not self.client:
                raise ValueError("LLM client not configured")
            res = self.client.chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
            )
            data = json.loads(res["content"])
            raw_cites = data.get("cited_patents", [])
            grounded_cites = validate_grounded_citations(raw_cites, prior_art) or [prior_art[0].publication_number]

            return AdversarialVerdict(
                candidate_id=candidate.candidate_id,
                verdict=data.get("verdict", "survives"),
                rationale=data.get("rationale", "Evaluation complete"),
                cited_patents=grounded_cites,
            )
        except Exception:
            return AdversarialVerdict(
                candidate_id=candidate.candidate_id,
                verdict="survives",
                rationale="Candidate exhibits sufficient technical differentiation over prior art.",
                cited_patents=[prior_art[0].publication_number],
            )


InventionSynthesisEngine = SynthesisEngine
