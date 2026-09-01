"""Decoupled Propose-Critique-Score Invention Engine."""

from typing import Optional
from .groq_client import GroqLlmClient
from .tools.schemas import PatentRecord, DemandSignal, InventionCandidate, AdversarialVerdict, ScoreCard


class InventionSynthesisEngine:
    def __init__(self, client: GroqLlmClient):
        self.client = client

    def run_loop(
        self,
        cluster_id: str,
        demand: DemandSignal,
        prior_art: list[PatentRecord],
        max_iterations: int = 2
    ) -> tuple[InventionCandidate, AdversarialVerdict, ScoreCard]:
        """Execute propose-critique loop with prior-art citations and governor scoring."""
        prior_art_summary = "\n".join([
            f"- {p.publication_number} ({p.filing_date}): {p.title}. Abstract: {p.abstract}"
            for p in prior_art[:5]
        ])

        candidate: Optional[InventionCandidate] = None
        verdict: Optional[AdversarialVerdict] = None

        for iteration in range(max_iterations):
            # 1. Propose (Inventor Agent)
            inventor_prompt = f"""
Domain/Cluster: {cluster_id}
Industrial Demand Need: {demand.title} - {demand.description}

Existing Domestic Prior Art:
{prior_art_summary}

Synthesize a novel technological invention candidate that directly solves the industrial demand while technically differentiating from the prior art above.
"""
            candidate = self.client.generate_structured(
                prompt=inventor_prompt,
                schema=InventionCandidate,
                system_prompt="You are an expert Chief Technology Officer and patent inventor."
            )

            # 2. Attack (Adversarial Agent)
            adversarial_prompt = f"""
Proposed Candidate:
Title: {candidate.title}
Novelty Claim: {candidate.novelty_claim}
Description: {candidate.description}

Prior Art to Search & Attack With:
{prior_art_summary}

Critique this invention. If it is anticipated or obvious based on the prior art, set verdict to 'rejected' and cite the patent numbers. If it presents clear novelty beyond the cited prior art, set verdict to 'survives'.
YOU MUST CITE AT LEAST ONE PUBLICATION NUMBER FROM THE PRIOR ART IN 'cited_patents'.
"""
            verdict = self.client.generate_structured(
                prompt=adversarial_prompt,
                schema=AdversarialVerdict,
                system_prompt="You are a strict European Patent Office (EPO) patent examiner."
            )

            if verdict.verdict == "survives":
                break

        # 3. Score (Governor Agent)
        governor_prompt = f"""
Final Candidate: {candidate.title}
Novelty Claim: {candidate.novelty_claim}
Adversarial Verdict: {verdict.verdict} ({verdict.rationale})
Cited Patents: {', '.join(verdict.cited_patents)}

Assign calibrated 0.0-1.0 scores for novelty, prior_art_risk, differentiation, evidence, and list the supporting publication numbers in supporting_evidence.
"""
        scorecard = self.client.generate_structured(
            prompt=governor_prompt,
            schema=ScoreCard,
            system_prompt="You are a quantitative patent innovation governor."
        )

        return candidate, verdict, scorecard
