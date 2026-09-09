"""Pure domain contract for the scientific-results publication artifact (ADR 0025).

`scientific_results.json` is a sibling of `project_status.json` (ADR 0022/0023): a
separate, statically-published, git-tracked artifact carrying Nexus's empirical
outputs, never the system's engineering/audit status. This module defines only the
contract boundary — the schema and its invariants — not a publisher. No producer for
this contract exists yet; nothing in this module is wired to real Nexus output.

Track semantics (ADR 0025 §1-2):
- `discovery` (Head A, ADR 0017): landscape/candidate/adversarial synthesis output.
  Real-time, LLM-involved, not reproducible. Must never be presented as scientifically
  verified, and must carry the exact `DISCOVERY_DISCLAIMER` wherever rendered.
- `verification` (Head B, ADR 0017): deterministic, policy-sealed matching evidence.

Reuses existing payload shapes rather than redefining them: `PatentCluster`,
`InventionCandidate`, `AdversarialVerdict`, `ScoreCard` (domain.models.runtime_schemas,
Head A) and `MatchAssessment` (domain.models.matching, Head B). This module adds only
the publication envelope, execution scoping, evidence-citation structure, and the
epistemic invariants ADR 0025 requires around them — it does not create producers
for `OpportunityScore`/`OpportunityHypothesis` (domain.models.opportunity), which
remain unused by any pipeline.

`TechnologyClusterObservation` was added to carry the white-space metrics
(density/recency/citation_traction/demand_intensity/quadrant/mean_age_years) that
`application.landscape.metrics.compute_white_space_metrics` already computes but
`PatentCluster`/`cluster_patents` discard — this is the concrete publisher requirement
(the first real snapshot, see `scripts/publish_scientific_results.py`) that justified
extending this contract beyond PR #71's original scope.

Discovery-track free text is additionally checked against a fixed phrase denylist
(see `_FORBIDDEN_DISCOVERY_CLAIM_PHRASES` below). That check is a conservative
lexical guardrail against the most obvious mistakes reaching publication, not a
semantic claim verifier — it can both over- and under-reject; see its docstring.
"""

import re
from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from domain.models.matching import MatchAssessment
from domain.models.runtime_schemas import AdversarialVerdict, InventionCandidate, PatentCluster, ScoreCard


class Track(StrEnum):
    """Mandatory, non-interchangeable classification of a published record (ADR 0025 §1)."""

    DISCOVERY = "discovery"
    VERIFICATION = "verification"


# Exact required wording (ADR 0025 §2). A discovery-track record's disclaimer must match
# this string verbatim — not a dashboard paraphrase (SCIENTIFIC_RESULTS_CONTRACT.md §5.8).
DISCOVERY_DISCLAIMER = (
    "Nexus generated/discovered this output; it is model-synthesized technology "
    "discovery output, not scientifically verified evidence. It does not demonstrate "
    "patentability, freedom-to-operate, or commercial efficacy, and is not a "
    "substitute for a professional prior-art search. (ADR 0017 §5, ADR 0025 §2)"
)

# CONSERVATIVE LEXICAL GUARDRAIL — not semantic/epistemic enforcement.
#
# This is a denylist substring match against a fixed phrase list, matched
# case-insensitively. It catches the obvious, unambiguous case: free text that
# asserts one of these exact phrases. It is deliberately NOT a claim-detection
# model and must not be treated as one:
#   - false positives are possible (e.g. text that *quotes* or *negates* a
#     forbidden phrase to explicitly disclaim it would still be rejected here);
#   - false negatives are possible (any rephrasing, translation, or claim not
#     on this exact list passes silently).
# Real enforcement of "discovery output must never imply patentability, FTO,
# efficacy, or scientific verification" (ADR 0017 §5.5-5.6, ADR 0025 §2) is a
# generation/review responsibility upstream of this contract — this guardrail
# exists only to fail loudly on the most obvious mistakes reaching publication,
# not to guarantee the invariant holds for everything that passes it.
_FORBIDDEN_DISCOVERY_CLAIM_PHRASES: tuple[str, ...] = (
    "is patentable",
    "is not patentable",
    "freedom to operate",
    "freedom-to-operate",
    "proven effective",
    "clinically proven",
    "scientifically verified",
    "scientifically proven",
    "demonstrates efficacy",
    "commercially viable",
    "guaranteed to",
)

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _require_exact_discovery_disclaimer(v: str, record_kind: str) -> str:
    if v != DISCOVERY_DISCLAIMER:
        raise ValueError(
            f"a discovery {record_kind} record must carry the exact required epistemic "
            "disclaimer verbatim (ADR 0025 §2) — not a paraphrase or omission"
        )
    return v


def _reject_forbidden_discovery_claims(*texts: str | None) -> None:
    """Conservative lexical guardrail (see comment above) — not a semantic claim verifier."""
    for text in texts:
        lowered = (text or "").lower()
        for phrase in _FORBIDDEN_DISCOVERY_CLAIM_PHRASES:
            if phrase in lowered:
                raise ValueError(
                    f"discovery-track text must not assert '{phrase}' "
                    "(ADR 0017 §5.5-5.6, ADR 0025 §2) — conservative lexical "
                    "guardrail, not a semantic claim verifier"
                )


class CitationResolution(StrEnum):
    """Whether an evidence citation's referenced publication was resolved to metadata."""

    RESOLVED = "resolved"
    UNRESOLVED = "unresolved"


class EvidenceCitation(BaseModel):
    """A structured, traceable reference to a cited prior-art publication.

    A citation that cannot be resolved to a `PatentRecord`/`PatentDocument` is kept as
    an explicit `unresolved` entry (SCIENTIFIC_RESULTS_CONTRACT.md §5 invariant 4) —
    never silently dropped and never conflated with a resolved one.
    """

    model_config = ConfigDict(frozen=True)

    publication_id: str = Field(min_length=1)
    role: Literal["supports", "challenges"]
    resolution: CitationResolution
    title: str | None = None
    publication_date: str | None = None

    @model_validator(mode="after")
    def validate_resolution_consistency(self) -> "EvidenceCitation":
        if self.resolution == CitationResolution.RESOLVED and self.title is None:
            raise ValueError("a 'resolved' citation must carry a resolved title")
        if self.resolution == CitationResolution.UNRESOLVED and (
            self.title is not None or self.publication_date is not None
        ):
            raise ValueError(
                "an 'unresolved' citation must not carry resolved metadata "
                "(title/publication_date) — that would misrepresent it as resolved"
            )
        return self


class ChallengeStatus(StrEnum):
    """Distinguishes 'no challenge has run yet' from 'a challenge ran' (SCIENTIFIC_RESULTS_CONTRACT.md
    §5 invariant 5: absence of evidence must never be represented as negative evidence).
    """

    NOT_YET_CHALLENGED = "not_yet_challenged"
    CHALLENGED = "challenged"


def _validate_utc_aware(v: datetime) -> datetime:
    if v.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware (UTC)")
    return v


class ScientificResultsExecution(BaseModel):
    """Identity and provenance of one execution that produced published records.

    `dataset_id`/`dataset_version`/`policy_id`/`policy_version`/`policy_sha256`/
    `engine_commit` are optional: the deterministic (`verification`) track already
    stamps all of them (mirrors `EvaluationRunReport`); the `discovery` track does not
    yet (ADR 0017 §7 — Head A has no durable, versioned execution record today). Making
    them optional here reflects that gap honestly rather than fabricating values; see
    `executions_are_aggregable` below for why an absent field blocks aggregation rather
    than being treated as a wildcard match.
    """

    model_config = ConfigDict(frozen=True)

    execution_id: str = Field(min_length=1)
    track: Track
    domain: str = Field(min_length=1)
    query: str = Field(min_length=1)
    created_at: datetime
    dataset_id: str | None = None
    dataset_version: str | None = None
    engine_commit: str | None = None
    policy_id: str | None = None
    policy_version: str | None = None
    policy_sha256: str | None = None

    @field_validator("created_at")
    @classmethod
    def validate_created_at_tz_aware(cls, v: datetime) -> datetime:
        return _validate_utc_aware(v)

    @field_validator("policy_sha256")
    @classmethod
    def validate_policy_sha256_format(cls, v: str | None) -> str | None:
        if v is not None and not _SHA256_RE.match(v.lower()):
            raise ValueError(f"Invalid SHA-256 digest format: {v}")
        return v.lower() if v is not None else v


def executions_are_aggregable(a: ScientificResultsExecution, b: ScientificResultsExecution) -> bool:
    """Whether two executions may be combined into one aggregate figure.

    Two executions are aggregable only if they share `track`, `dataset_id`, and
    `policy_version`, and none of those fields is missing on either side — a missing
    field never matches, on either side, even against another missing field
    (SCIENTIFIC_RESULTS_CONTRACT.md §5 invariant 6). This is the single reusable rule a
    future dashboard/publisher must call before computing any cross-execution figure;
    it does not itself perform aggregation.
    """
    if a.track != b.track:
        return False
    if a.dataset_id is None or b.dataset_id is None or a.dataset_id != b.dataset_id:
        return False
    return not (a.policy_version is None or b.policy_version is None or a.policy_version != b.policy_version)


class DiscoveryCandidateRecord(BaseModel):
    """A published `discovery`-track candidate invention, scoped to its execution."""

    model_config = ConfigDict(frozen=True)

    execution_id: str = Field(min_length=1)
    candidate: InventionCandidate
    disclaimer: str = Field(default=DISCOVERY_DISCLAIMER)

    @field_validator("disclaimer")
    @classmethod
    def validate_disclaimer_is_exact(cls, v: str) -> str:
        return _require_exact_discovery_disclaimer(v, "candidate")

    @model_validator(mode="after")
    def validate_no_forbidden_claims(self) -> "DiscoveryCandidateRecord":
        _reject_forbidden_discovery_claims(
            self.candidate.title,
            self.candidate.description,
            self.candidate.claimed_novelty,
        )
        return self


class DiscoveryVerificationRecord(BaseModel):
    """A published `discovery`-track adversarial-challenge outcome for one candidate.

    `challenge_status` is the field that makes "not yet challenged" observably distinct
    from "challenged and found clean" — an `AdversarialVerdict` is never present without
    a `CHALLENGED` status, and never absent while still claiming `CHALLENGED`.
    """

    model_config = ConfigDict(frozen=True)

    execution_id: str = Field(min_length=1)
    candidate_id: str = Field(min_length=1)
    challenge_status: ChallengeStatus
    verdict: AdversarialVerdict | None = None
    scorecard: ScoreCard | None = None
    citations: tuple[EvidenceCitation, ...] = Field(default_factory=tuple)
    disclaimer: str = Field(default=DISCOVERY_DISCLAIMER)

    @field_validator("disclaimer")
    @classmethod
    def validate_disclaimer_is_exact(cls, v: str) -> str:
        return _require_exact_discovery_disclaimer(v, "verification")

    @model_validator(mode="after")
    def validate_challenge_consistency(self) -> "DiscoveryVerificationRecord":
        if self.challenge_status == ChallengeStatus.NOT_YET_CHALLENGED:
            if self.verdict is not None or self.citations:
                raise ValueError(
                    "a 'not_yet_challenged' record must carry no verdict and no "
                    "citations — an empty verdict/citation set on a challenge that "
                    "never ran would be indistinguishable from a completed challenge "
                    "that found nothing, which is exactly the ambiguity this status "
                    "exists to prevent"
                )
        elif self.verdict is None:
            raise ValueError("a 'challenged' record must carry its verdict")

        if self.verdict is not None:
            _reject_forbidden_discovery_claims(self.verdict.rationale)
        if self.scorecard is not None:
            _reject_forbidden_discovery_claims(*self.scorecard.supporting_evidence)
        return self


class VerificationMatchRecord(BaseModel):
    """A published `verification`-track demand-patent match assessment, scoped to its execution.

    Carries no disclaimer: `verification`-track evidence is the deterministic, policy-sealed
    track ADR 0025 §2 permits describing as "evaluated under this deterministic policy."
    """

    model_config = ConfigDict(frozen=True)

    execution_id: str = Field(min_length=1)
    assessment: MatchAssessment


class TechnologyClusterObservation(BaseModel):
    """A published cluster observation: the existing `PatentCluster` plus the fuller
    white-space metrics `compute_white_space_metrics`
    (application.landscape.metrics) already computes but `cluster_patents`
    (application.landscape.clustering) discards before returning. No new computation
    is introduced by this type — every field is copied verbatim from data Nexus's
    existing landscape pipeline already produces (SCIENTIFIC_RESULTS_CONTRACT.md §4,
    `TechnologyCluster` "Derivable" row).
    """

    model_config = ConfigDict(frozen=True)

    cluster: PatentCluster
    density: float
    recency: float
    citation_traction: float
    citation_coverage: float
    demand_intensity: float
    quadrant: str = Field(min_length=1)
    mean_age_years: float


class DiscoveryLandscapeRecord(BaseModel):
    """A published `discovery`-track landscape observation, scoped to its execution."""

    model_config = ConfigDict(frozen=True)

    execution_id: str = Field(min_length=1)
    query: str = Field(min_length=1)
    clusters: tuple[TechnologyClusterObservation, ...] = Field(default_factory=tuple)
    disclaimer: str = Field(default=DISCOVERY_DISCLAIMER)

    @field_validator("disclaimer")
    @classmethod
    def validate_disclaimer_is_exact(cls, v: str) -> str:
        return _require_exact_discovery_disclaimer(v, "landscape")


class ScientificResultsDocument(BaseModel):
    """Top-level `scientific_results.json` contract.

    Enforces referential integrity between records and their declared execution
    (every record must reference a real, listed execution) and track consistency
    (a record's track must match the track of the execution it references) —
    the mechanism that makes "discovery and verification cannot be silently mixed"
    a structural guarantee rather than a convention.
    """

    model_config = ConfigDict(frozen=True)

    schema_version: str = Field(min_length=1)
    generated_at: datetime
    executions: tuple[ScientificResultsExecution, ...] = Field(default_factory=tuple)
    landscapes: tuple[DiscoveryLandscapeRecord, ...] = Field(default_factory=tuple)
    candidates: tuple[DiscoveryCandidateRecord, ...] = Field(default_factory=tuple)
    verifications: tuple[DiscoveryVerificationRecord, ...] = Field(default_factory=tuple)
    matches: tuple[VerificationMatchRecord, ...] = Field(default_factory=tuple)

    @field_validator("generated_at")
    @classmethod
    def validate_generated_at_tz_aware(cls, v: datetime) -> datetime:
        return _validate_utc_aware(v)

    @model_validator(mode="after")
    def validate_referential_integrity(self) -> "ScientificResultsDocument":
        executions_by_id: dict[str, ScientificResultsExecution] = {}
        for execution in self.executions:
            if execution.execution_id in executions_by_id:
                raise ValueError(f"duplicate execution_id in executions: '{execution.execution_id}'")
            executions_by_id[execution.execution_id] = execution

        for landscape in self.landscapes:
            self._require_track(landscape.execution_id, executions_by_id, Track.DISCOVERY, "landscape")
        for candidate in self.candidates:
            self._require_track(candidate.execution_id, executions_by_id, Track.DISCOVERY, "candidate")
        for verification in self.verifications:
            self._require_track(verification.execution_id, executions_by_id, Track.DISCOVERY, "verification")
        for match in self.matches:
            self._require_track(match.execution_id, executions_by_id, Track.VERIFICATION, "match")
        return self

    @staticmethod
    def _require_track(
        execution_id: str,
        executions_by_id: dict[str, ScientificResultsExecution],
        required_track: Track,
        record_kind: str,
    ) -> None:
        execution = executions_by_id.get(execution_id)
        if execution is None:
            raise ValueError(f"{record_kind} references unknown execution_id '{execution_id}'")
        if execution.track != required_track:
            raise ValueError(
                f"{record_kind} references execution_id '{execution_id}' with "
                f"track={execution.track}, but a {record_kind} record requires "
                f"track={required_track} — discovery and verification cannot be mixed "
                "(ADR 0025 §1)"
            )
