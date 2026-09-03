# ADR 0001: Nexus Testing Strategy

**Status:** Accepted  
**Date:** 2026-09-03  
**Scope:** Entire Nexus repository  

## Context

Nexus follows Clean Architecture with three layers:
* `domain`
* `application`
* `infrastructure`

The testing strategy must preserve architectural boundaries and test **behavior at the level where that behavior belongs**.

Tests must not be introduced merely because a class, module, adapter, or function exists. Each test must provide evidence for a meaningful domain invariant, application use case, infrastructure behavior, or externally observable product behavior.

This ADR is normative for all current and future Nexus development, including experimental capabilities implemented as part of empirical studies. Empirical studies must not introduce a separate testing architecture.

## Decision

### 1. Domain

Domain tests are required **only when domain objects contain meaningful logic**.

Examples of behavior that warrants domain unit tests:
* invariants and validation;
* value-object construction rules;
* deterministic transformations;
* domain calculations;
* state transitions;
* equality or ordering semantics;
* collection deduplication or provenance rules.

Pure data containers with no behavior do not require dedicated unit tests merely for field coverage.

Domain tests must be:
* fast;
* deterministic;
* isolated;
* independent of databases, filesystems, network services, external APIs, and heavyweight models.

### 2. Application

Application tests verify **use cases and application orchestration**.

They must test what the application service does from the perspective of its collaborators and returned result, including:
* input handling;
* orchestration order where behaviorally relevant;
* collaboration between domain and ports;
* branching and failure behavior;
* construction of the resulting domain output.

Application tests use **stubs**, not mocks.

A stub supplies deterministic collaborator behavior. Tests must not depend on interaction-verification frameworks or mock-based assertions.

For example, the matching use case may receive stubs for candidate retrieval and ranking strategies. The test verifies the resulting use-case behavior, not implementation details of individual classes.

Application tests must not require concrete infrastructure such as database engines, sentence transformers, external services, or production data snapshots.

### 3. Infrastructure

Infrastructure tests verify the **real implementation of the corresponding vertical slice**.

They must exercise the actual infrastructure components against controlled test fixtures where appropriate.

Infrastructure tests must verify real behavior such as:
* database queries;
* full-text retrieval;
* embedding generation or consumption;
* taxonomic classification matching;
* persistence;
* snapshot integrity;
* serialization;
* deterministic ordering;
* infrastructure-specific failure states.

Do not replace the infrastructure under test with mocks. Use small deterministic fixtures to make expected behavior explicit and reproducible.

### 4. End-to-End Acceptance

E2E tests verify **observable Nexus behavior across the complete relevant vertical slice**.

They use the real application wiring and real infrastructure required by the scenario.

For matching capabilities, an acceptance test exercises the complete flow from input demand through eligibility, candidate retrieval, pooling, and ranking to the returned matching result.

E2E tests establish that layers integrate correctly. They are not substitutes for domain or application tests.

### 5. Test Doubles

The repository follows this rule:

> **Stubs at the application boundary; real infrastructure in infrastructure and E2E tests.**

Do not introduce mocks simply because they are convenient.
* Use a stub when the purpose of the test is to provide a known collaborator result.
* Use a real implementation when the purpose of the test is to establish that implementation's behavior or integration.

### 6. Test Ownership by Layer

| Behavior | Test location | Test type |
|---|---|---|
| Domain invariant | `backend/test/unit/domain/` | Unit |
| Domain calculation | `backend/test/unit/domain/` | Unit |
| Use-case orchestration | `backend/test/unit/application/` | Unit / Use-case with stubs |
| Port interaction semantics | `backend/test/unit/application/` | Use-case with stubs |
| Database query behavior | `backend/test/integration/infrastructure/` | Integration / Vertical slice |
| Embedding storage & search | `backend/test/integration/infrastructure/` | Integration / Vertical slice |
| Taxonomic infrastructure | `backend/test/integration/infrastructure/` | Integration / Vertical slice |
| Full observable flow | `backend/test/e2e/` | End-to-end acceptance |
| Statistical evaluation for papers | `scripts/evaluation/` | Independent analysis tests |

### 7. Quality Gates and CI

Every implementation must preserve the repository's existing quality gates:
* Ruff;
* Mypy;
* Pytest;
* Coverage requirements;
* Frontend quality/build checks where affected;
* Gitleaks;
* Sonar;
* Final CI quality gate.

A new capability is not considered complete merely because its local tests pass. It must integrate cleanly with the repository's existing CI.

## Consequences

This strategy deliberately avoids:
* one test file per production class as a blanket rule;
* mock-heavy application tests;
* mocked infrastructure tests;
* duplicated tests across layers;
* tests written solely for coverage;
* a separate "scientific" testing architecture.

It favors:
* domain tests for actual domain behavior;
* application tests for use cases;
* real vertical-slice infrastructure tests;
* E2E tests for product acceptance;
* small deterministic fixtures;
* explicit architectural boundaries.

## Rule for Future Agents

When adding or modifying functionality in Nexus, **apply this ADR before creating tests**.

Do not ask which testing pattern to use unless the new behavior genuinely falls outside the cases defined here.

Determine the layer that owns the behavior and test it at that level:
> **Domain logic → domain unit test.**  
> **Use case → application test with stubs.**  
> **Infrastructure behavior → real vertical-slice test.**  
> **Observable product flow → E2E acceptance test.**  

This ADR is the authoritative testing convention for Nexus.
