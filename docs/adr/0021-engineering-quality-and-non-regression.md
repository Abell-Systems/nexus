# ADR 0021: Engineering Quality & Non-Regression Policy

**Status:** Accepted  
**Date:** 2026-09-08  
**Scope:** Entire Nexus repository  

## Context

Nexus is evolving as both a production software system and a reproducible research platform. Its functional surface, scientific contracts, infrastructure, and test suite will necessarily grow over time.

Growth must not be allowed to silently trade away maintainability, correctness, architectural integrity, or reproducibility. In particular, functional work must not accumulate incidental technical debt merely because the debt is outside the immediate feature scope.

ADR 0001 establishes the testing strategy and ADR 0002 establishes minimal Clean Code and pragmatic SOLID. This ADR complements those decisions by defining the non-regression principle that applies across contributions.

## Decision

### 1. Technical quality is non-regressive

A Nexus contribution must leave the repository at an equal or better technical quality level than the base revision, unless an explicit exception is justified and documented.

The relevant dimensions are:

* correctness and behavioral integrity;
* maintainability and readability;
* architectural boundaries and dependency direction;
* test adequacy for changed behavior;
* reproducibility and provenance where applicable;
* static-analysis and tooling health.

A functional improvement does not by itself justify deterioration in one of these dimensions.

### 2. Contracts are protected

Existing architectural, domain, scientific, and data contracts must not be weakened implicitly.

When existing behavior is changed intentionally:

1. identify the affected contract;
2. characterize the current behavior when necessary;
3. define the new behavior explicitly;
4. test the intended transition;
5. update the governing ADR or other normative documentation when the decision itself changes.

The implementation must not silently change semantics merely to simplify a refactor or satisfy a tooling warning.

### 3. Refactoring and feature work remain reviewable

A contribution should have one coherent purpose.

Unrelated refactoring, cleanup, architectural rewrites, or opportunistic modernization must not be bundled into functional or scientific changes when separation would make the change easier to review and verify.

If a refactor is valuable independently, it should normally have its own issue or pull request.

### 4. New technical debt is explicit

New technical debt must not be introduced silently.

If a temporary compromise is necessary, the contribution must state:

* what technical quality dimension is affected;
* why the compromise is necessary;
* its expected impact;
* how the debt is tracked;
* what condition permits its removal.

The exception is part of the engineering record; it is not a hidden property of the implementation.

### 5. Quality gates are evidence, not the architecture

Pull requests should use the repository's available automated checks, including tests, linting, type checking, architectural checks, documentation checks, and static analysis where configured.

These tools are evidence for technical quality, not substitutes for architectural judgment.

In particular, a static-analysis finding must not be "fixed" by changing correct behavior merely to satisfy the tool. Where a tool conflicts with a real contract, preserve the contract and document or separately resolve the tooling issue.

No single metric, including a Sonar issue count, defines engineering quality.

### 6. Scientific and technical integrity are coupled

For research-critical code, maintainability is not independent of scientific validity. Changes that affect data selection, evaluation, ranking, temporal eligibility, provenance, metrics, or reproducibility must preserve the corresponding scientific contracts.

A technically cleaner implementation that changes an experimental contract without an explicit decision is a regression, not an improvement.

### 7. Exceptions require explicit review

An exception to this policy is acceptable only when the trade-off is deliberate and reviewable.

The pull request must identify the exception and its rationale. If the exception changes an architectural or scientific decision, the appropriate ADR or normative artifact must be updated before or together with the implementation.

## Consequences

Expected consequences are:

* technical quality becomes an explicit project constraint rather than an informal preference;
* feature work cannot silently accumulate unrelated debt;
* characterization tests become the preferred safety mechanism for behavior-preserving refactors;
* Sonar and other static-analysis tools remain useful without becoming architectural authorities;
* technical cleanup can proceed independently from scientific work;
* deliberate trade-offs remain visible and reversible;
* Nexus can grow without treating accumulated complexity as an unavoidable cost of progress.

This policy does not require every contribution to reduce every quality metric. It requires that deterioration be avoided by default and made explicit when unavoidable.

## Relationship to Existing ADRs

This ADR complements, rather than replaces:

* **ADR 0001** — testing strategy;
* **ADR 0002** — minimal Clean Code and pragmatic SOLID;
* subsequent architectural and scientific ADRs governing specific contracts.

Specific ADRs remain authoritative for their respective architectural or scientific decisions.

## Normative Rule

For every Nexus contribution:

> **Do not trade technical quality for short-term progress silently. Preserve contracts, test changed behavior, separate unrelated cleanup, make new debt explicit, and use tooling as evidence rather than as the architecture.**
