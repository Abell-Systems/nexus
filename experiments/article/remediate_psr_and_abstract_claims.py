"""Remediation script for the BLOCKER/WARNING findings in
POST_109_MANUSCRIPT_AUDIT.md (#110): removes the 4 remaining Patent Search
Report (PSR X/Y/P/E) claims #109 missed, and aligns two Abstract sentences
with caveats already present in the body.

Repository-relative: run from anywhere, resolves the manuscript path via
this file's own location, no hardcoded absolute developer path. Paragraphs
are located by unique anchor text (not raw indices), and every replacement
is followed by an executable postcondition check -- this script fails
loudly if its assumptions about the document no longer hold, rather than
silently modifying the wrong paragraph.
"""
import re
import sys
from pathlib import Path

import docx

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCX_PATH = REPO_ROOT / "experiments" / "article" / "full paper marine policy (updated charts+text).docx"


def find_unique_paragraph(doc, anchor):
    """Return the single paragraph whose text contains `anchor`, or raise."""
    matches = [p for p in doc.paragraphs if anchor in p.text]
    if len(matches) != 1:
        raise AssertionError(
            f"expected exactly 1 paragraph containing {anchor!r}, found {len(matches)}"
        )
    return matches[0]


def set_paragraph_text(p, text):
    runs = p.runs
    if not runs:
        p.add_run(text)
        return
    runs[0].text = text
    for r in runs[1:]:
        r.text = ""


def main():
    if not DOCX_PATH.exists():
        sys.exit(f"manuscript not found at {DOCX_PATH}")

    doc = docx.Document(str(DOCX_PATH))
    pre_paragraph_count = len(doc.paragraphs)
    pre_table_count = len(doc.tables)

    changes = []

    # ---------- Abstract: two PSR-derived sentences + two body-caveat alignments ----------
    p_abstract = find_unique_paragraph(
        doc, "evaluates the quality of inventions through Patent Search Reports"
    )
    old_abstract = p_abstract.text
    assert "Most patents rely on established prior art, signaling incremental innovation." in old_abstract
    assert "Results show patent activity dominated by the private company Pharma Mar S.A." in old_abstract

    new_abstract = old_abstract
    new_abstract = new_abstract.replace(
        "the research maps the spatial distribution of patents, identifies leading organizations and "
        "biological sources, analyzes international patent extensions, and evaluates the quality of "
        "inventions through Patent Search Reports.",
        "the research maps the spatial distribution of patents, examines applicant concentration and "
        "biological sources -- each subject to caveats on data reconciliation detailed in the body -- and "
        "analyzes international patent extensions. An earlier version of this study also reported Patent "
        "Search Report (PSR) prior-art category statistics; that analysis has no traceable source dataset "
        "anywhere in the project archive and has been removed throughout the manuscript rather than restated "
        "unverified.",
    )
    new_abstract = new_abstract.replace(
        "Results show patent activity dominated by the private company Pharma Mar S.A. and a preference for "
        "a narrow set of marine organisms; a regional (sub-national) concentration analysis was attempted "
        "but its underlying data could not be independently verified from the project's archive and is not "
        "presented as a finding here.",
        "Results show patent activity concentrated among a small number of applicants, with Pharma Mar S.A. "
        "leading per a legacy applicant count that could only be partially reconciled against the project's "
        "archived data (see body), and a reliance on a narrow set of marine organism categories, whose "
        "underlying per-compound counts likewise have no independently reproducible source and are presented "
        "as illustrative rather than audited. A regional (sub-national) concentration analysis was attempted "
        "but its underlying data could not be independently verified from the project's archive and is not "
        "presented as a finding here.",
    )
    new_abstract = new_abstract.replace(
        "International patenting strategies reveal a focus on high-income markets, reinforcing global "
        "asymmetries in access to marine genetic resources. Most patents rely on established prior art, "
        "signaling incremental innovation.",
        "International patenting strategies reveal a focus on high-income markets, reinforcing global "
        "asymmetries in access to marine genetic resources.",
    )
    assert new_abstract != old_abstract, "Abstract replacement produced no change"
    set_paragraph_text(p_abstract, new_abstract)
    changes.append(("Abstract", old_abstract, new_abstract))

    # ---------- Introduction: remove the PSR claim ----------
    p_intro = find_unique_paragraph(
        doc, "By analysing Patent Search Reports and mapping legal classifications"
    )
    old_intro = p_intro.text
    new_intro = old_intro.replace(
        "By analysing Patent Search Reports and mapping legal classifications, the study provides a detailed "
        "understanding of the innovation quality and timing in this niche field—an area rarely explored "
        "in prior research.",
        "By mapping applicant concentration, biological source preferences, and international patenting "
        "strategies, the study provides an empirical view of innovation activity in this niche "
        "field—an area rarely explored in prior research.",
    )
    assert new_intro != old_intro, "Introduction replacement produced no change"
    set_paragraph_text(p_intro, new_intro)
    changes.append(("Introduction", old_intro, new_intro))

    # ---------- Conclusion: remove the X/Y/P-category claim ----------
    p_conclusion = find_unique_paragraph(
        doc, "high presence of X and Y category documents in Patent Search Reports"
    )
    old_conclusion = p_conclusion.text
    new_conclusion = old_conclusion.replace(
        " The data further show that most patented inventions are built on well-established prior art (as "
        "revealed by the high presence of X and Y category documents in Patent Search Reports), indicating "
        "incremental rather than radical innovation trends. Additionally, the temporal dynamics of P-category "
        "documents stress the importance of timing in the patenting process.",
        " An earlier version of this manuscript reported Patent Search Report (X/Y/P-category) statistics in "
        "this paragraph as evidence of incremental innovation; that claim has been removed, consistent with "
        "its removal from Results and Discussion, since no dataset supporting it exists anywhere in the "
        "project's archive (see experiments/article/LEGACY_AUDIT_DECISIONS.md and "
        "experiments/article/POST_109_MANUSCRIPT_AUDIT.md).",
    )
    assert new_conclusion != old_conclusion, "Conclusion replacement produced no change"
    set_paragraph_text(p_conclusion, new_conclusion)
    changes.append(("Conclusion", old_conclusion, new_conclusion))

    doc.save(str(DOCX_PATH))

    # ---------- Executable postconditions ----------
    reloaded = docx.Document(str(DOCX_PATH))
    assert len(reloaded.paragraphs) == pre_paragraph_count, (
        f"paragraph count changed: {pre_paragraph_count} -> {len(reloaded.paragraphs)}"
    )
    assert len(reloaded.tables) == pre_table_count, (
        f"table count changed: {pre_table_count} -> {len(reloaded.tables)}"
    )

    full_text = "\n".join(p.text for p in reloaded.paragraphs)

    # No PSR-as-finding phrasing may remain anywhere.
    forbidden_finding_phrases = [
        "evaluates the quality of inventions through Patent Search Reports",
        "Most patents rely on established prior art, signaling incremental innovation.",
        "By analysing Patent Search Reports and mapping legal classifications",
        "high presence of X and Y category documents in Patent Search Reports",
        "X-category documents (72%)",
        "Y-category references in 32%",
        "72% of the patents include an X",
    ]
    for phrase in forbidden_finding_phrases:
        assert phrase not in full_text, f"forbidden PSR-finding phrase still present: {phrase!r}"

    # Every remaining "Patent Search Report" mention must be inside a removal notice
    # (identifiable by "removed" or "has no traceable source" appearing nearby).
    for m in re.finditer(r".{0,120}Patent Search Report.{0,160}", full_text):
        window = m.group(0)
        assert re.search(r"removed|no traceable source|no dataset supporting|not.{0,20}presented as a finding", window), (
            f"'Patent Search Report' mention is not a clearly-marked removal notice: {window!r}"
        )

    print(f"OK: {len(changes)} paragraphs edited; postconditions verified "
          f"({pre_paragraph_count} paragraphs, {pre_table_count} tables, no PSR-finding phrases remain).")
    for name, old, new in changes:
        print(f"\n--- {name} ---")
        print("OLD:", old[:200])
        print("NEW:", new[:200])


if __name__ == "__main__":
    main()
