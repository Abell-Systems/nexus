"""How well the application number links the corpus to the OEPM's inventory and to sources keyed by filing number.

Measures; it joins nothing into the corpus and changes no figure. Publications are matched to inventory entries by
publication number, kind code and publication date; their application keys are then compared. A key that cannot be
built is reported, never repaired.
"""

import re
from collections import Counter
from collections.abc import Iterable
from typing import Any

from domain.models.whitespace import (
    ApplicationKey,
    AuthorityEntry,
    PatentPublication,
    application_key_candidates,
    application_key_from_reference,
)

PublicationKey = tuple[str, str, str]


def _shape(text: str) -> str:
    return re.sub(r"[A-Za-z]", "a", re.sub(r"\d", "9", text))


def _group(kind: str) -> str:
    return "ep_translation" if kind.startswith("T") else "other"


def link_report(
    publications: Iterable[PatentPublication],
    authority: Iterable[AuthorityEntry],
    first_year: int = 2000,
    last_year: int = 2025,
) -> dict[str, Any]:
    """Matching, agreement of application keys, collisions of the inventory's keys and what could not be parsed."""
    corpus: dict[PublicationKey, tuple[ApplicationKey | None, str]] = {}
    copies_that_disagree = 0
    for p in publications:
        pub_key = (p.doc_number, p.kind, p.publication_date.strftime("%Y%m%d"))
        value = (
            application_key_from_reference(p.application_reference),
            p.application_date.strftime("%Y%m%d") if p.application_date else "",
        )
        copies_that_disagree += pub_key in corpus and corpus[pub_key] != value
        corpus.setdefault(pub_key, value)

    seen_in_authority = 0
    agreement: Counter[str] = Counter()
    examples: dict[str, list[Any]] = {}
    unparsed: Counter[tuple[str, str]] = Counter()
    filing_dates: dict[ApplicationKey, str | None] = {}  # None once a key has several filing dates
    series_of_digits: dict[str, set[str]] = {}
    by_year: dict[int, Counter[str]] = {}
    authority_entries = 0
    for entry in authority:
        authority_entries += 1
        key = entry.application_key
        in_range = first_year <= int(entry.publication_date[:4]) <= last_year
        if key is None:
            unparsed[(entry.application_office, _shape(entry.application_text))] += 1
        else:
            known = filing_dates.get(key, entry.filing_date)
            filing_dates[key] = known if known == entry.filing_date else None
            if key.series in ("P", "U"):
                series_of_digits.setdefault(key.number, set()).add(key.series)
        if in_range:
            counter = by_year.setdefault(int(entry.publication_date[:4]), Counter())
            counter[f"{_group(entry.kind)}_entries"] += 1
            counter[f"{_group(entry.kind)}_with_application_key"] += key is not None
        publication = (entry.publication_number, entry.kind, entry.publication_date)
        if publication not in corpus:
            continue
        seen_in_authority += 1
        corpus_key, corpus_filing = corpus[publication]
        if corpus_key is None or key is None:
            outcome = "corpus_key_missing" if corpus_key is None else "authority_key_missing"
        elif corpus_key == key:
            outcome = "same_key_filing_date_differs" if corpus_filing != entry.filing_date else "same_key"
        else:
            outcome = "different_keys"
        agreement[outcome] += 1
        if outcome != "same_key" and len(examples.setdefault(outcome, [])) < 3:
            examples[outcome].append(
                {
                    "publication": publication,
                    "corpus": [corpus_key.model_dump() if corpus_key else None, corpus_filing],
                    "authority": [entry.application_office, entry.application_text, entry.filing_date],
                }
            )

    return {
        "authority_entries": authority_entries,
        "corpus_publication_keys": len(corpus),
        "corpus_keys_with_copies_that_disagree_on_the_application": copies_that_disagree,
        "corpus_keys_in_authority": seen_in_authority,
        "corpus_keys_not_in_authority": len(corpus) - seen_in_authority,
        "application_key_agreement": dict(agreement),
        "agreement_examples": examples,
        "authority_application_numbers_not_parsed": {f"{o}|{s}": n for (o, s), n in unparsed.most_common(10)},
        "authority_application_keys": len(filing_dates),
        "authority_keys_with_several_filing_dates": sum(v is None for v in filing_dates.values()),
        "national_digit_strings": len(series_of_digits),
        "national_digit_strings_shared_by_P_and_U": sum(len(v) > 1 for v in series_of_digits.values()),
        "by_year": {y: dict(c) for y, c in sorted(by_year.items())},
    }


def resolve_filing_numbers(numbers: Iterable[tuple[str, str]], known: set[ApplicationKey]) -> dict[str, int]:
    """Distinct (country, filing number) pairs of a source keyed by filing number, by how many known applications they could be."""
    outcomes: Counter[str] = Counter()
    for country, number in set(numbers):
        candidates = application_key_candidates(country, number)
        hits = [c for c in candidates if c in known]
        if not candidates:
            outcomes["not_a_digit_number_or_unknown_office"] += 1
        elif len(hits) == 1:
            outcomes["matched_uniquely"] += 1
        elif len(hits) > 1:
            outcomes["ambiguous_between_series"] += 1
        else:
            outcomes["no_application_in_the_inventory"] += 1
    return dict(outcomes)
