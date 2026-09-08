# PR-E Dry-Run Annotation Guide — DRAFT

**Status:** DRAFT. Per `docs/superpowers/specs/2026-09-08-pr-e-dry-run-execution-design.md` §5 (step 4/5): this is a proposal for the scale's worked examples and boundary language. **Sections marked `⚠ PENDING VALIDATION` are not decided** — they are starting points for Valentín + Lydia to accept, edit, or replace. Not a frozen artifact (spec §7): no manifest, no hash, until finalized.

This guide is deliberately independent of which 6-8 demands end up selected (`docs/annotation/phase2-dry-run-selection.md`, itself still a draft) — nothing here presupposes a specific demand.

## 1. What you are judging

For each `(demand, patent candidate)` pair, you assign one grade: **how relevant is this patent to solving the technology demand, on purely technical/topical grounds.**

You are **not** judging:
- Whether the patent legally qualifies as prior art.
- Whether the patent's publication date matters (you will not be shown any date — see §2).
- How "important" or "urgent" the demand is.
- Which system, method, or search produced this candidate (you will not be shown that either).

If you catch yourself reasoning about dates, priority, or eligibility while grading, that reasoning does not belong in this task — it happens later, separately, in Nexus's own eligibility pipeline (ADR 0019), never during annotation.

## 2. What you will see, and what you won't

Per the blind-export boundary (PR #56): for each candidate you will see only —

- The demand's title and description.
- The patent's `publication_id`, title, abstract, and CPC classification codes (as observed, auxiliary evidence — not a hint, not a recommendation).

You will **not** see: any relevance/similarity score, which retrieval method (lexical/CPC/semantic) surfaced the candidate, its position/rank in any list, or its publication date. This is enforced structurally, not just by convention (the data types you're given literally have no field for any of those).

## 3. The scale

| Grade | Label | Meaning |
|---|---|---|
| **0** | Not relevant | The patent has no meaningful technical connection to the demand. |
| **1** | Marginally relevant | Same general technical area, but does not address the demand's actual problem. |
| **2** | Relevant | Addresses a real component of the demand's problem, or a closely analogous technical approach. |
| **3** | Highly relevant | Directly addresses the demand's stated problem — a candidate solution or substantial prior art in the plain technical sense (not a legal determination). |

Grade every pair independently — do not compare pairs to each other while grading, and do not revise an earlier grade after seeing a later one in the same batch.

## 4. Worked examples (illustrative — not from the real candidate pool)

These are synthetic, to avoid presupposing which real demands get selected.

**Example set A** — *Demand:* "Seeking a coating to reduce corrosion on steel pipes exposed to seawater."

- **Grade 0:** A patent describing a corrosion-resistant coating for aircraft aluminum fuselages. Same general concept (corrosion coating) but wrong material, wrong environment, no transferable technical link.
- **Grade 1:** A patent on general-purpose anti-corrosion primers for structural steel, with no mention of marine/seawater exposure. Same material, same broad problem class, but doesn't address the demand's specific (seawater) condition.
- **Grade 2:** A patent on a zinc-based sacrificial coating for steel structures in marine environments, but for ship hulls rather than pipes. Same problem, same environment, closely analogous application.
- **Grade 3:** A patent on a polymer-ceramic composite coating specifically for steel pipelines in seawater/offshore applications. Directly addresses the stated problem.

**Example set B** — *Demand:* "Seeking a method to detect water quality using low-power sensors."

- **Grade 0:** A patent on a high-power industrial water treatment plant control system. Water-related, but not sensing, not low-power, no real technical overlap.
- **Grade 1:** A patent on a general environmental sensor network architecture (not water-specific, not addressing power constraints).
- **Grade 2:** A patent on a semiconductor-based pH sensor for water, without an explicit low-power design claim.
- **Grade 3:** A patent on a miniaturized, low-power multiparameter water quality sensor using semiconductor sensing. Matches the demand closely on both the "what" (water quality) and the stated constraint (low-power).

## 5. ⚠ PENDING VALIDATION — the 1↔2 and 2↔3 boundaries

This is the section most likely to drive disagreement, per the instrument's own design intent (§4/§10 of the dry-run execution spec) — it is deliberately left as a proposal, not a rule.

**Proposed 1↔2 boundary (draft):** grade 2 requires the patent to address a genuine *component* of the demand's problem (the same sub-problem, the same functional requirement, or a closely analogous technical mechanism) — not just the same general field. Grade 1 is "same neighborhood," grade 2 is "same building."

**Proposed 2↔3 boundary (draft):** grade 3 requires the patent to address the demand's problem as a whole, not just one component of it — even if it's not a perfect match, a grade-3 candidate should read as "if I were solving this demand, I would look closely at this patent," not "this is one piece of a possible solution."

**Open question for Valentín + Lydia to resolve, not implied by anything above:** how to grade a patent that solves the demand's problem completely but via a very different technical mechanism than what the demand describes (e.g. a chemical solution to a demand phrased in mechanical terms) — is that a 2 (analogous approach) or a 3 (directly addresses the problem, mechanism aside)? The worked examples above don't cover this case on purpose; it's exactly the kind of edge case the dry-run is meant to surface.

## 6. Disagreements

Disagreements between annotators are recorded (`compute_iaa`'s `Disagreement` list) and reviewed together with the confusion matrix — never auto-resolved, never averaged, never silently picked by one annotator's authority over the other's. See the execution-design spec §8 for what happens with the IAA result.

## 7. Process reminders

- Annotate independently. Do not discuss specific pairs with the other annotator until both have finished the full batch.
- The candidate pool and batch are frozen before annotation starts (spec §9, non-negotiable) — your judgments cannot add, remove, or reorder candidates.
- If a candidate's evidence (title/abstract/CPC) is too sparse to judge confidently, grade on what's actually shown — do not look up the patent externally, since that would reintroduce information (like publication date) the blind boundary deliberately withholds.
