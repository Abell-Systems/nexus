"""Innoget Technology Calls Demand Data Source.

Parses the Innoget JSON dataset and implements full-text search with deterministic
ranking and matching provenance.
"""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .cpc_mapper import map_cpc_prefix
from .schemas import DemandSignal

FIXTURE_PATH = Path(__file__).parent / "innoget_demands.json"


@dataclass
class MatchProvenance:
    """Internal metadata explaining why a record matched a search query."""

    record_id: int
    score: float
    matched_fields: list[str] = field(default_factory=list)


class InnogetDemandDataSource:
    """DemandDataSource implementation over the local Innoget fixture dataset."""

    def __init__(self, json_path: Path | str | None = None):
        path = Path(json_path or FIXTURE_PATH)
        if not path.exists():
            self._records: list[dict[str, Any]] = []
            return
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            self._records = data.get("records", [])

    def search_demand_with_provenance(
        self, query: str, domain: str, max_results: int = 20
    ) -> list[tuple[DemandSignal, MatchProvenance]]:
        """Search demand signals and return paired (DemandSignal, MatchProvenance)."""
        terms = set((query + " " + domain).lower().split())
        # Filter out short stop words
        search_terms = {t for t in terms if len(t) > 2}

        scored_results: list[tuple[float, int, dict[str, Any], list[str]]] = []

        for record in self._records:
            rec_id = record.get("id", 0)
            title = record.get("title", "")
            desc = record.get("description", "")
            cat = record.get("category", "")
            keywords = " ".join(record.get("related_keywords", []))
            text = record.get("text", "")

            field_texts = {
                "title": title.lower(),
                "description": desc.lower(),
                "category": cat.lower(),
                "related_keywords": keywords.lower(),
                "text": text.lower(),
            }

            score = 0.0
            matched_fields: list[str] = []

            for term in search_terms:
                if term in field_texts["title"]:
                    score += 3.0
                    matched_fields.append("title")
                if term in field_texts["category"]:
                    score += 2.0
                    matched_fields.append("category")
                if term in field_texts["related_keywords"]:
                    score += 2.0
                    matched_fields.append("related_keywords")
                if term in field_texts["description"]:
                    score += 1.0
                    matched_fields.append("description")
                if term in field_texts["text"]:
                    score += 0.5
                    matched_fields.append("text")

            if score > 0 or not search_terms:
                unique_matched = sorted(list(set(matched_fields)))
                final_score = score if search_terms else 1.0
                scored_results.append((final_score, rec_id, record, unique_matched))

        # Deterministic sorting: highest score first, then lowest record ID as tie-breaker
        scored_results.sort(key=lambda item: (-item[0], item[1]))

        results: list[tuple[DemandSignal, MatchProvenance]] = []
        for score, rec_id, record, matched_fields in scored_results[:max_results]:
            cpc_prefix = map_cpc_prefix([
                record.get("title", ""),
                record.get("description", ""),
                record.get("category", ""),
                " ".join(record.get("related_keywords", [])),
            ])

            collected = record.get("collected_at") or "2026-08-25"
            posted_date = collected.split("T")[0]

            signal = DemandSignal(
                source="innoget",
                id=f"innoget-{rec_id}",
                title=record.get("title", ""),
                description=record.get("description", "") or record.get("text", "")[:300],
                cpc_prefix=cpc_prefix,
                posted_date=posted_date,
                url=record.get("url", f"https://www.innoget.com/technology-calls/{rec_id}"),
            )
            provenance = MatchProvenance(
                record_id=rec_id,
                score=score,
                matched_fields=matched_fields,
            )
            results.append((signal, provenance))

        return results

    def search_demand(self, query: str, domain: str, max_results: int = 20) -> list[DemandSignal]:
        """Search demand signals matching DemandDataSource protocol."""
        return [signal for signal, _ in self.search_demand_with_provenance(query, domain, max_results)]
