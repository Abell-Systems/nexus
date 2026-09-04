# AGENTS.md — Nexus Architecture & Engineering Directives for AI Coding Agents

This repository is governed by strict scientific, architectural, and quality invariants. All agents contributing code to Abell Nexus MUST read, internalize, and strictly obey the directives in this document.

---

## 1. Core Principle

> **La ciencia valida el motor; el producto resuelve el problema.**
> (Science validates the engine; the product solves the problem.)

We solve problems with clean, decoupled architecture, never with ad-hoc heuristics or opportunistic patches.

---

## 2. Architecture Decision Records (ADRs) are Binding Contracts

ADRs located in `docs/adr/` are **mandatory engineering constraints**, not optional documentation or historical summaries.

Before modifying architecture, behavior, data contracts, persistence, external integrations, configuration boundaries, scientific methodology, or other cross-cutting design concerns:

1. **Inspect existing ADRs first.**
2. If an applicable ADR exists, **the implementation MUST comply with it**.
3. If the proposed change conflicts with an existing ADR, **do not silently override or work around it**. Either:
   * adapt the implementation to comply, or
   * create/update an ADR explicitly documenting the architectural change.
4. If the change introduces a **new architectural decision**, a new ADR MUST be created in `docs/adr/` in the same change set.
5. A PR is **not merge-ready** while an applicable ADR is missing, contradicted, or not reflected in the implementation.
6. Tests MUST verify important architectural invariants where practical.

### Hard Rule
> **ADR compliance is part of the definition of done.**

Do not treat ADRs as explanatory prose added after implementation. ADRs define binding architectural constraints for production code.

---

## 3. Configuration Over Hardcoding

Any value that represents a domain constraint, study constraint, jurisdiction, policy, allowlist/blocklist, source-specific rule, external identifier set, or other changeable decision MUST be represented as versioned configuration/data rather than hardcoded in production code.

Temporary constraints are still configuration.

The implementation MUST separate:
```text
facts / observations
        +
versioned configuration / policy
        ↓
algorithm / decision procedure
```

* **Zero Hardcoded Business Lists in Production:** Never embed country lists, company lists, corporate abbreviation heuristics, or domain lists inside algorithm classes.
* **Fail-Fast Invariant:** Missing or corrupted configuration MUST raise an immediate explicit error (`FileNotFoundError`, `ValueError`). The application MUST NEVER synthesize an in-memory fallback policy when configuration is missing.
* **Symmetrical Tripartite Classification:** Absence of evidence is not proof of negation (`UNKNOWN != NEGATIVE`). If evidence is missing or unrecognized, classification must evaluate strictly to `UNVERIFIED`, never to a default foreign/negative outcome.
* **Unified Provenance:** Use canonical `FieldObservation` models with explicit distinction between `SOURCE_REPORTED` and `INDEPENDENTLY_VERIFIED`.

---

## 4. Architectural Enforcement via Automated Quality Gates & Import Linter (ADR 0008)

Agent instructions alone are insufficient; rules must be backed by automated technical enforcement in CI.

Architectural constraints are **executable, machine-verifiable contracts**. If an architectural rule can be expressed as a dependency constraint, layer boundary, or invariant, it MUST be enforced by CI rather than relying solely on documentation or human code review.

The 4-level enforcement stack is binding on all pull requests:
1. **Level 1 (Ruff):** Format, linting, import sorting, complexity limits.
2. **Level 2 (Mypy):** Strict protocol contracts, structural subtyping without `Any` to hide cross-context coupling.
3. **Level 3 (Import Linter & Invariant Tests):** Declarative layer contracts in `.importlinter` (`domain` isolated from `application`/`infrastructure`; `application` isolated from `infrastructure`; auditor subsystems isolated from collaborator domain models) plus pytest architecture invariants.
4. **Level 4 (SonarCloud):** Bugs, code smells, duplication, cognitive complexity, test coverage threshold.

Every major architectural boundary MUST be accompanied by deterministic architectural invariant tests:
1. **No In-Code Policies:** Verify that algorithm resolvers require explicit policy injection and fail fast if policy is omitted.
2. **Dynamic Behavior:** Demonstrate that changing configuration (e.g., target jurisdiction) alters classification behavior without modifying Python code.
3. **No Synthetic Inventions:** Verify that entity identifiers and attributes are authentic from observed facts, never fabricated from arbitrary batch IDs or fallback strings.
4. **No Cross-Context Concealment:** Never use `typing.Any` to bypass static type checks or circumvent import restrictions across bounded contexts.

---

## 5. Agent Verification Checklist Before Completing Tasks

Before declaring any task or PR complete, the agent MUST explicitly verify:
* [ ] Applicable ADRs were inspected (ADR 0001 through ADR 0008).
* [ ] Implementation strictly complies with ADRs.
* [ ] Any new architectural decisions have an ADR in `docs/adr/`.
* [ ] Configurable constraints are externalized to versioned files (e.g., `config/policies/`).
* [ ] No policy/domain data has been hardcoded into production code.
* [ ] Absence of configuration triggers fail-fast errors (no default fallbacks fabricated in code).
* [ ] All tests pass cleanly (`pytest backend/test/unit -v --cov=backend/src/main --cov-report=xml:coverage.xml`).
* [ ] Static analysis is 100% green (`ruff check .` and `mypy backend/src/main`).
* [ ] Architectural quality gate is 100% green (`python scripts/check_architecture.py` and `PYTHONPATH=backend/src/main lint-imports`).
* [ ] Diff contains only files relevant to the specific block/PR.
